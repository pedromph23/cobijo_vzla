"""Throttles personalizados para la API.

DRF aplica estos límites por usuario (autenticado) o por IP (anónimo).
Usan el CACHES['default'] como backend.

Nota: con FileBasedCache y gunicorn multi-worker, cada worker mantiene su
propio contador. El rate efectivo es rate × workers. Se mitiga migrando
a Redis en FASE 5.
"""
from rest_framework.throttling import AnonRateThrottle


class ReporteCiudadanoThrottle(AnonRateThrottle):
    """Limita los reportes ciudadanos anónimos para prevenir spam.

    Rate configurado en settings.REST_FRAMEWORK['DEFAULT_THROTTLE_RATES'].
    """
    scope = 'reporte_ciudadano'


class MapaCalorPublicoThrottle(AnonRateThrottle):
    """Limita el cálculo del mapa de calor público (costoso en CPU)."""
    scope = 'mapa_calor_publico'


class BuscarLugarThrottle(AnonRateThrottle):
    """Limita el autocompletado de búsquedas públicas."""
    scope = 'buscar_lugar'
