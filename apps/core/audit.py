"""
Servicios de auditoría central de CobijoVzla.
"""
import logging

from .models import RegistroAuditoria

logger = logging.getLogger(__name__)


def ip_cliente(request):
    """Obtiene la IP del cliente real, considerando proxies.

    En Render, el servidor está detrás de un proxy SSL. La IP real del
    cliente viene en X-Forwarded-For. Tomamos la primera IP de la lista
    (el cliente original) porque Render reenvía la cadena completa.

    En local, REMOTE_ADDR es la IP real.
    """
    if not request:
        return None

    # Django solo expone X-Forwarded-For si USE_X_FORWARDED_HOST está
    # activo o si el proxy lo pasa. Consultamos META directamente.
    xff = request.META.get('HTTP_X_FORWARDED_FOR', '')
    if xff:
        # XFF puede ser "cliente, proxy1, proxy2". Tomamos el primero.
        primera = xff.split(',')[0].strip()
        if primera:
            return primera

    # Fallback: IP del socket (localhost, desarrollo).
    return request.META.get('REMOTE_ADDR')


def registrar_auditoria(
    request,
    *,
    accion,
    resultado='exitoso',
    detalle='',
    modelo='',
    objeto_id='',
    datos_anteriores=None,
    datos_nuevos=None,
):
    """Registra una acción sin capturar secretos ni cuerpos de solicitudes."""
    try:
        return RegistroAuditoria.objects.create(
            usuario=request.user if getattr(request, 'user', None) and request.user.is_authenticated else None,
            accion=accion[:80],
            metodo=request.method[:10],
            ruta=request.path[:500],
            modelo=modelo[:150],
            objeto_id=str(objeto_id)[:100],
            resultado=resultado,
            detalle=detalle,
            datos_anteriores=datos_anteriores,
            datos_nuevos=datos_nuevos,
            ip=ip_cliente(request),
            user_agent=request.META.get('HTTP_USER_AGENT', '')[:500],
        )
    except Exception:
        logger.exception('No se pudo registrar el evento de auditoría.')
        return None
