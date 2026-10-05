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
from django.utils import timezone

from apps.core.models import RefugioExistente, ZonaAfectada, Estado, Parroquia


logger = logging.getLogger(__name__)


CACHE_TTL_REFUGIOS = 300
CACHE_TTL_ZONAS = 180
CACHE_TTL_BUSQUEDA = 600
CACHE_KEY_REFUGIOS = 'publico_refugios'
# Versionar esta clave evita que un [] antiguo permanezca en Redis después de
# corregir la consulta o crear/actualizar zonas desde el panel administrativo.
CACHE_KEY_ZONAS = 'publico_zonas_v2'


def _serializar_refugio(r: RefugioExistente) -> Dict:
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
    """Serializa la zona completa, no solo su centroide."""
    if not z.geom:
        return None
    centro = z.geom.centroid
    ahora = timezone.now()
    return {
        'id': z.id,
        'nombre': z.nombre,
        'descripcion': z.descripcion,
        'nivel_alerta': z.nivel_alerta,
        'heridos': z.heridos,
        'fallecidos': z.fallecidos,
        'damnificados': z.damnificados,
        'lat': centro.y,
        'lng': centro.x,
        'fecha_inicio': z.fecha_inicio.isoformat() if z.fecha_inicio else None,
        'fecha_fin': z.fecha_fin.isoformat() if z.fecha_fin else None,
        'activa': bool(
            z.fecha_inicio <= ahora
            and (z.fecha_fin is None or z.fecha_fin >= ahora)
        ),
        'geojson': z.geom.geojson,
        'evento': z.evento.nombre if z.evento else None,
        'tipo_evento': z.evento.tipo if z.evento else None,
    }


def obtener_refugios_publicos(limite: int = 1000) -> List[Dict]:
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
        return data
    except Exception as e:
        logger.error(f"Error obteniendo refugios: {e}", exc_info=True)
        return []


def obtener_zonas_activas(limite: int = 500) -> List[Dict]:
    """Devuelve únicamente zonas vigentes y con geometría válida.

    Una zona sigue activa mientras su inicio ya haya ocurrido y su fecha de
    finalización sea nula o todavía no haya vencido. No se debe filtrar por
    ``fecha_fin IS NULL`` porque eso ocultaría zonas que tienen una fecha de
    finalización futura.
    """
    cache_key = f'{CACHE_KEY_ZONAS}_{limite}'
    cached = cache.get(cache_key)
    if cached is not None:
        return cached
    try:
        ahora = timezone.now()
        qs = (
            ZonaAfectada.objects
            .filter(
                fecha_inicio__lte=ahora,
                geom__isnull=False,
            )
            .filter(Q(fecha_fin__isnull=True) | Q(fecha_fin__gte=ahora))
            .select_related('evento')
            .only(
                'id', 'nombre', 'descripcion', 'nivel_alerta',
                'fecha_inicio', 'fecha_fin',
                'heridos', 'fallecidos', 'damnificados',
                'geom', 'evento__nombre', 'evento__tipo',
            )[:limite]
        )
        data = []
        for z in qs:
            try:
                serializada = _serializar_zona(z)
                if serializada:
                    data.append(serializada)
            except Exception:
                logger.warning(
                    'No se pudo serializar la geometría de la zona pública %s',
                    z.id,
                    exc_info=True,
                )
        cache.set(cache_key, data, CACHE_TTL_ZONAS)
        logger.info(f"Zonas activas: {len(data)} cacheadas por {CACHE_TTL_ZONAS}s")
        return data
    except Exception as e:
        logger.error(f"Error obteniendo zonas: {e}", exc_info=True)
        return []


def _normalizar_query(q: str) -> str:
    return (q or '').strip()[:100]


def buscar_lugares(query: str, limite_por_tipo: int = 5) -> List[Dict]:
    query = _normalizar_query(query)
    if len(query) < 2:
        return []

    cache_key = f'publico_busqueda_{hashlib.md5(query.lower().encode()).hexdigest()[:12]}'
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    resultados: List[Dict] = []
    try:
        parroquias = (
            Parroquia.objects
            .filter(nombre__icontains=query, geom__isnull=False)
            .select_related('estado')
            .only('id', 'nombre', 'geom', 'estado__nombre')[:limite_por_tipo]
        )
        for p in parroquias:
            c = p.geom.centroid
            resultados.append({
                'tipo': 'parroquia', 'nombre': p.nombre,
                'estado': f"Parroquia del Estado {p.estado.nombre}" if p.estado else 'Parroquia',
                'lat': c.y, 'lng': c.x,
            })

        estados = (
            Estado.objects
            .filter(nombre__icontains=query, geom__isnull=False)
            .only('id', 'nombre', 'geom')[:min(3, limite_por_tipo)]
        )
        for e in estados:
            c = e.geom.centroid
            resultados.append({
                'tipo': 'estado', 'nombre': e.nombre, 'estado': 'Estado',
                'lat': c.y, 'lng': c.x,
            })

        refugios = (
            RefugioExistente.objects
            .filter(
                Q(nombre__icontains=query) | Q(direccion__icontains=query),
                operativo=True, ubicacion__isnull=False,
            )
            .only('id', 'nombre', 'direccion', 'ubicacion')[:limite_por_tipo]
        )
        for r in refugios:
            resultados.append({
                'tipo': 'refugio', 'nombre': r.nombre,
                'estado': r.direccion or 'Refugio',
                'lat': r.ubicacion.y, 'lng': r.ubicacion.x,
            })

        cache.set(cache_key, resultados, CACHE_TTL_BUSQUEDA)
        return resultados
    except Exception as e:
        logger.error(f"Error en búsqueda '{query}': {e}", exc_info=True)
        return []


def obtener_estadisticas_home() -> Dict[str, int]:
    cache_key = 'publico_home_stats'
    cached = cache.get(cache_key)
    if cached is not None:
        return cached
    from apps.emergencias.models import Evento
    try:
        ahora = timezone.now()
        stats = {
            'eventos_activos': Evento.objects.filter(activo=True).count(),
            'total_refugios': RefugioExistente.objects.filter(operativo=True).count(),
            'zonas_activas': ZonaAfectada.objects.filter(
                fecha_inicio__lte=ahora,
            ).filter(Q(fecha_fin__isnull=True) | Q(fecha_fin__gte=ahora)).count(),
        }
        cache.set(cache_key, stats, CACHE_TTL_REFUGIOS)
        return stats
    except Exception as e:
        logger.error(f"Error en stats home: {e}", exc_info=True)
        return {'eventos_activos': 0, 'total_refugios': 0, 'zonas_activas': 0}


def invalidar_cache_publico():
    """Invalida tanto las claves base como las claves parametrizadas."""
    if hasattr(cache, 'delete_pattern'):
        cache.delete_pattern('publico_*')
    for clave in (
        CACHE_KEY_REFUGIOS,
        CACHE_KEY_REFUGIOS + '_1000',
        CACHE_KEY_ZONAS,
        CACHE_KEY_ZONAS + '_500',
        'publico_zonas_500',
        'publico_home_stats',
    ):
        cache.delete(clave)
    logger.info("Caché del portal público invalidada")
