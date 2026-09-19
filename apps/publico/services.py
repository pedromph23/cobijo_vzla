"""
Servicios del portal público.

Extrae la lógica de negocio de las vistas para mantener controladores
delgados y cacheables.
"""
from __future__ import annotations

import hashlib
import logging
from typing import Dict, List, Optional

from django.core.cache import cache
from django.db.models import Q, QuerySet

from apps.core.models import RefugioExistente, ZonaAfectada, Estado, Parroquia


logger = logging.getLogger(__name__)


# ============================================================
# CONFIGURACIÓN DE CACHÉ
# ============================================================

CACHE_TTL_REFUGIOS = 300   # 5 min
CACHE_TTL_ZONAS = 180      # 3 min (cambian con más frecuencia)
CACHE_TTL_BUSQUEDA = 600   # 10 min
CACHE_KEY_REFUGIOS = 'publico_refugios'
CACHE_KEY_ZONAS = 'publico_zonas'


# ============================================================
# SERIALIZADORES
# ============================================================

def _serializar_refugio(r: RefugioExistente) -> Dict:
    """Serializa un refugio para la API pública."""
    return {
        'id': r.id,
        'nombre': r.nombre,
        'direccion': r.direccion,
        'lat': r.ubicacion.y if r.ubicacion else None,
        'lng': r.ubicacion.x if r.ubicacion else None,
        'capacidad_total': r.capacidad_total,
        'capacidad_disponible': r.capacidad_disponible,
        'servicios': r.servicios if isinstance(r.servicios, list) else [],
        'operativo': r.operativo,
        'telefono': r.telefono,
        'horario': r.horario,
    }


def _serializar_zona(z: ZonaAfectada) -> Optional[Dict]:
    """Serializa una zona afectada. Retorna None si no tiene geometría."""
    if not z.geom:
        return None
    c = z.geom.centroid
    return {
        'id': z.id,
        'nombre': z.nombre,
        'descripcion': z.descripcion,
        'nivel_alerta': z.nivel_alerta,
        'heridos': z.heridos,
        'fallecidos': z.fallecidos,
        'damnificados': z.damnificados,
        'lat': c.y,
        'lng': c.x,
        'evento': z.evento.nombre if z.evento else None,
        'tipo_evento': z.evento.tipo if z.evento else None,
    }


# ============================================================
# REFUGIOS
# ============================================================

def obtener_refugios_publicos(limite: int = 1000) -> List[Dict]:
    """
    Lista de refugios operativos para el mapa público.

    Cacheado por 5 minutos. Limita el número de resultados para evitar
    respuestas gigantes.

    Args:
        limite: máximo de refugios a retornar (default 1000).
    """
    cache_key = f'{CACHE_KEY_REFUGIOS}_{limite}'
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    try:
        qs = (
            RefugioExistente.objects
            .filter(operativo=True, ubicacion__isnull=False)
            .only(
                'id', 'nombre', 'direccion', 'ubicacion',
                'capacidad_total', 'capacidad_disponible',
                'servicios', 'operativo', 'telefono', 'horario',
            )[:limite]
        )
        data = [_serializar_refugio(r) for r in qs]
        cache.set(cache_key, data, CACHE_TTL_REFUGIOS)
        logger.info(f"Refugios públicos: {len(data)} cacheados por {CACHE_TTL_REFUGIOS}s")
        return data
    except Exception as e:
        logger.error(f"Error obteniendo refugios: {e}", exc_info=True)
        return []


# ============================================================
# ZONAS AFECTADAS
# ============================================================

def obtener_zonas_activas(limite: int = 500) -> List[Dict]:
    """
    Zonas afectadas activas (sin fecha de fin).

    Cacheado por 3 minutos.
    """
    cache_key = f'{CACHE_KEY_ZONAS}_{limite}'
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    try:
        qs = (
            ZonaAfectada.objects
            .filter(fecha_fin__isnull=True, geom__isnull=False)
            .select_related('evento')
            .only(
                'id', 'nombre', 'descripcion', 'nivel_alerta',
                'heridos', 'fallecidos', 'damnificados',
                'geom', 'evento__nombre', 'evento__tipo',
            )[:limite]
        )
        data = []
        for z in qs:
            s = _serializar_zona(z)
            if s:
                data.append(s)
        cache.set(cache_key, data, CACHE_TTL_ZONAS)
        logger.info(f"Zonas activas: {len(data)} cacheadas por {CACHE_TTL_ZONAS}s")
        return data
    except Exception as e:
        logger.error(f"Error obteniendo zonas: {e}", exc_info=True)
        return []


