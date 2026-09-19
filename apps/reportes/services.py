"""
Servicios de consulta para generación de reportes.

Extrae la lógica de agregación de datos de `generador_reportes.py`
para mantenerlo testeable y evitar N+1 queries.
"""
from __future__ import annotations

import logging
from typing import Dict, List

import pandas as pd
from django.db.models import Count, Sum, Avg
from django.utils import timezone

from apps.core.models import (
    Estado, Parroquia, RefugioExistente, PuntoDemanda, ZonaAfectada,
)
from apps.emergencias.models import Evento


logger = logging.getLogger(__name__)


# ============================================================
# DATAFRAMES BASE
# ============================================================

def df_zonas_afectadas() -> pd.DataFrame:
    """DataFrame de zonas afectadas (una fila por zona)."""
    try:
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


def df_por_estado() -> pd.DataFrame:
    """
    DataFrame agregado por estado.

    Optimizado: usa anotaciones en vez de N+1 queries.
    """
    try:
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
        for z in ZonaAfectada.objects.only(
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


def df_refugios() -> pd.DataFrame:
    """DataFrame de refugios existentes."""
    try:
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


def df_demandas() -> pd.DataFrame:
    """DataFrame de puntos de demanda."""
    try:
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


def df_eventos() -> pd.DataFrame:
    """DataFrame de eventos."""
    try:
        qs = Evento.objects.only(
            'id', 'nombre', 'tipo', 'fecha', 'magnitud',
            'descripcion', 'activo',
        )
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

def resumen_general() -> Dict[str, int]:
    """Métricas globales para el reporte general."""
    try:
        return {
            'estados': Estado.objects.count(),
            'parroquias': Parroquia.objects.count(),
            'refugios': RefugioExistente.objects.count(),
            'demandas': PuntoDemanda.objects.count(),
            'zonas': ZonaAfectada.objects.count(),
            'eventos': Evento.objects.count(),
            'heridos': (
                ZonaAfectada.objects.aggregate(t=Sum('heridos'))['t'] or 0
            ),
            'fallecidos': (
                ZonaAfectada.objects.aggregate(t=Sum('fallecidos'))['t'] or 0
            ),
            'damnificados': (
                ZonaAfectada.objects.aggregate(t=Sum('damnificados'))['t'] or 0
            ),
        }
    except Exception as e:
        logger.error(f"Error resumen_general: {e}", exc_info=True)
        return {}