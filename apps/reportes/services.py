"""
Servicios de consulta para generación de reportes.

Extrae la lógica de agregación de datos de `generador_reportes.py`
para mantenerlo testeable y evitar N+1 queries.
"""
from __future__ import annotations

import logging
from typing import Dict

import pandas as pd
from django.db.models import Count, Sum, Avg

from apps.core.models import (
    Estado, Parroquia, RefugioExistente, PuntoDemanda, ZonaAfectada,
)
from apps.emergencias.models import Evento
from apps.core.history import estado_a_fecha


logger = logging.getLogger(__name__)



def _historicos(modelo, as_of):
    """Última versión de cada objeto conocida a la fecha indicada."""
    from apps.core.models import RegistroVersion
    ids = (
        RegistroVersion.objects
        .filter(modelo=modelo, fecha_version__lte=as_of)
        .values_list('objeto_id', flat=True)
        .distinct()
    )
    resultado = []
    for objeto_id in ids:
        version = estado_a_fecha(modelo, objeto_id, as_of)
        if version and version.operacion != 'eliminado':
            resultado.append(version.datos)
    return resultado


def _df_historico_zonas(as_of):
    zonas = _historicos('core.zonaafectada', as_of)
    eventos = {str(v.get('id')): v for v in _historicos('emergencias.evento', as_of)}
    data = []
    for z in zonas:
        evento = eventos.get(str(z.get('evento')), {})
        data.append({
            'ID': z.get('id'),
            'Nombre': z.get('nombre', ''),
            'Evento': evento.get('nombre', 'Sin evento'),
            'Tipo Evento': evento.get('tipo', ''),
            'Nivel Alerta': str(z.get('nivel_alerta', '')).upper(),
            'Descripción': z.get('descripcion', ''),
            'Heridos': z.get('heridos', 0) or 0,
            'Fallecidos': z.get('fallecidos', 0) or 0,
            'Damnificados': z.get('damnificados', 0) or 0,
            'Fecha Inicio': str(z.get('fecha_inicio', '')),
            'Fecha Fin': str(z.get('fecha_fin', '')) if z.get('fecha_fin') else 'Activa',
        })
    return pd.DataFrame(data)


def _df_historico_simple(modelo, as_of, campos):
    rows = _historicos(modelo, as_of)
    return pd.DataFrame([{campo: row.get(campo) for campo in campos} for row in rows])


def resumen_general_historico(as_of):
    zonas = _historicos('core.zonaafectada', as_of)
    eventos = _historicos('emergencias.evento', as_of)
    refugios = _historicos('core.refugioexistente', as_of)
    demandas = _historicos('core.puntodemanda', as_of)
    return {
        'estados': Estado.objects.count(),
        'parroquias': Parroquia.objects.count(),
        'refugios': len(refugios),
        'demandas': len(demandas),
        'zonas': len(zonas),
        'eventos': len(eventos),
        'heridos': sum(z.get('heridos', 0) or 0 for z in zonas),
        'fallecidos': sum(z.get('fallecidos', 0) or 0 for z in zonas),
        'damnificados': sum(z.get('damnificados', 0) or 0 for z in zonas),
    }


# ============================================================
# DATAFRAMES BASE
# ============================================================

def df_zonas_afectadas(desde=None, hasta=None, as_of=None) -> pd.DataFrame:
    """DataFrame de zonas afectadas, opcionalmente filtrado por fecha/hora."""
    try:
        if as_of is not None:
            return _df_historico_zonas(as_of)
        qs = (
            ZonaAfectada.objects
            .select_related('evento')
            .only(
                'id', 'nombre', 'descripcion', 'nivel_alerta',
                'heridos', 'fallecidos', 'damnificados',
                'fecha_inicio', 'fecha_fin',
                'evento__nombre', 'evento__tipo',
            )
        )
        if desde is not None:
            qs = qs.filter(fecha_inicio__gte=desde)
        if hasta is not None:
            qs = qs.filter(fecha_inicio__lte=hasta)
        data = [
            {
                'ID': z.id,
                'Nombre': z.nombre,
                'Evento': z.evento.nombre if z.evento else 'Sin evento',
                'Tipo Evento': z.evento.tipo if z.evento else '',
                'Nivel Alerta': (z.nivel_alerta or '').upper(),
                'Descripción': z.descripcion or '',
                'Heridos': z.heridos or 0,
                'Fallecidos': z.fallecidos or 0,
                'Damnificados': z.damnificados or 0,
                'Fecha Inicio': (
                    z.fecha_inicio.strftime('%Y-%m-%d %H:%M')
                    if z.fecha_inicio else ''
                ),
                'Fecha Fin': (
                    z.fecha_fin.strftime('%Y-%m-%d %H:%M')
                    if z.fecha_fin else 'Activa'
                ),
            }
            for z in qs
        ]
        return pd.DataFrame(data)
    except Exception as e:
        logger.error(f"Error df_zonas_afectadas: {e}", exc_info=True)
        return pd.DataFrame()


