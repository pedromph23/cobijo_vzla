"""
Módulo de mapa de calor para CobijoVzla.

Calcula índices de necesidad por parroquia combinando variables
ponderadas. Optimizado para 1000+ parroquias con caché de refugios
y muestreo inteligente de distancias.

Ejemplo:
    >>> from apps.optimizacion.heatmap import generar_mapa_calor
    >>> puntos = generar_mapa_calor()
    >>> len(puntos)
    1270
"""
from __future__ import annotations

import hashlib
import logging
from dataclasses import dataclass, asdict
from typing import Dict, List, Optional

from django.core.cache import cache
from django.db.models import Count, Q
from django.utils import timezone
from datetime import timedelta
from geopy.distance import geodesic

from apps.core.models import Parroquia, RefugioExistente, ZonaAfectada, PuntoDemanda
from apps.emergencias.models import Reporte


logger = logging.getLogger(__name__)


# ============================================================
# CONFIGURACIÓN
# ============================================================

class Pesos:
    """Pesos por defecto para el índice de necesidad."""
    DENSIDAD = 1.0
    VULNERABILIDAD = 1.0
    DISTANCIA = 1.0
    HERIDOS = 1.0
    FALLECIDOS = 1.0
    DAMNIFICADOS = 1.0
    REPORTES = 1.0

    @classmethod
    def to_dict(cls) -> Dict[str, float]:
        return {
            'densidad': cls.DENSIDAD,
            'vulnerabilidad': cls.VULNERABILIDAD,
            'distancia': cls.DISTANCIA,
            'heridos': cls.HERIDOS,
            'fallecidos': cls.FALLECIDOS,
            'damnificados': cls.DAMNIFICADOS,
            'reportes': cls.REPORTES,
        }

    @classmethod
    def from_request(cls, query_params) -> Dict[str, float]:
        """Extrae pesos desde query params, con fallback a defaults."""
        pesos = cls.to_dict()
        for clave in pesos:
            if clave in query_params:
                try:
                    valor = float(query_params[clave])
                    if valor >= 0:
                        pesos[clave] = valor
                except (ValueError, TypeError):
                    logger.warning(f"Peso inválido '{clave}': {query_params[clave]}")
        return pesos


class Limites:
    """Valores máximos para normalizar cada variable al rango [0, 1]."""
    DENSIDAD = 20000.0
    DISTANCIA_KM = 50.0
    HERIDOS = 500.0
    FALLECIDOS = 50.0
    DAMNIFICADOS = 5000.0
    REPORTES = 100.0


CACHE_TTL_HEATMAP = 1800  # 30 minutos
CACHE_KEY_REFUGIOS = 'heatmap_refugios_coords'
MUESTRA_MAX_REFUGIOS = 50  # Si hay más, muestreamos


# ============================================================
# DATACLASSES
# ============================================================

@dataclass
class PuntoCalor:
    """Punto del mapa de calor."""
    lat: float
    lng: float
    intensidad: float
    parroquia: str
    estado: str
    parroquia_id: int

    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class EstadisticasCalor:
    """Estadísticas agregadas del mapa de calor."""
    total: int = 0
    promedio: float = 0.0
    maximo: float = 0.0
    minimo: float = 0.0
    alto: int = 0
    medio: int = 0
    bajo: int = 0

    def to_dict(self) -> Dict:
        return asdict(self)


# ============================================================
# UTILIDADES
# ============================================================

def normalizar(valor: Optional[float], maximo: float) -> float:
    """Normaliza un valor al rango [0, 1]. Tolerante a None y negativos."""
    if valor is None or valor <= 0 or maximo <= 0:
        return 0.0
    return min(float(valor) / maximo, 1.0)


def _hash_pesos(pesos: Optional[Dict]) -> str:
    """Genera un hash corto de los pesos para usar como parte de la caché key."""
    if not pesos:
        return "default"
    items = sorted(pesos.items())
    s = "|".join(f"{k}={v}" for k, v in items)
    return hashlib.md5(s.encode()).hexdigest()[:8]


def _refugios_coords() -> List[tuple]:
    """
    Coordenadas (lat, lng) de refugios operativos.
    Cacheado 5 minutos. Filtra refugios sin geometría.

    Nota: se extrae y/x en Python porque Django no garantiza
    `values_list('ubicacion__y')` en todas las configuraciones.
    """
    coords = cache.get(CACHE_KEY_REFUGIOS)
    if coords is None:
        coords = []
        qs = (
            RefugioExistente.objects
            .filter(operativo=True, ubicacion__isnull=False)
            .only('ubicacion')
            .iterator(chunk_size=500)
        )
        for r in qs:
            try:
                coords.append((r.ubicacion.y, r.ubicacion.x))
            except Exception as e:
                logger.warning(f"Refugio {r.id} sin coords válidas: {e}")
                continue
        cache.set(CACHE_KEY_REFUGIOS, coords, CACHE_TTL_HEATMAP)
        logger.debug(f"Cacheados {len(coords)} refugios operativos")
    return coords


