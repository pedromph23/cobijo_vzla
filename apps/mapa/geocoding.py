"""Geocodificación centralizada para los formularios CRUD del mapa."""
from __future__ import annotations

import logging
import re
import unicodedata
from difflib import SequenceMatcher

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

_GENERIC_WORDS = {
    "av",
    "avenida",
    "barrio",
    "calle",
    "carretera",
    "ciudad",
    "colegio",
    "escuela",
    "instituto",
    "liceo",
    "nacional",
    "parroquia",
    "unidad",
    "educativa",
    "bolivariano",
    "bolivariana",
    "venezuela",
}


def _normalizar_texto(value: str) -> str:
    value = unicodedata.normalize("NFKD", value or "")
    value = "".join(char for char in value if not unicodedata.combining(char))
    value = re.sub(r"[^a-z0-9\s]", " ", value.lower())
    return " ".join(value.split())


def _cache_key(address: str) -> str:
    normalized = _normalizar_texto(address)
    return f"cobijo:geocode:ve:{normalized}"


def _resultado_score(query: str, result) -> float:
    """Prioriza coincidencias de nombre sin perder el ranking geográfico de Nominatim."""
    raw = getattr(result, "raw", {}) or {}
    query_normalizado = _normalizar_texto(query)
    query_tokens = set(query_normalizado.split()) - _GENERIC_WORDS

    nombres = []
    nombre_principal = raw.get("name")
    if nombre_principal:
        nombres.append(str(nombre_principal))
    for value in (raw.get("namedetails") or {}).values():
        if value:
            nombres.append(str(value))
    display_name = getattr(result, "address", None) or raw.get("display_name") or ""
    nombres.append(str(display_name))

    mejor = 0.0
    for nombre in nombres:
        normalizado = _normalizar_texto(nombre)
        if not normalizado:
            continue
        similitud = SequenceMatcher(None, query_normalizado, normalizado).ratio()
        tokens = set(normalizado.split())
        coincidencias = len(query_tokens & tokens) / max(len(query_tokens), 1)
        contiene = 1.0 if query_normalizado in normalizado else 0.0
        mejor = max(mejor, (similitud * 0.45) + (coincidencias * 0.45) + (contiene * 0.10))

    # Los POI tienen prioridad frente a resultados administrativos genéricos.
    categoria = str(raw.get("class") or raw.get("category") or "")
    tipo = str(raw.get("type") or "")
    if categoria in {"amenity", "building", "shop", "tourism", "leisure", "office"}:
        mejor += 0.12
    if tipo in {"school", "college", "university", "kindergarten"}:
        mejor += 0.12

    return mejor + (float(raw.get("importance") or 0) * 0.05)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def api_geocodificar_direccion(request):
    """Devuelve la mejor ubicación encontrada en Venezuela para un texto de lugar."""
    address = " ".join(request.query_params.get("direccion", "").split())
    if not address:
        return JsonResponse({"ok": False, "detail": "La dirección o nombre del lugar es obligatorio."}, status=400)
    if len(address) > 300:
        return JsonResponse({"ok": False, "detail": "La dirección o nombre del lugar es demasiado largo."}, status=400)

    key = _cache_key(address)
    cached = cache.get(key)
    if cached:
        return JsonResponse(cached)

    query = address if "venezuela" in _normalizar_texto(address) else f"{address}, Venezuela"

    try:
        results = _GEOCODER.geocode(
            query,
            exactly_one=False,
            limit=8,
            country_codes="ve",
            language="es",
            addressdetails=True,
            namedetails=True,
        ) or []
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

    if not results:
        response = {
            "ok": False,
            "found": False,
            "detail": "No encontramos ese lugar en Venezuela. Puedes seleccionar el punto directamente en el mapa.",
        }
        cache.set(key, response, _CACHE_TIMEOUT)
        return JsonResponse(response)

    result = max(results, key=lambda item: _resultado_score(address, item))
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