def df_por_estado(desde=None, hasta=None, as_of=None) -> pd.DataFrame:
    """
    DataFrame agregado por estado.

    Optimizado: usa anotaciones en vez de N+1 queries.
    """
    try:
        if as_of is not None:
            return pd.DataFrame()
        # El filtro temporal afecta la información de zonas; el resto del estado
        # representa una fotografía territorial vigente.
        # Query principal: parroquias agregadas por estado
        estados_agg = (
            Estado.objects
            .annotate(
                n_parroquias=Count('parroquias', distinct=True),
                poblacion_total=Sum('parroquias__poblacion'),
                vulnerabilidad_prom=Avg('parroquias__indice_vulnerabilidad'),
            )
            .values(
                'id', 'nombre',
                'n_parroquias', 'poblacion_total', 'vulnerabilidad_prom',
            )
        )

        # Mapa de estado_id → {zonas: [...], heridos, fallecidos, damnificados}
        zonas_por_estado: Dict[int, Dict[str, int]] = {}
        zonas_qs = ZonaAfectada.objects
        if desde is not None:
            zonas_qs = zonas_qs.filter(fecha_inicio__gte=desde)
        if hasta is not None:
            zonas_qs = zonas_qs.filter(fecha_inicio__lte=hasta)
        for z in zonas_qs.only(
            'id', 'heridos', 'fallecidos', 'damnificados', 'geom'
        ).iterator(chunk_size=500):
            if not z.geom:
                continue
            try:
                estado = Estado.objects.filter(geom__contains=z.geom).first()
                if not estado:
                    continue
                agg = zonas_por_estado.setdefault(
                    estado.id,
                    {'zonas': 0, 'heridos': 0, 'fallecidos': 0, 'damnificados': 0},
                )
                agg['zonas'] += 1
                agg['heridos'] += z.heridos or 0
                agg['fallecidos'] += z.fallecidos or 0
                agg['damnificados'] += z.damnificados or 0
            except Exception:
                continue

        data = []
        for e in estados_agg:
            z_data = zonas_por_estado.get(e['id'], {})
            data.append({
                'Estado': e['nombre'],
                'Total Parroquias': e['n_parroquias'] or 0,
                'Población Total': e['poblacion_total'] or 0,
                'Total Zonas Afectadas': z_data.get('zonas', 0),
                'Heridos': z_data.get('heridos', 0),
                'Fallecidos': z_data.get('fallecidos', 0),
                'Damnificados': z_data.get('damnificados', 0),
                'Vulnerabilidad Promedio': round(e['vulnerabilidad_prom'] or 0, 4),
            })
        return pd.DataFrame(data)
    except Exception as e:
        logger.error(f"Error df_por_estado: {e}", exc_info=True)
        return pd.DataFrame()


def df_refugios(as_of=None) -> pd.DataFrame:
    """DataFrame de refugios existentes."""
    try:
        if as_of is not None:
            return _df_historico_simple('core.refugioexistente', as_of, ['id','nombre','direccion','capacidad_total','capacidad_disponible','servicios','operativo','telefono'])
        qs = RefugioExistente.objects.only(
            'id', 'nombre', 'direccion', 'capacidad_total',
            'capacidad_disponible', 'servicios', 'operativo', 'telefono',
        )
        data = []
        for r in qs:
            total = r.capacidad_total or 0
            disponible = r.capacidad_disponible or 0
            ocupacion = (
                round(((total - disponible) / total) * 100, 1)
                if total > 0 else 0.0
            )
            data.append({
                'ID': r.id,
                'Nombre': r.nombre,
                'Dirección': r.direccion,
                'Capacidad Total': total,
                'Capacidad Disponible': disponible,
                'Ocupación (%)': ocupacion,
                'Servicios': (
                    ', '.join(r.servicios)
                    if isinstance(r.servicios, list) else ''
                ),
                'Operativo': 'Sí' if r.operativo else 'No',
                'Teléfono': r.telefono or '',
            })
        return pd.DataFrame(data)
    except Exception as e:
        logger.error(f"Error df_refugios: {e}", exc_info=True)
        return pd.DataFrame()