def _distancia_promedio(lat: float, lng: float, coords: List[tuple]) -> float:
    """
    Distancia promedio desde (lat, lng) a las coordenadas dadas.

    Si hay más de MUESTRA_MAX_REFUGIOS, muestrea para eficiencia.
    """
    if not coords:
        return Limites.DISTANCIA_KM

    if len(coords) > MUESTRA_MAX_REFUGIOS:
        paso = len(coords) // MUESTRA_MAX_REFUGIOS
        muestra = coords[::paso][:MUESTRA_MAX_REFUGIOS]
    else:
        muestra = coords

    try:
        distancias = [
            geodesic((lat, lng), (r_lat, r_lng)).km
            for r_lat, r_lng in muestra
        ]
        return sum(distancias) / len(distancias) if distancias else Limites.DISTANCIA_KM
    except Exception as e:
        logger.warning(f"Error calculando distancias: {e}")
        return Limites.DISTANCIA_KM


# ============================================================
# ÍNDICE DE NECESIDAD
# ============================================================

def calcular_indice_necesidad(
    parroquia,
    pesos: Optional[Dict] = None,
    refugios_coords: Optional[List[tuple]] = None,
) -> float:
    """
    Calcula el índice de necesidad (0-1) para una parroquia.

    Combina: densidad, vulnerabilidad, distancia a refugios,
    afectados (heridos/fallecidos/damnificados) y reportes recientes.

    Args:
        parroquia: Instancia de Parroquia.
        pesos: Pesos por variable. Si None, usa defaults.
        refugios_coords: Lista precalculada de coords de refugios.

    Returns:
        Índice redondeado a 4 decimales, entre 0.0 y 1.0.
    """
    pesos = pesos or Pesos.to_dict()
    indice = 0.0
    total_peso = 0.0

    try:
        # 1. Densidad
        if pesos.get('densidad', 0) > 0:
            v = normalizar(parroquia.densidad_poblacional, Limites.DENSIDAD)
            indice += pesos['densidad'] * v
            total_peso += pesos['densidad']

        # 2. Vulnerabilidad
        if pesos.get('vulnerabilidad', 0) > 0:
            v = normalizar(parroquia.indice_vulnerabilidad, 1.0)
            indice += pesos['vulnerabilidad'] * v
            total_peso += pesos['vulnerabilidad']

        # 3. Distancia a refugios
        if pesos.get('distancia', 0) > 0 and parroquia.geom:
            coords = refugios_coords if refugios_coords is not None else _refugios_coords()
            c = parroquia.geom.centroid
            dist = _distancia_promedio(c.y, c.x, coords)
            v = normalizar(dist, Limites.DISTANCIA_KM)
            indice += pesos['distancia'] * v
            total_peso += pesos['distancia']

        # 4. Zonas afectadas (spatial query por parroquia — usa índice GIST)
        if parroquia.geom and any(pesos.get(k, 0) > 0 for k in ('heridos', 'fallecidos', 'damnificados')):
            try:
                zonas = ZonaAfectada.objects.filter(geom__within=parroquia.geom)
                heridos = sum(z.heridos or 0 for z in zonas)
                fallecidos = sum(z.fallecidos or 0 for z in zonas)
                damnificados = sum(z.damnificados or 0 for z in zonas)
            except Exception as e:
                logger.warning(f"Error zonas parroquia {parroquia.id}: {e}")
                heridos = fallecidos = damnificados = 0

            if pesos.get('heridos', 0) > 0:
                v = normalizar(heridos, Limites.HERIDOS)
                indice += pesos['heridos'] * v
                total_peso += pesos['heridos']

            if pesos.get('fallecidos', 0) > 0:
                v = normalizar(fallecidos, Limites.FALLECIDOS)
                indice += pesos['fallecidos'] * v
                total_peso += pesos['fallecidos']

            if pesos.get('damnificados', 0) > 0:
                v = normalizar(damnificados, Limites.DAMNIFICADOS)
                indice += pesos['damnificados'] * v
                total_peso += pesos['damnificados']

        # 5. Reportes recientes (últimos 7 días)
        if pesos.get('reportes', 0) > 0 and parroquia.geom:
            try:
                desde = timezone.now() - timedelta(days=7)
                n = Reporte.objects.filter(
                    Q(punto_demanda__parroquia=parroquia)
                    | Q(zona_afectada__geom__within=parroquia.geom),
                    fecha__gte=desde,
                ).count()
            except Exception as e:
                logger.warning(f"Error reportes parroquia {parroquia.id}: {e}")
                n = 0

            v = normalizar(n, Limites.REPORTES)
            indice += pesos['reportes'] * v
            total_peso += pesos['reportes']

        return round(min(indice / total_peso, 1.0), 4) if total_peso > 0 else 0.0

    except Exception as e:
        logger.error(f"Error índice parroquia {parroquia.id}: {e}")
        return 0.0


