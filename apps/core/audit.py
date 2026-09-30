"""Servicio centralizado de auditoría para CobijoVzla."""

from __future__ import annotations

from datetime import date, datetime, time
from decimal import Decimal
from typing import Any
import logging

from django.contrib.auth.signals import (
    user_logged_in,
    user_logged_out,
    user_login_failed,
)
from django.dispatch import receiver
from django.utils import timezone

from .models import AuditLog


logger = logging.getLogger(__name__)


# ============================================================
# ACCIONES DE AUDITORÍA
# ============================================================

ACCION_LOGIN = "LOGIN"
ACCION_LOGOUT = "LOGOUT"
ACCION_LOGIN_FALLIDO = "LOGIN_FAILED"

ACCION_CREATE = "CREATE"
ACCION_UPDATE = "UPDATE"
ACCION_DELETE = "DELETE"

ACCION_IMPORT = "IMPORT"
ACCION_EXPORT = "EXPORT"

ACCION_OPTIMIZATION = "OPTIMIZATION"
ACCION_COMMAND = "COMMAND"
ACCION_REPORT = "REPORT"


# ============================================================
# CAMPOS SENSIBLES
# ============================================================

_SENSITIVE_KEYS = {
    "password",
    "password1",
    "password2",
    "token",
    "access_token",
    "refresh_token",
    "secret",
    "secret_key",
    "api_key",
    "authorization",
    "cookie",
    "csrfmiddlewaretoken",
}


# ============================================================
# SANITIZACIÓN
# ============================================================

def sanitizar_datos(valor: Any) -> Any:
    """
    Convierte datos a un formato compatible con JSON
    y elimina información sensible.
    """

    if isinstance(valor, dict):
        return {
            str(k): sanitizar_datos(v)
            for k, v in valor.items()
            if str(k).lower() not in _SENSITIVE_KEYS
        }

    if isinstance(valor, (list, tuple, set)):
        return [sanitizar_datos(v) for v in valor]

    if isinstance(valor, (datetime, date, time)):
        return valor.isoformat()

    if isinstance(valor, Decimal):
        return str(valor)

    if valor is None or isinstance(valor, (str, int, float, bool)):
        return valor

    # GeoDjango / GEOS
    if hasattr(valor, "wkt"):
        return valor.wkt

    # Archivos
    if (
        hasattr(valor, "name")
        and valor.__class__.__name__ in {"ImageFieldFile", "FieldFile"}
    ):
        return valor.name or ""

    return str(valor)


# ============================================================
# SERIALIZACIÓN DE MODELOS
# ============================================================

def serializar_instancia(objeto) -> dict[str, Any]:
    """
    Obtiene una fotografía JSON segura de los campos persistidos
    de una instancia Django.
    """

    datos = {}

    for field in objeto._meta.concrete_fields:
        nombre = field.name

        if nombre.lower() in _SENSITIVE_KEYS:
            continue

        try:
            datos[nombre] = sanitizar_datos(
                field.value_from_object(objeto)
            )
        except Exception:
            datos[nombre] = "<no disponible>"

    return datos


# ============================================================
# OBTENER IP DEL CLIENTE
# ============================================================

def _ip_cliente(request) -> str | None:
    """
    Obtiene la IP del cliente.

    X-Forwarded-For solo debe considerarse confiable cuando
    la aplicación está detrás de un proxy controlado.
    """

    if request is None:
        return None

    try:
        forwarded = request.META.get("HTTP_X_FORWARDED_FOR")

        if forwarded:
            return forwarded.split(",")[0].strip() or None

        return request.META.get("REMOTE_ADDR") or None

    except Exception:
        return None


# ============================================================
# REGISTRAR AUDITORÍA
# ============================================================