def df_demandas(as_of=None) -> pd.DataFrame:
    """DataFrame de puntos de demanda."""
    try:
        if as_of is not None:
            return _df_historico_simple('core.puntodemanda', as_of, ['id','nombre','poblacion','vulnerabilidad'])
        qs = (
            PuntoDemanda.objects
            .select_related('parroquia', 'parroquia__estado')
            .only(
                'id', 'nombre', 'poblacion', 'vulnerabilidad',
                'parroquia__nombre', 'parroquia__estado__nombre',
            )
        )
        data = [
            {
                'ID': d.id,
                'Nombre': d.nombre,
                'Parroquia': d.parroquia.nombre if d.parroquia else '',
                'Estado': (
                    d.parroquia.estado.nombre
                    if d.parroquia and d.parroquia.estado else ''
                ),
                'Población': d.poblacion,
                'Vulnerabilidad': round(d.vulnerabilidad or 0, 3),
            }
            for d in qs
        ]
        return pd.DataFrame(data)
    except Exception as e:
        logger.error(f"Error df_demandas: {e}", exc_info=True)
        return pd.DataFrame()


def df_eventos(desde=None, hasta=None, as_of=None) -> pd.DataFrame:
    """DataFrame de eventos."""
    try:
        if as_of is not None:
            return _df_historico_simple('emergencias.evento', as_of, ['id','nombre','tipo','fecha','magnitud','descripcion','activo'])
        qs = Evento.objects.only(
            'id', 'nombre', 'tipo', 'fecha', 'magnitud',
            'descripcion', 'activo',
        )
        if desde is not None:
            qs = qs.filter(fecha__gte=desde)
        if hasta is not None:
            qs = qs.filter(fecha__lte=hasta)
        data = [
            {
                'ID': e.id,
                'Nombre': e.nombre,
                'Tipo': e.get_tipo_display(),
                'Fecha': e.fecha.strftime('%Y-%m-%d %H:%M') if e.fecha else '',
                'Magnitud': e.magnitud or 0,
                'Descripción': e.descripcion or '',
                'Activo': 'Sí' if e.activo else 'No',
            }
            for e in qs
        ]
        return pd.DataFrame(data)
    except Exception as e:
        logger.error(f"Error df_eventos: {e}", exc_info=True)
        return pd.DataFrame()


# ============================================================
# RESUMEN GENERAL
# ============================================================

def resumen_general(desde=None, hasta=None, as_of=None) -> Dict[str, int]:
    """Métricas globales para el reporte general."""
    try:
        if as_of is not None:
            return resumen_general_historico(as_of)
        zonas_qs = ZonaAfectada.objects.all()
        eventos_qs = Evento.objects.all()
        if desde is not None:
            zonas_qs = zonas_qs.filter(fecha_inicio__gte=desde)
            eventos_qs = eventos_qs.filter(fecha__gte=desde)
        if hasta is not None:
            zonas_qs = zonas_qs.filter(fecha_inicio__lte=hasta)
            eventos_qs = eventos_qs.filter(fecha__lte=hasta)
        return {
            'estados': Estado.objects.count(),
            'parroquias': Parroquia.objects.count(),
            'refugios': RefugioExistente.objects.count(),
            'demandas': PuntoDemanda.objects.count(),
            'zonas': zonas_qs.count(),
            'eventos': eventos_qs.count(),
            'heridos': (
                zonas_qs.aggregate(t=Sum('heridos'))['t'] or 0
            ),
            'fallecidos': (
                zonas_qs.aggregate(t=Sum('fallecidos'))['t'] or 0
            ),
            'damnificados': (
                zonas_qs.aggregate(t=Sum('damnificados'))['t'] or 0
            ),
        }
    except Exception as e:
        logger.error(f"Error resumen_general: {e}", exc_info=True)
        return {}