# ============================================================
# MAPA DE CALOR
# ============================================================

def generar_mapa_calor(
    pesos: Optional[Dict] = None,
    parroquias_ids: Optional[List[int]] = None,
    usar_cache: bool = True,
) -> List[Dict]:
    """
    Genera puntos del mapa de calor.

    Args:
        pesos: Pesos personalizados. Si None, usa defaults.
        parroquias_ids: Filtrar por IDs específicos. Si None, todas.
        usar_cache: Usar caché de resultado completo.

    Returns:
        Lista de dicts {lat, lng, intensidad, parroquia, estado, parroquia_id}.
    """
    # --- Caché de resultado completo ---
    if usar_cache and parroquias_ids is None:
        cache_key = f"heatmap_full_{_hash_pesos(pesos)}"
        cached = cache.get(cache_key)
        if cached is not None:
            logger.debug("Heatmap desde caché")
            return cached

    logger.warning(
    "Generando mapa de calor completo (puede tardar ~30s). "
    "El resultado se cachea por 30 minutos."
    )

    try:
        qs = Parroquia.objects.select_related('estado').filter(geom__isnull=False)
        if parroquias_ids:
            qs = qs.filter(id__in=parroquias_ids)

        refugios = _refugios_coords()
        puntos: List[Dict] = []

        for parroquia in qs.iterator(chunk_size=500):
            try:
                indice = calcular_indice_necesidad(
                    parroquia, pesos=pesos, refugios_coords=refugios,
                )
                c = parroquia.geom.centroid
                puntos.append(PuntoCalor(
                    lat=round(c.y, 6),
                    lng=round(c.x, 6),
                    intensidad=indice,
                    parroquia=parroquia.nombre,
                    estado=parroquia.estado.nombre if parroquia.estado else '',
                    parroquia_id=parroquia.id,
                ).to_dict())
            except Exception as e:
                logger.warning(f"Parroquia {parroquia.id} omitida: {e}")
                continue

        logger.info(f"Mapa de calor listo: {len(puntos)} puntos")

        # Guardar en caché
        if usar_cache and parroquias_ids is None:
            cache.set(f"heatmap_full_{_hash_pesos(pesos)}", puntos, CACHE_TTL_HEATMAP)

        return puntos

    except Exception as e:
        logger.error(f"Error generando mapa de calor: {e}", exc_info=True)
        return []


def generar_mapa_calor_por_estado(estado_id: int, pesos: Optional[Dict] = None) -> List[Dict]:
    """Genera mapa de calor para un estado específico."""
    ids = list(Parroquia.objects.filter(estado_id=estado_id).values_list('id', flat=True))
    return generar_mapa_calor(pesos=pesos, parroquias_ids=ids)


# ============================================================
# ESTADÍSTICAS
# ============================================================

def obtener_estadisticas_calor(pesos: Optional[Dict] = None) -> Dict:
    """Estadísticas agregadas del mapa de calor."""
    try:
        puntos = generar_mapa_calor(pesos=pesos)
        if not puntos:
            return EstadisticasCalor().to_dict()

        indices = [p['intensidad'] for p in puntos]
        return EstadisticasCalor(
            total=len(indices),
            promedio=round(sum(indices) / len(indices), 4),
            maximo=max(indices),
            minimo=min(indices),
            alto=sum(1 for i in indices if i > 0.7),
            medio=sum(1 for i in indices if 0.3 <= i <= 0.7),
            bajo=sum(1 for i in indices if i < 0.3),
        ).to_dict()
    except Exception as e:
        logger.error(f"Error en estadísticas: {e}")
        return EstadisticasCalor().to_dict()


# ============================================================
# HELPERS DE COMPATIBILIDAD
# ============================================================

def get_pesos_desde_request(query_params) -> Dict:
    """Compatibilidad. Usar Pesos.from_request()."""
    return Pesos.from_request(query_params)


def invalidar_cache():
    """Invalida caché del heatmap. Llamar cuando cambien refugios/zonas."""
    cache.delete(CACHE_KEY_REFUGIOS)
    # Nota: en caché local (LocMemCache) no se pueden borrar patrones.
    # Se invalidan solos por TTL (5 min). Para Redis, descomentar:
    # try:
    #     cache.delete_pattern("heatmap_full_*")
    # except AttributeError:
    #     pass
    logger.info("Caché de heatmap invalidada (TTL expirará en 5 min)")