def registrar_auditoria(
    request,
    accion: str,
    objeto=None,
    *,
    descripcion: str = "",
    datos_anteriores: Any = None,
    datos_nuevos: Any = None,
    resultado: str = "exitoso",
    modelo: str = "",
    objeto_id: str = "",
    usuario=None,
) -> AuditLog | None:
    """
    Registra un evento de auditoría.

    La auditoría nunca debe romper la operación principal.
    Si la auditoría falla, se registra el problema en los logs
    y la función devuelve None.
    """

    try:

        # ----------------------------------------------------
        # USUARIO
        # ----------------------------------------------------

        if usuario is None:
            usuario = (
                getattr(request, "user", None)
                if request is not None
                else None
            )

            if (
                usuario is not None
                and not getattr(usuario, "is_authenticated", False)
            ):
                usuario = None

        # ----------------------------------------------------
        # OBJETO
        # ----------------------------------------------------

        objeto_repr = ""

        if objeto is not None:
            meta = objeto._meta

            # label_lower => core.estado
            # en lugar de core.Estado
            modelo = modelo or meta.label_lower

            objeto_id = (
                objeto_id
                or str(getattr(objeto, "pk", "") or "")
            )

            objeto_repr = str(objeto)[:255]

        # ----------------------------------------------------
        # CONTEXTO HTTP
        # ----------------------------------------------------

        # IMPORTANTE:
        # getattr() puede devolver None si el atributo existe
        # pero su valor es None. Por eso utilizamos "or """.
        metodo_http = getattr(request, "method", "") or ""

        ruta = getattr(request, "path", "") or ""

        user_agent = ""

        if request is not None:
            try:
                user_agent = (
                    request.META.get("HTTP_USER_AGENT", "")
                    or ""
                )
            except Exception:
                user_agent = ""

        # ----------------------------------------------------
        # SANITIZACIÓN PREVIA
        # ----------------------------------------------------

        datos_anteriores_seguro = sanitizar_datos(
            datos_anteriores
        )

        datos_nuevos_seguro = sanitizar_datos(
            datos_nuevos
        )

        # ----------------------------------------------------
        # CREAR REGISTRO
        # ----------------------------------------------------

        registro = AuditLog.objects.create(
            usuario=usuario,
            accion=str(accion or "")[:50],

            modelo=str(modelo or "")[:150],

            objeto_id=str(objeto_id or "")[:100],

            objeto_repr=str(objeto_repr or "")[:255],

            descripcion=str(descripcion or "")[:500],

            ip=_ip_cliente(request),

            metodo_http=str(metodo_http or "")[:10],

            ruta=str(ruta or "")[:500],

            user_agent=str(user_agent or "")[:1000],

            datos_anteriores=datos_anteriores_seguro,

            datos_nuevos=datos_nuevos_seguro,

            resultado=str(resultado or "")[:20],

            fecha_hora=timezone.now(),
        )

        return registro

    except Exception:
        # La auditoría nunca debe tumbar la operación principal.
        # El fallo sí debe quedar registrado para diagnóstico.
        logger.exception(
            "No se pudo registrar un evento de auditoría"
        )

        return None


# ============================================================
# LOGIN
# ============================================================

@receiver(user_logged_in)
def auditar_login(sender, request, user, **kwargs):
    """
    Registra un inicio de sesión exitoso.
    """

    registrar_auditoria(
        request=request,
        accion=ACCION_LOGIN,
        objeto=user,
        usuario=user,
        descripcion="Inicio de sesión",
        resultado="exitoso",
    )


# ============================================================
# LOGOUT
# ============================================================

@receiver(user_logged_out)
def auditar_logout(sender, request, user, **kwargs):
    """
    Registra un cierre de sesión.

    request puede ser None dependiendo del flujo utilizado.
    """

    registrar_auditoria(
        request=request,
        accion=ACCION_LOGOUT,
        objeto=user,
        usuario=user,
        descripcion="Cierre de sesión",
        resultado="exitoso",
    )


# ============================================================
# LOGIN FALLIDO
# ============================================================

@receiver(user_login_failed)
def auditar_login_fallido(
    sender,
    credentials,
    request,
    **kwargs,
):
    """
    Registra intentos fallidos sin almacenar la contraseña
    ni otras credenciales sensibles.
    """

    username = (
        credentials.get("username")
        or credentials.get("email")
        or "usuario no identificado"
    )

    registrar_auditoria(
        request=request,
        accion=ACCION_LOGIN_FALLIDO,
        descripcion=(
            "Intento de inicio de sesión fallido para "
            f"{str(username)[:100]}"
        ),
        resultado="fallido",
    )
