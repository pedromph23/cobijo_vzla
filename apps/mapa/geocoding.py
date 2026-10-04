"""Geocodificación centralizada para los formularios CRUD del mapa."""
from __future__ import annotations

import logging

from django.conf import settings
from django.core.cache import cache
from django.http import JsonResponse
from geopy.exc import GeocoderServiceError, GeocoderTimedOut
from geopy.geocoders import Nominatim
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated

logger = logging.getLogger(__name__)

_CACHE_TIMEOUT = 60 * 60 * 24
_GEOCODER = Nominatim(
    user_agent=getattr(
        settings,
        "COBIJO_GEOCODER_USER_AGENT",
        "CobijoVzla/1.0 (https://cobijo-vzla.onrender.com)",
    ),
    timeout=8,
)


def _cache_key(address: str) -> str:
    normalized = " ".join(address.lower().split())
    return f"cobijo:geocode:ve:{normalized}"


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def api_geocodificar_direccion(request):
    """Devuelve una única ubicación para una dirección dentro de Venezuela."""
    address = " ".join(request.query_params.get("direccion", "").split())
    if not address:
        return JsonResponse({"ok": False, "detail": "La dirección es obligatoria."}, status=400)
    if len(address) > 300:
        return JsonResponse({"ok": False, "detail": "La dirección es demasiado larga."}, status=400)

    key = _cache_key(address)
    cached = cache.get(key)
    if cached:
        return JsonResponse(cached)

    try:
        result = _GEOCODER.geocode(
            address,
            exactly_one=True,
            country_codes="ve",
            language="es",
            addressdetails=True,
        )
    except (GeocoderTimedOut, GeocoderServiceError) as exc:
        logger.warning("Geocodificación no disponible: %s", exc)
        return JsonResponse(
            {"ok": False, "detail": "No se pudo consultar el servicio de ubicación."},
            status=503,
        )
    except Exception:
        logger.exception("Error inesperado durante la geocodificación")
        return JsonResponse(
            {"ok": False, "detail": "No se pudo ubicar la dirección."},
            status=503,
        )

    if result is None:
        response = {
            "ok": False,
            "found": False,
            "detail": "No encontramos esa dirección en Venezuela.",
        }
        cache.set(key, response, _CACHE_TIMEOUT)
        return JsonResponse(response)

    lat = float(result.latitude)
    lng = float(result.longitude)
    response = {
        "ok": True,
        "found": True,
        "lat": lat,
        "lng": lng,
        "display_name": result.address,
    }
    cache.set(key, response, _CACHE_TIMEOUT)
    return JsonResponse(response)
