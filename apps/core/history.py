"""
Historial temporal de entidades operativas.
"""
from __future__ import annotations

from decimal import Decimal
from django.contrib.gis.geos import GEOSGeometry
from django.forms.models import model_to_dict

from .models import RegistroVersion

MODELOS_HISTORICOS = {
    "apps.core.models.PuntoDemanda",
    "apps.core.models.SitioCandidato",
    "apps.core.models.RefugioExistente",
    "apps.core.models.ZonaAfectada",
    "apps.core.models.ParametrosModelo",
    "apps.emergencias.models.Evento",
}

def _serializar_valor(valor):
    if isinstance(valor, GEOSGeometry):
        return valor.geojson
    if isinstance(valor, Decimal):
        return str(valor)
    if hasattr(valor, "isoformat"):
        return valor.isoformat()
    if isinstance(valor, (list, tuple)):
        return [_serializar_valor(v) for v in valor]
    if isinstance(valor, dict):
        return {str(k): _serializar_valor(v) for k, v in valor.items()}
    return valor

def serializar_instancia(obj):
    datos = model_to_dict(obj)
    datos['id'] = obj.pk
    for nombre, valor in list(datos.items()):
        datos[nombre] = _serializar_valor(valor)
    return datos

def nombre_modelo(obj):
    return f"{obj._meta.app_label}.{obj._meta.model_name}"

def registrar_version(request, obj, operacion, datos=None):
    if nombre_modelo(obj) not in MODELOS_HISTORICOS:
        return None
    payload = datos if datos is not None else serializar_instancia(obj)
    return RegistroVersion.objects.create(
        usuario=(request.user if request is not None and getattr(request, "user", None) and request.user.is_authenticated else None),
        modelo=nombre_modelo(obj),
        objeto_id=str(obj.pk),
        operacion=operacion,
        datos=payload,
        ruta=request.path[:500] if request is not None else "",
        ip=request.META.get("REMOTE_ADDR") if request is not None else None,
    )

def estado_a_fecha(modelo, objeto_id, momento):
    return (
        RegistroVersion.objects
        .filter(modelo=modelo, objeto_id=str(objeto_id), fecha_version__lte=momento)
        .order_by("-fecha_version")
        .first()
    )
