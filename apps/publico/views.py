"""
Vistas del portal público de CobijoVzla.

Controladores delgados: la lógica de negocio vive en `services.py`
y el cálculo del heatmap en `apps.optimizacion.heatmap`.
"""
import logging

from django.shortcuts import render
from django.http import JsonResponse
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework import status

from apps.optimizacion.heatmap import generar_mapa_calor, Pesos
from . import services
from .forms import ReporteCiudadanoForm


logger = logging.getLogger(__name__)


# ============================================================
# VISTAS DE PLANTILLAS
# ============================================================

def mapa_publico(request):
    """Vista principal del mapa público."""
    return render(request, 'publico/mapa_publico.html', {
        'estadisticas': services.obtener_estadisticas_home(),
    })


def reporte_ciudadano_view(request):
    """Vista para el formulario de reporte ciudadano."""
    return render(request, 'publico/reporte_ciudadano.html', {
        'form': ReporteCiudadanoForm(),
    })


# ============================================================
# APIs PÚBLICAS
# ============================================================

@api_view(['GET'])
@permission_classes([AllowAny])
def api_refugios_publicos(request):
    """Lista de refugios operativos (cacheado 5 min)."""
    try:
        return JsonResponse(services.obtener_refugios_publicos(), safe=False)
    except Exception as e:
        logger.error(f"Error en api_refugios_publicos: {e}", exc_info=True)
        return JsonResponse(
            {'error': 'Error al obtener refugios'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@api_view(['GET'])
@permission_classes([AllowAny])
def api_zonas_afectadas(request):
    """Zonas afectadas activas (cacheado 3 min)."""
    try:
        return JsonResponse(services.obtener_zonas_activas(), safe=False)
    except Exception as e:
        logger.error(f"Error en api_zonas_afectadas: {e}", exc_info=True)
        return JsonResponse(
            {'error': 'Error al obtener zonas afectadas'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@api_view(['GET'])
@permission_classes([AllowAny])
def api_mapa_calor_publico(request):
    """Mapa de calor con pesos personalizables (query params)."""
    try:
        pesos = Pesos.from_request(request.query_params)
        puntos = generar_mapa_calor(pesos=pesos)
        return JsonResponse(puntos, safe=False)
    except Exception as e:
        logger.error(f"Error en api_mapa_calor_publico: {e}", exc_info=True)
        return JsonResponse(
            {'error': 'Error al generar mapa de calor'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@api_view(['GET'])
@permission_classes([AllowAny])
def api_buscar_lugar(request):
    """Búsqueda de estados, parroquias y refugios por nombre."""
    try:
        query = request.GET.get('q', '')
        return JsonResponse(services.buscar_lugares(query), safe=False)
    except Exception as e:
        logger.error(f"Error en api_buscar_lugar: {e}", exc_info=True)
        return JsonResponse(
            {'error': 'Error en búsqueda'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@api_view(['POST'])
@permission_classes([AllowAny])
def api_reporte_ciudadano(request):
    """Recibe y valida reportes ciudadanos."""
    try:
        form = ReporteCiudadanoForm(request.data, request.FILES)
        if form.is_valid():
            reporte = form.save()
            return JsonResponse({
                'id': reporte.id,
                'mensaje': 'Reporte enviado correctamente. ¡Gracias por ayudar!',
            }, status=status.HTTP_201_CREATED)

        return JsonResponse({
            'error': 'Datos inválidos',
            'detalles': form.errors,
        }, status=status.HTTP_400_BAD_REQUEST)

    except Exception as e:
        logger.error(f"Error en api_reporte_ciudadano: {e}", exc_info=True)
        return JsonResponse(
            {'error': 'Error al procesar el reporte'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@api_view(['GET'])
@permission_classes([AllowAny])
def api_info_emergencia(request):
    """Información de contacto de emergencia (estática)."""
    return JsonResponse({
        'telefono_emergencia': '171',
        'bomberos': '911',
        'proteccion_civil': '0800-123-456',
        'horario_atencion': '24 horas',
    })