"""
Vistas del módulo de reportes.

Genera y sirve archivos Excel/PDF. La lógica de generación vive en
`generador_reportes.py`; aquí solo se orquesta y se asegura la
descarga segura.
"""
import logging
import os
import time as time_module
from datetime import datetime, time

from django.conf import settings
from django.http import FileResponse, JsonResponse
from django.shortcuts import render
from django.utils import timezone
from django.utils.dateparse import parse_date, parse_time
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework import status

from apps.mapa.decorators import gestor_requerido
from apps.core.audit import registrar_auditoria

from .models import RegistroReporte

from .generador_reportes import (
    EXTENSIONES_PERMITIDAS,
    limpiar_reportes_antiguos,
    generar_excel_zonas_afectadas,
    generar_excel_estadisticas_generales,
    generar_pdf_zonas_afectadas,
    generar_pdf_estadisticas_generales,
)


logger = logging.getLogger(__name__)


# Tipos de reporte soportados
TIPOS_VALIDOS = {
    ('excel', 'zonas'): generar_excel_zonas_afectadas,
    ('excel', 'general'): generar_excel_estadisticas_generales,
    ('pdf', 'zonas'): generar_pdf_zonas_afectadas,
    ('pdf', 'general'): generar_pdf_estadisticas_generales,
}




def _parsear_filtro_historico(request):
    fecha = request.query_params.get('fecha_historica', '').strip()
    hora = request.query_params.get('hora_historica', '').strip()
    if not fecha:
        return None, ['La fecha histórica es obligatoria.']
    d = parse_date(fecha)
    h = parse_time(hora) if hora else time.max
    errores = []
    if not d:
        errores.append('fecha_historica inválida; use AAAA-MM-DD.')
    if hora and not h:
        errores.append('hora_historica inválida; use HH:MM.')
    if errores:
        return None, errores
    return timezone.make_aware(datetime.combine(d, h)), []

def _parsear_filtro_temporal(request):
    """Convierte filtros de fecha/hora en un intervalo timezone-aware."""
    fecha = request.query_params.get('fecha', '').strip()
    fecha_desde = request.query_params.get('fecha_desde', '').strip()
    fecha_hasta = request.query_params.get('fecha_hasta', '').strip()
    hora_desde = request.query_params.get('hora_desde', '').strip()
    hora_hasta = request.query_params.get('hora_hasta', '').strip()
    errores = []
    if fecha:
        fecha_desde = fecha_hasta = fecha
    d_desde = parse_date(fecha_desde) if fecha_desde else None
    d_hasta = parse_date(fecha_hasta) if fecha_hasta else None
    parsed_h_desde = parse_time(hora_desde) if hora_desde else time.min
    parsed_h_hasta = parse_time(hora_hasta) if hora_hasta else time.max
    if fecha_desde and not d_desde:
        errores.append('fecha_desde inválida; use AAAA-MM-DD.')
    if fecha_hasta and not d_hasta:
        errores.append('fecha_hasta inválida; use AAAA-MM-DD.')
    if hora_desde and not d_desde:
        errores.append('hora_desde requiere una fecha_desde.')
    if hora_hasta and not d_hasta:
        errores.append('hora_hasta requiere una fecha_hasta.')
    if hora_desde and not parsed_h_desde:
        errores.append('hora_desde inválida; use HH:MM.')
    if hora_hasta and not parsed_h_hasta:
        errores.append('hora_hasta inválida; use HH:MM.')
    if errores:
        return None, None, errores
    desde = timezone.make_aware(datetime.combine(d_desde, parsed_h_desde)) if d_desde else None
    hasta = timezone.make_aware(datetime.combine(d_hasta, parsed_h_hasta)) if d_hasta else None
    if desde and hasta and desde > hasta:
        errores.append('El inicio del período no puede ser posterior al final.')
    return desde, hasta, errores



def _ip_cliente(request):
    """Obtiene la IP del cliente sin confiar en cabeceras no verificadas."""
    return request.META.get('REMOTE_ADDR')


def _registrar_reporte(request, *, tipo, contenido, desde=None, hasta=None,
                       resultado, archivo='', detalle='', modo='actual', fecha_referencia=None):
    """Registra en la bitácora la ejecución de un reporte."""
    try:
        RegistroReporte.objects.create(
            usuario=request.user if request.user.is_authenticated else None,
            tipo=tipo,
            contenido=contenido,
            fecha_desde=desde,
            fecha_hasta=hasta,
            modo=modo,
            fecha_referencia=fecha_referencia,
            archivo=archivo,
            resultado=resultado,
            detalle=detalle[:500],
            ip=_ip_cliente(request),
            user_agent=request.META.get('HTTP_USER_AGENT', '')[:500],
        )
        registrar_auditoria(
            request,
            accion=f'reporte:{tipo}:{contenido}',
            resultado='error' if resultado == 'error' else ('rechazado' if resultado == 'rechazado' else 'exitoso'),
            detalle=detalle[:1000],
            modelo='RegistroReporte',
            objeto_id=archivo,
            datos_nuevos={
                'tipo': tipo,
                'contenido': contenido,
                'resultado': resultado,
                'fecha_desde': desde.isoformat() if desde else None,
                'fecha_hasta': hasta.isoformat() if hasta else None,
                'archivo': archivo,
                'modo': modo,
                'fecha_referencia': fecha_referencia.isoformat() if fecha_referencia else None,
            },
        )
    except Exception:
        logger.exception('No se pudo registrar la generación del reporte en la bitácora.')