# ============================================================
# BÚSQUEDA
# ============================================================

def _normalizar_query(q: str) -> str:
    """Limpia y valida el término de búsqueda."""
    return (q or '').strip()[:100]  # máximo 100 caracteres


def buscar_lugares(query: str, limite_por_tipo: int = 5) -> List[Dict]:
    """
    Busca estados, parroquias y refugios que coincidan con `query`.

    Args:
        query: término de búsqueda (mínimo 2 caracteres).
        limite_por_tipo: máximo de resultados por cada tipo.

    Returns:
        Lista de dicts {tipo, nombre, estado, lat, lng}.
    """
    query = _normalizar_query(query)
    if len(query) < 2:
        return []

    # Caché por término (case-insensitive)
    cache_key = f'publico_busqueda_{hashlib.md5(query.lower().encode()).hexdigest()[:12]}'
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    resultados: List[Dict] = []

    try:
        # 1. Parroquias
        parroquias = (
            Parroquia.objects
            .filter(nombre__icontains=query, geom__isnull=False)
            .select_related('estado')
            .only('id', 'nombre', 'geom', 'estado__nombre')[:limite_por_tipo]
        )
        for p in parroquias:
            c = p.geom.centroid
            resultados.append({
                'tipo': 'parroquia',
                'nombre': p.nombre,
                'estado': f"Parroquia del Estado {p.estado.nombre}" if p.estado else 'Parroquia',
                'lat': c.y,
                'lng': c.x,
            })

        # 2. Estados
        estados = (
            Estado.objects
            .filter(nombre__icontains=query, geom__isnull=False)
            .only('id', 'nombre', 'geom')[:min(3, limite_por_tipo)]
        )
        for e in estados:
            c = e.geom.centroid
            resultados.append({
                'tipo': 'estado',
                'nombre': e.nombre,
                'estado': 'Estado',
                'lat': c.y,
                'lng': c.x,
            })

        # 3. Refugios
        refugios = (
            RefugioExistente.objects
            .filter(
                Q(nombre__icontains=query) | Q(direccion__icontains=query),
                operativo=True,
                ubicacion__isnull=False,
            )
            .only('id', 'nombre', 'direccion', 'ubicacion')[:limite_por_tipo]
        )
        for r in refugios:
            resultados.append({
                'tipo': 'refugio',
                'nombre': r.nombre,
                'estado': r.direccion or 'Refugio',
                'lat': r.ubicacion.y,
                'lng': r.ubicacion.x,
            })

        cache.set(cache_key, resultados, CACHE_TTL_BUSQUEDA)
        return resultados

    except Exception as e:
        logger.error(f"Error en búsqueda '{query}': {e}", exc_info=True)
        return []


# ============================================================
# ESTADÍSTICAS PARA LA HOME
# ============================================================

def obtener_estadisticas_home() -> Dict[str, int]:
    """Estadísticas para la página principal del mapa público."""
    cache_key = 'publico_home_stats'
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    from apps.emergencias.models import Evento
    try:
        stats = {
            'eventos_activos': Evento.objects.filter(activo=True).count(),
            'total_refugios': RefugioExistente.objects.filter(operativo=True).count(),
            'zonas_activas': ZonaAfectada.objects.filter(fecha_fin__isnull=True).count(),
        }
        cache.set(cache_key, stats, CACHE_TTL_REFUGIOS)
        return stats
    except Exception as e:
        logger.error(f"Error en stats home: {e}", exc_info=True)
        return {'eventos_activos': 0, 'total_refugios': 0, 'zonas_activas': 0}


def invalidar_cache_publico():
    """Invalida toda la caché del portal público."""
    cache.delete_pattern('publico_*') if hasattr(cache, 'delete_pattern') else None
    # Fallback: borrar claves conocidas
    for clave in (CACHE_KEY_REFUGIOS, CACHE_KEY_ZONAS, 'publico_home_stats'):
        cache.delete(clave)
    logger.info("Caché del portal público invalidada")