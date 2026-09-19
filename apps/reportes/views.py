"""
Vistas del módulo de reportes.

Genera y sirve archivos Excel/PDF. La lógica de generación vive en
`generador_reportes.py`; aquí solo se orquesta y se asegura la
descarga segura.
"""
import logging
import os

from django.conf import settings
from django.http import FileResponse, JsonResponse
from django.shortcuts import render
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework import status

from apps.mapa.decorators import gestor_requerido

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

    try:
        # Limpiar reportes antiguos antes de generar uno nuevo
        limpiar_reportes_antiguos()

        ruta = generador()
        if not ruta:
            return JsonResponse(
                {'error': 'No hay datos para generar el reporte'},
                status=status.HTTP_404_NOT_FOUND,
            )

        return JsonResponse({
            'success': True,
            'mensaje': 'Reporte generado correctamente',
            'archivo': os.path.basename(ruta),
        })
    except Exception as e:
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