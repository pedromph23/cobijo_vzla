"""Proxy de cálculo de rutas para el mapa público.

El navegador no depende directamente de un servicio de routing externo.
Render/Django consulta el motor de rutas y devuelve un payload pequeño y
compatible con Leaflet Routing Machine. Esto evita problemas de CORS,
timeouts y bloqueos indefinidos del cliente.
"""
from __future__ import annotations

import json
import logging
from math import isfinite
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

from django.http import JsonResponse
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework import status

logger = logging.getLogger(__name__)

VE_BOUNDS = {
    "south": 0.60,
    "west": -73.50,
    "north": 12.25,
    "east": -58.05,
}

ROUTERS = (
    "https://router.project-osrm.org/route/v1/driving/",
    "https://routing.openstreetmap.de/routed-car/route/v1/driving/",
)


def _numero(value):
    try:
        value = float(value)
    except (TypeError, ValueError):
        return None
    return value if isfinite(value) else None


def _en_venezuela(lat, lng):
    return (
        VE_BOUNDS["south"] <= lat <= VE_BOUNDS["north"]
        and VE_BOUNDS["west"] <= lng <= VE_BOUNDS["east"]
    )


def _texto_paso(step):
    maneuver = step.get("maneuver") or {}
    tipo = str(maneuver.get("type") or "").lower()
    modifier = str(maneuver.get("modifier") or "").lower()
    nombre = str(step.get("name") or "").strip()
    hacia = f" hacia {nombre}" if nombre else ""

    if tipo == "arrive":
        return "Ha llegado a su destino"
    if tipo in {"depart", "new name"}:
        return f"Continúe por {nombre}" if nombre else "Inicie la ruta y continúe"
    if tipo in {"merge"}:
        return f"Incorpórese a {nombre}" if nombre else "Incorpórese a la vía"
    if tipo in {"fork", "on ramp", "off ramp"}:
        return f"Tome la salida{hacia}" if tipo == "off ramp" else f"Tome la bifurcación{hacia}"
    if tipo in {"roundabout", "rotary"}:
        salida = maneuver.get("exit")
        extra = f" y tome la salida {salida}" if salida else ""
        return f"Entre en la rotonda{extra}{hacia}"
    if tipo == "continue":
        return f"Continúe por {nombre}" if nombre else "Continúe recto"

    giros = {
        "left": "Gire a la izquierda",
        "right": "Gire a la derecha",
        "slight left": "Gire ligeramente a la izquierda",
        "slight right": "Gire ligeramente a la derecha",
        "sharp left": "Gire fuertemente a la izquierda",
        "sharp right": "Gire fuertemente a la derecha",
        "uturn": "Realice un cambio de sentido",
    }
    if modifier in giros:
        return f"{giros[modifier]}{hacia}"

    return f"Continúe por {nombre}" if nombre else "Continúe por la ruta indicada"


def _indice_mas_cercano(coordenadas, lng, lat):
    if not coordenadas:
        return 0
    mejor = 0
    distancia = float("inf")
    for indice, punto in enumerate(coordenadas):
        try:
            dlng = float(punto[0]) - lng
            dlat = float(punto[1]) - lat
            actual = dlng * dlng + dlat * dlat
        except (TypeError, ValueError, IndexError):
            continue
        if actual < distancia:
            distancia = actual
            mejor = indice
    return mejor


def _normalizar_osrm(payload):
    rutas = payload.get("routes") or []
    if not rutas:
        raise ValueError("El motor de rutas no encontró una ruta.")

    ruta = rutas[0]
    geometria = ((ruta.get("geometry") or {}).get("coordinates") or [])
    if len(geometria) < 2:
        raise ValueError("La ruta devuelta no contiene una geometría válida.")

    coordenadas = [[float(p[1]), float(p[0])] for p in geometria]
    instrucciones = []
    for leg in ruta.get("legs") or []:
        for step in leg.get("steps") or []:
            maneuver = step.get("maneuver") or {}
            location = maneuver.get("location") or [geometria[0][0], geometria[0][1]]
            instrucciones.append({
                "text": _texto_paso(step),
                "distance": float(step.get("distance") or 0),
                "time": float(step.get("duration") or 0),
                "index": _indice_mas_cercano(geometria, float(location[0]), float(location[1])),
                "type": str(maneuver.get("type") or "continue"),
                "modifier": str(maneuver.get("modifier") or ""),
                "road": str(step.get("name") or "").strip(),
            })

    return {
        "summary": {
            "totalDistance": float(ruta.get("distance") or 0),
            "totalTime": float(ruta.get("duration") or 0),
        },
        "coordinates": coordenadas,
        "instructions": instrucciones,
    }


def _consultar_motor(origen_lat, origen_lng, destino_lat, destino_lng):
    coordenadas = f"{origen_lng:.6f},{origen_lat:.6f};{destino_lng:.6f},{destino_lat:.6f}"
    consulta = "?overview=full&geometries=geojson&steps=true&alternatives=false&annotations=false"
    ultimo_error = None

    for base in ROUTERS:
        url = base + quote(coordenadas, safe=";,.-") + consulta
        try:
            request = Request(
                url,
                headers={
                    "Accept": "application/json",
                    "User-Agent": "CobijoVzla/1.0 routing proxy",
                },
            )
            with urlopen(request, timeout=7) as response:
                payload = json.loads(response.read().decode("utf-8"))
            if payload.get("code") != "Ok":
                raise ValueError(payload.get("message") or "Motor de rutas sin resultado")
            return _normalizar_osrm(payload)
        except (HTTPError, URLError, TimeoutError, OSError, ValueError, json.JSONDecodeError) as exc:
            ultimo_error = exc
            logger.warning("Motor de rutas no disponible (%s): %s", base, exc)

    raise RuntimeError("No fue posible calcular la ruta en los motores disponibles.") from ultimo_error


@api_view(["GET"])
@permission_classes([AllowAny])
def api_ruta_publica(request):
    """Calcula una ruta dentro de Venezuela con timeout y fallback."""
    origen_lat = _numero(request.query_params.get("origen_lat"))
    origen_lng = _numero(request.query_params.get("origen_lng"))
    destino_lat = _numero(request.query_params.get("destino_lat"))
    destino_lng = _numero(request.query_params.get("destino_lng"))

    puntos = (
        (origen_lat, origen_lng, "tu ubicación"),
        (destino_lat, destino_lng, "el destino"),
    )
    for lat, lng, etiqueta in puntos:
        if lat is None or lng is None:
            return JsonResponse({"error": f"Coordenadas inválidas para {etiqueta}."}, status=status.HTTP_400_BAD_REQUEST)
        if not _en_venezuela(lat, lng):
            return JsonResponse({"error": f"{etiqueta.capitalize()} está fuera del área de cobertura de Venezuela."}, status=status.HTTP_400_BAD_REQUEST)

    try:
        ruta = _consultar_motor(origen_lat, origen_lng, destino_lat, destino_lng)
        return JsonResponse({"ok": True, "ruta": ruta})
    except Exception:
        logger.exception("Error calculando ruta pública")
        return JsonResponse(
            {"ok": False, "error": "No fue posible calcular la ruta en este momento. Inténtalo nuevamente en unos segundos."},
            status=status.HTTP_503_SERVICE_UNAVAILABLE,
        )
