"""
Servicios del panel administrativo.

Extrae la lógica de negocio de las vistas para mantener los controladores
delgados y testeables.
"""
from typing import Dict, List

from django.db.models import Count, Sum, Q
from django.utils import timezone
import logging

from apps.core.models import (
    PuntoDemanda,
    SitioCandidato,
    RefugioExistente,
    ZonaAfectada,
    Estado,
    Parroquia,
)
from apps.emergencias.models import Evento, Reporte


logger = logging.getLogger(__name__)


# ============================================================
# ESTADÍSTICAS
# ============================================================

def obtener_estadisticas() -> Dict[str, int]:
    """Estadísticas agregadas del sistema."""
    try:
        hoy = timezone.now().date()
        return {
            'estados': Estado.objects.count(),
            'parroquias': Parroquia.objects.count(),
            'puntos_demanda': PuntoDemanda.objects.count(),
            'sitios_candidatos': SitioCandidato.objects.filter(disponible=True).count(),
            'refugios': RefugioExistente.objects.filter(operativo=True).count(),
            'zonas_afectadas': ZonaAfectada.objects.filter(fecha_fin__isnull=True).count(),
            'eventos_activos': Evento.objects.filter(activo=True).count(),
            'reportes_recientes': Reporte.objects.filter(fecha__date=hoy).count(),
        }
    except Exception as e:
        logger.error(f"Error obteniendo estadísticas: {e}", exc_info=True)
        return {
            'estados': 0, 'parroquias': 0, 'puntos_demanda': 0,
            'sitios_candidatos': 0, 'refugios': 0, 'zonas_afectadas': 0,
            'eventos_activos': 0, 'reportes_recientes': 0,
        }


# ============================================================
# DATOS DEL MAPA
# ============================================================

def _serializar_puntos_demanda(limite: int) -> List[Dict]:
    """Serializa puntos de demanda usando .only() para reducir carga."""
    qs = PuntoDemanda.objects.only(
        'id', 'nombre', 'ubicacion', 'poblacion', 'vulnerabilidad'
    )[:limite]
    return [
        {
            'id': p.id,
            'nombre': p.nombre,
            'lat': p.ubicacion.y if p.ubicacion else None,
            'lng': p.ubicacion.x if p.ubicacion else None,
            'poblacion': p.poblacion,
            'vulnerabilidad': p.vulnerabilidad,
        }
        for p in qs
    ]


def _serializar_sitios_candidatos(limite: int) -> List[Dict]:
    qs = SitioCandidato.objects.filter(disponible=True).only(
        'id', 'nombre', 'ubicacion', 'capacidad_maxima'
    )[:limite]
    return [
        {
            'id': s.id,
            'nombre': s.nombre,
            'lat': s.ubicacion.y if s.ubicacion else None,
            'lng': s.ubicacion.x if s.ubicacion else None,
            'capacidad_maxima': s.capacidad_maxima,
        }
        for s in qs
    ]


def _serializar_refugios(limite: int) -> List[Dict]:
    qs = RefugioExistente.objects.only(
        'id', 'nombre', 'ubicacion', 'capacidad_disponible', 'operativo'
    )[:limite]
    return [
        {
            'id': r.id,
            'nombre': r.nombre,
            'lat': r.ubicacion.y if r.ubicacion else None,
            'lng': r.ubicacion.x if r.ubicacion else None,
            'capacidad_disponible': r.capacidad_disponible,
            'operativo': r.operativo,
        }
        for r in qs
    ]


def _serializar_zonas(limite: int) -> List[Dict]:
    """Serializa las zonas registradas para el mapa administrativo."""
    ahora = timezone.now()
    qs = (
        ZonaAfectada.objects
        .select_related('evento')
        .only(
            'id', 'nombre', 'descripcion', 'nivel_alerta',
            'fecha_inicio', 'fecha_fin',
            'heridos', 'fallecidos', 'damnificados', 'geom',
            'evento__nombre', 'evento__tipo',
        )[:limite]
    )

    data = []
    for z in qs:
        if not z.geom:
            continue
        try:
            data.append({
                'id': z.id,
                'nombre': z.nombre,
                'descripcion': z.descripcion,
                'nivel_alerta': z.nivel_alerta,
                'heridos': z.heridos,
                'fallecidos': z.fallecidos,
                'damnificados': z.damnificados,
                'fecha_inicio': z.fecha_inicio.isoformat() if z.fecha_inicio else None,
                'fecha_fin': z.fecha_fin.isoformat() if z.fecha_fin else None,
                'activa': bool(
                    z.fecha_inicio <= ahora
                    and (z.fecha_fin is None or z.fecha_fin >= ahora)
                ),
                'geojson': z.geom.geojson,
            })
        except Exception:
            logger.warning(
                'No se pudo serializar la geometría de la zona %s',
                z.id,
                exc_info=True,
            )

    return data


def _cargar_capa(nombre: str, serializador, limite: int) -> tuple[List[Dict], str | None]:
    """Carga una capa sin permitir que su fallo rompa las demás."""
    try:
        return serializador(limite), None
    except Exception as exc:
        logger.error('Error cargando capa %s: %s', nombre, exc, exc_info=True)
        return [], nombre


def obtener_datos_mapa(limite_por_capa: int = 500) -> Dict[str, List[Dict]]:
    """Devuelve las capas del mapa de forma independiente.

    Un problema en una capa no debe convertir todo el endpoint en HTTP 500.
    La capa problemática queda vacía y el error queda registrado para
    diagnóstico en servidor.
    """
    capas = (
        ('puntos_demanda', _serializar_puntos_demanda, limite_por_capa),
        ('sitios_candidatos', _serializar_sitios_candidatos, limite_por_capa),
        ('refugios', _serializar_refugios, limite_por_capa),
        ('zonas_afectadas', _serializar_zonas, min(limite_por_capa, 200)),
    )

    datos: Dict[str, List[Dict]] = {}
    errores: List[str] = []

    for nombre, serializador, limite in capas:
        datos[nombre], error = _cargar_capa(nombre, serializador, limite)
        if error:
            errores.append(error)

    if errores:
        logger.warning('Capas con error en mapa administrativo: %s', ', '.join(errores))

    return datos


# ============================================================
# EXPORTACIONES
# ============================================================

def construir_geojson_centros(datos_json: Dict) -> Dict:
    """Convierte los centros de un resultado en GeoJSON."""
    features = []
    for centro in datos_json.get('centros', []):
        lat = centro.get('lat')
        lng = centro.get('lng')
        if lat is None or lng is None:
            continue
        features.append({
            'type': 'Feature',
            'geometry': {'type': 'Point', 'coordinates': [lng, lat]},
            'properties': {
                'nombre': centro.get('nombre', ''),
                'id': centro.get('id'),
                'capacidad_maxima': centro.get('capacidad_maxima'),
                'demanda_asignada': centro.get('demanda_asignada', 0),
            },
        })
    return {'type': 'FeatureCollection', 'features': features}