# ============================================================
# VISTAS DE PLANTILLAS
# ============================================================

@gestor_requerido
def pagina_reportes(request):
    """Página principal de reportes."""
    return render(request, 'admin/reportes.html')


# ============================================================
# APIs
# ============================================================

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def api_generar_reporte(request):
    """
    Genera un reporte.

    Query params:
        tipo: 'excel' | 'pdf'
        contenido: 'zonas' | 'general'
    """
    tipo = request.query_params.get('tipo', '').lower()
    contenido = request.query_params.get('contenido', '').lower()
    modo = request.query_params.get('modo', 'actual').lower()
    fecha_referencia = None
    if modo == 'historico':
        fecha_referencia, errores = _parsear_filtro_historico(request)
        desde, hasta = None, None
    else:
        desde, hasta, errores = _parsear_filtro_temporal(request)
    if errores:
        # Registrar como rechazado cuando el tipo/contenido es válido pero
        # el intervalo temporal no cumple las reglas del módulo.
        if (tipo, contenido) in TIPOS_VALIDOS:
            _registrar_reporte(
                request,
                tipo=tipo,
                contenido=contenido,
                resultado='rechazado',
                detalle='; '.join(errores),
                modo=modo,
                fecha_referencia=fecha_referencia,
            )
        return JsonResponse(
            {'error': 'Filtros temporales inválidos', 'detalle': errores},
            status=status.HTTP_400_BAD_REQUEST,
        )

    generador = TIPOS_VALIDOS.get((tipo, contenido))
    if not generador:
        return JsonResponse(
            {
                'error': 'Parámetros inválidos',
                'detalle': (
                    f"Combinación no soportada: tipo='{tipo}', "
                    f"contenido='{contenido}'. "
                    f"Use tipo=excel|pdf y contenido=zonas|general."
                ),
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    inicio = time_module.monotonic()
    try:
        # Limpiar reportes antiguos antes de generar uno nuevo
        limpiar_reportes_antiguos()

        ruta = generador(desde=desde, hasta=hasta, as_of=fecha_referencia)
        if not ruta:
            _registrar_reporte(request, tipo=tipo, contenido=contenido, desde=desde, hasta=hasta,
                               resultado='sin_datos', detalle='No hubo datos para la referencia solicitada.', modo=modo, fecha_referencia=fecha_referencia)
            return JsonResponse(
                {'error': 'No hay datos para generar el reporte'},
                status=status.HTTP_404_NOT_FOUND,
            )

        _registrar_reporte(request, tipo=tipo, contenido=contenido, desde=desde, hasta=hasta,
                           archivo=os.path.basename(ruta), resultado='exitoso', modo=modo, fecha_referencia=fecha_referencia,
                           detalle=f'Duración: {time_module.monotonic() - inicio:.2f}s')
        return JsonResponse({
            'success': True,
            'mensaje': 'Reporte generado correctamente',
            'archivo': os.path.basename(ruta),
        })
    except Exception as e:
        _registrar_reporte(request, tipo=tipo, contenido=contenido, desde=desde, hasta=hasta,
                           resultado='error', detalle=str(e), modo=modo, fecha_referencia=fecha_referencia)
        logger.error(f"Error generando reporte {tipo}/{contenido}: {e}", exc_info=True)
        return JsonResponse(
            {'error': 'Error al generar el reporte'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def api_descargar_reporte(request, nombre_archivo):
    """
    Sirve un reporte generado.

    ⚠️ Seguridad: solo permite descargar archivos dentro de
    MEDIA_ROOT/reportes y con extensión .xlsx o .pdf.
    """
    try:
        # 1) Sanitizar: solo el basename
        nombre_seguro = os.path.basename(nombre_archivo)
        if nombre_seguro != nombre_archivo:
            logger.warning(f"Intento de path traversal: {nombre_archivo}")
            return JsonResponse(
                {'error': 'Nombre de archivo inválido'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # 2) Validar extensión
        _, ext = os.path.splitext(nombre_seguro)
        if ext.lower() not in EXTENSIONES_PERMITIDAS:
            return JsonResponse(
                {'error': 'Tipo de archivo no permitido'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # 3) Resolver ruta real y verificar que está dentro del directorio
        directorio = os.path.realpath(os.path.join(settings.MEDIA_ROOT, 'reportes'))
        ruta = os.path.realpath(os.path.join(directorio, nombre_seguro))

        if not ruta.startswith(directorio + os.sep) and ruta != directorio:
            logger.warning(f"Path fuera de directorio: {ruta}")
            return JsonResponse(
                {'error': 'Ruta no permitida'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not os.path.isfile(ruta):
            return JsonResponse(
                {'error': 'Archivo no encontrado'},
                status=status.HTTP_404_NOT_FOUND,
            )

        return FileResponse(
            open(ruta, 'rb'),
            as_attachment=True,
            filename=nombre_seguro,
        )
    except Exception as e:
        logger.error(f"Error sirviendo reporte: {e}", exc_info=True)
        return JsonResponse(
            {'error': 'Error al descargar el reporte'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )