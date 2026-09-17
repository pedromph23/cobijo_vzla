"""
Vistas para la aplicación pública de CobijoVzla.
Este módulo contiene las vistas y APIs necesarias para:
- Mapa público interactivo
- Búsqueda de refugios y lugares
- Reportes ciudadanos
- Mapa de calor público
- Zonas afectadas
"""
from django.shortcuts import render
from django.http import JsonResponse
from django.db.models import Q
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework import status

from apps.core.models import (
    RefugioExistente,
    ZonaAfectada,
    Estado,
    Parroquia
)
from apps.emergencias.models import Reporte, Evento
from apps.optimizacion.heatmap import generar_mapa_calor
from .forms import ReporteCiudadanoForm

# ============================================================
# VISTAS DE PLANTILLAS
# ============================================================

def mapa_publico(request):
    """Vista principal del mapa público."""
    context = {
        'eventos_activos': Evento.objects.filter(activo=True).count(),
        'total_refugios': RefugioExistente.objects.filter(operativo=True).count(),
    }
    return render(request, 'publico/mapa_publico.html', context)

def reporte_ciudadano_view(request):
    """Vista para el formulario de reporte ciudadano."""
    form = ReporteCiudadanoForm()
    context = {
        'form': form,
    }
    return render(request, 'publico/reporte_ciudadano.html', context)

# ============================================================
# APIs PÚBLICAS
# ============================================================

@api_view(['GET'])
@permission_classes([AllowAny])
def api_refugios_publicos(request):
    """API que devuelve la lista de refugios operativos."""
    try:
        refugios = RefugioExistente.objects.filter(operativo=True)
        data = []
        for r in refugios:
            data.append({
                'id': r.id,
                'nombre': r.nombre,
                'direccion': r.direccion,
                'lat': r.ubicacion.y if r.ubicacion else None,
                'lng': r.ubicacion.x if r.ubicacion else None,
                'capacidad_total': r.capacidad_total,
                'capacidad_disponible': r.capacidad_disponible,
                'servicios': r.servicios if isinstance(r.servicios, list) else [],
                'operativo': r.operativo,
                'telefono': r.telefono,
                'horario': r.horario,
            })
        return JsonResponse(data, safe=False)
    except Exception as e:
        return JsonResponse(
            {'error': f'Error al obtener refugios: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(['GET'])
@permission_classes([AllowAny])
def api_zonas_afectadas(request):
    """API que devuelve las zonas afectadas activas."""
    try:
        zonas = ZonaAfectada.objects.filter(
            fecha_fin__isnull=True
        ).select_related('evento')
        
        data = []
        for z in zonas:
            centroide = z.geom.centroid if z.geom else None
            data.append({
                'id': z.id,
                'nombre': z.nombre,
                'descripcion': z.descripcion,
                'nivel_alerta': z.nivel_alerta,
                'heridos': z.heridos,
                'fallecidos': z.fallecidos,
                'damnificados': z.damnificados,
                'lat': centroide.y if centroide else None,
                'lng': centroide.x if centroide else None,
                'evento': z.evento.nombre if z.evento else None,
                'tipo_evento': z.evento.tipo if z.evento else None,
            })
        return JsonResponse(data, safe=False)
    except Exception as e:
        return JsonResponse(
            {'error': f'Error al obtener zonas afectadas: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(['GET'])
@permission_classes([AllowAny])
def api_mapa_calor_publico(request):
    """API que genera el mapa de calor público."""
    try:
        puntos = generar_mapa_calor()
        return JsonResponse(puntos, safe=False)
    except Exception as e:
        return JsonResponse(
            {'error': f'Error al generar mapa de calor: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(['GET'])
@permission_classes([AllowAny])
def api_buscar_lugar(request):
    """API para buscar estados, parroquias y refugios (Calcula Centroides)."""
    try:
        query = request.GET.get('q', '').strip()
        
        if not query or len(query) < 2:
            return JsonResponse([], safe=False)
            
        resultados = []
        
        # 1. Buscar en Parroquias
        parroquias = Parroquia.objects.filter(
            nombre__icontains=query
        ).select_related('estado')[:5]
        
        for p in parroquias:
            if p.geom:
                centroide = p.geom.centroid
                resultados.append({
                    'tipo': 'parroquia',
                    'nombre': p.nombre,
                    'estado': f"Parroquia del Estado {p.estado.nombre}" if p.estado else 'Parroquia',
                    'lat': centroide.y,
                    'lng': centroide.x,
                })
                
        # 2. Buscar en Estados
        estados = Estado.objects.filter(nombre__icontains=query)[:3]
        for e in estados:
            if e.geom:
                centroide = e.geom.centroid
                resultados.append({
                    'tipo': 'estado',
                    'nombre': e.nombre,
                    'estado': 'Estado',
                    'lat': centroide.y,
                    'lng': centroide.x,
                })
                
        # 3. Buscar en Refugios
        refugios = RefugioExistente.objects.filter(
            Q(nombre__icontains=query) | Q(direccion__icontains=query),
            operativo=True
        )[:5]
        
        for r in refugios:
            if r.ubicacion:
                resultados.append({
                    'tipo': 'refugio',
                    'nombre': r.nombre,
                    'estado': r.direccion or 'Refugio',
                    'lat': r.ubicacion.y,
                    'lng': r.ubicacion.x,
                })
                
        return JsonResponse(resultados, safe=False)
    except Exception as e:
        return JsonResponse(
            {'error': f'Error en búsqueda: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(['POST'])
@permission_classes([AllowAny])
def api_reporte_ciudadano(request):
    """API para recibir reportes ciudadanos."""
    try:
        form = ReporteCiudadanoForm(request.data, request.FILES)
        if form.is_valid():
            reporte = form.save()
            return JsonResponse({
                'id': reporte.id,
                'mensaje': 'Reporte enviado correctamente. ¡Gracias por ayudar!',
            }, status=status.HTTP_201_CREATED)
        else:
            return JsonResponse({
                'error': 'Datos inválidos',
                'detalles': form.errors,
            }, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        return JsonResponse(
            {'error': f'Error al enviar reporte: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(['GET'])
@permission_classes([AllowAny])
def api_info_emergencia(request):
    """API que devuelve información de contacto de emergencia."""
    data = {
        'telefono_emergencia': '171',
        'bomberos': '911',
        'proteccion_civil': '0800-123-456',
        'horario_atencion': '24 horas',
    }
    return JsonResponse(data)