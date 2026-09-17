"""
Vistas para la aplicación de mapa administrativo.
"""

from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse, HttpResponse
from django.db.models import Count, Sum, Avg
from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework import status

import csv
import json

from apps.core.models import (
    PuntoDemanda,
    SitioCandidato,
    RefugioExistente,
    ZonaAfectada,
    ParametrosModelo,
    ResultadoOptimizacion,
    Estado,
    Parroquia
)
from apps.emergencias.models import Evento, Reporte
from apps.optimizacion.optimizer import ejecutar_optimizacion
from apps.optimizacion.heatmap import generar_mapa_calor


# ============================================================
# FUNCIONES AUXILIARES
# ============================================================

def es_gestor(user):
    """Verifica si el usuario pertenece al grupo 'Gestores'."""
    if not user or not user.is_authenticated:
        return False
    return user.groups.filter(name='Gestores').exists() or user.is_superuser


def get_datos_estadisticos():
    """Obtiene estadísticas generales del sistema."""
    try:
        return {
            'estados': Estado.objects.count(),
            'parroquias': Parroquia.objects.count(),
            'puntos_demanda': PuntoDemanda.objects.count(),
            'sitios_candidatos': SitioCandidato.objects.count(),
            'refugios': RefugioExistente.objects.count(),
            'zonas_afectadas': ZonaAfectada.objects.filter(fecha_fin__isnull=True).count(),
            'eventos_activos': Evento.objects.filter(activo=True).count(),
            'reportes_recientes': Reporte.objects.filter(fecha__date=timezone.now().date()).count(),
        }
    except Exception as e:
        print(f"Error en get_datos_estadisticos: {e}")
        return {
            'estados': 0, 'parroquias': 0, 'puntos_demanda': 0,
            'sitios_candidatos': 0, 'refugios': 0, 'zonas_afectadas': 0,
            'eventos_activos': 0, 'reportes_recientes': 0,
        }


def get_datos_mapa_context():
    """Obtiene el contexto completo para el mapa administrativo."""
    try:
        puntos_demanda = []
        for p in PuntoDemanda.objects.select_related('parroquia__estado').all()[:500]:
            puntos_demanda.append({
                'id': p.id,
                'nombre': p.nombre,
                'lat': p.ubicacion.y if p.ubicacion else None,
                'lng': p.ubicacion.x if p.ubicacion else None,
                'poblacion': p.poblacion,
                'vulnerabilidad': p.vulnerabilidad,
            })

        sitios_candidatos = []
        for s in SitioCandidato.objects.filter(disponible=True)[:200]:
            sitios_candidatos.append({
                'id': s.id,
                'nombre': s.nombre,
                'lat': s.ubicacion.y if s.ubicacion else None,
                'lng': s.ubicacion.x if s.ubicacion else None,
                'capacidad_maxima': s.capacidad_maxima,
            })

        refugios = []
        for r in RefugioExistente.objects.all()[:200]:
            refugios.append({
                'id': r.id,
                'nombre': r.nombre,
                'lat': r.ubicacion.y if r.ubicacion else None,
                'lng': r.ubicacion.x if r.ubicacion else None,
                'capacidad_disponible': r.capacidad_disponible,
                'operativo': r.operativo,
            })

        zonas_afectadas = []
        for z in ZonaAfectada.objects.filter(fecha_fin__isnull=True).select_related('evento')[:100]:
            zonas_afectadas.append({
                'id': z.id,
                'nombre': z.nombre,
                'descripcion': z.descripcion,
                'nivel_alerta': z.nivel_alerta,
                'heridos': z.heridos,
                'fallecidos': z.fallecidos,
                'damnificados': z.damnificados,
                'geojson': z.geom.geojson if z.geom else None,
            })

        return {
            'puntos_demanda': puntos_demanda,
            'sitios_candidatos': sitios_candidatos,
            'refugios': refugios,
            'zonas_afectadas': zonas_afectadas,
        }
    except Exception as e:
        print(f"Error en get_datos_mapa_context: {e}")
        return {
            'puntos_demanda': [], 'sitios_candidatos': [],
            'refugios': [], 'zonas_afectadas': [],
        }


# ============================================================
# VISTAS DE PLANTILLAS
# ============================================================

@login_required
@user_passes_test(es_gestor)
def panel_control(request):
    """Vista principal del panel de control."""
    parametros = ParametrosModelo.objects.all().order_by('-fecha_creacion')
    context = {
        'parametros': parametros,
        'estadisticas': get_datos_estadisticos(),
    }
    return render(request, 'admin/panel_control.html', context)


@login_required
@user_passes_test(es_gestor)
def carga_datos(request):
    """Vista para la página de carga de datos."""
    context = {'estadisticas': get_datos_estadisticos()}
    return render(request, 'admin/carga_datos.html', context)


@login_required
@user_passes_test(es_gestor)
def resultados_view(request):
    """Vista para la página de resultados."""
    resultados = ResultadoOptimizacion.objects.select_related('parametros').order_by('-fecha_ejecucion')[:10]
    context = {'resultados': resultados}
    return render(request, 'admin/resultados.html', context)


# ============================================================
# APIs DE MAPA ADMINISTRATIVO
# ============================================================

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def api_datos_mapa(request):
    """API que devuelve todos los datos para el mapa administrativo."""
    try:
        datos = get_datos_mapa_context()
        return JsonResponse(datos, safe=False)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def api_estadisticas(request):
    """API que devuelve estadísticas generales."""
    try:
        return JsonResponse(get_datos_estadisticos())
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


# ============================================================
# APIs DE OPTIMIZACIÓN
# ============================================================

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def api_ejecutar_optimizacion(request):
    """API para ejecutar un modelo de optimización."""
    try:
        param_id = request.data.get('parametros_id')
        if not param_id:
            return JsonResponse({'error': 'Se requiere parametros_id'}, status=400)
        
        parametros = get_object_or_404(ParametrosModelo, pk=param_id)
        resultado = ejecutar_optimizacion(param_id)
        
        if resultado is None:
            return JsonResponse({'error': 'La optimización no devolvió resultados'}, status=400)
        
        if 'error' in resultado:
            return JsonResponse({'error': resultado['error']}, status=400)
        
        resultado_obj = ResultadoOptimizacion.objects.create(
            parametros=parametros,
            datos_json=resultado
        )
        
        return JsonResponse({
            'resultado_id': resultado_obj.id,
            'datos': resultado,
            'mensaje': 'Optimización ejecutada correctamente'
        })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def api_listar_resultados(request):
    """API para listar resultados de optimización."""
    try:
        resultados = ResultadoOptimizacion.objects.select_related('parametros').order_by('-fecha_ejecucion')[:20]
        
        data = []
        for r in resultados:
            data.append({
                'id': r.id,
                'fecha': r.fecha_ejecucion.strftime('%Y-%m-%d %H:%M'),
                'escenario': r.parametros.nombre_escenario if r.parametros else 'Sin escenario',
                'tipo_modelo': r.parametros.tipo_modelo if r.parametros else '',
                'resumen': {
                    'distancia_total': r.datos_json.get('distancia_total_km'),
                    'poblacion_atendida': r.datos_json.get('poblacion_atendida'),
                    'porcentaje_cubierto': r.datos_json.get('porcentaje_cubierto'),
                    'costo_total': r.datos_json.get('costo_total'),
                },
                'centros': r.datos_json.get('centros', [])[:5],
            })
        
        return JsonResponse(data, safe=False)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def api_detalle_resultado(request, resultado_id):
    """API para obtener detalle de un resultado específico."""
    try:
        resultado = get_object_or_404(
            ResultadoOptimizacion.objects.select_related('parametros'),
            pk=resultado_id
        )
        
        data = {
            'id': resultado.id,
            'fecha': resultado.fecha_ejecucion.strftime('%Y-%m-%d %H:%M'),
            'escenario': resultado.parametros.nombre_escenario if resultado.parametros else 'Sin escenario',
        }
        data.update(resultado.datos_json)
        
        return JsonResponse(data)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


# ============================================================
# APIs DE MAPA DE CALOR
# ============================================================

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def api_mapa_calor(request):
    """API para generar mapa de calor."""
    try:
        pesos = {
            'densidad': float(request.query_params.get('densidad', 1.0)),
            'vulnerabilidad': float(request.query_params.get('vulnerabilidad', 1.0)),
            'distancia': float(request.query_params.get('distancia', 1.0)),
            'heridos': float(request.query_params.get('heridos', 1.0)),
            'fallecidos': float(request.query_params.get('fallecidos', 1.0)),
            'damnificados': float(request.query_params.get('damnificados', 1.0)),
            'reportes': float(request.query_params.get('reportes', 1.0)),
        }
        
        puntos = generar_mapa_calor(pesos)
        return JsonResponse(puntos, safe=False)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


# ============================================================
# APIs DE EJECUCIÓN DE COMANDOS
# ============================================================

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def api_ejecutar_comando(request):
    """API para ejecutar comandos de gestión."""
    try:
        from django.core.management import call_command
        from io import StringIO
        import sys
        
        comando = request.data.get('comando')
        comandos_permitidos = ['cargar_datos_prueba', 'cargar_datos_masivos', 'importar_limites']
        
        if not comando:
            return JsonResponse({'error': 'Se requiere un comando'}, status=400)
        
        if comando not in comandos_permitidos:
            return JsonResponse({'error': f'Comando no permitido: {comando}'}, status=400)
        
        salida = StringIO()
        sys.stdout = salida
        call_command(comando)
        sys.stdout = sys.__stdout__
        
        return JsonResponse({
            'success': True,
            'mensaje': f'Comando {comando} ejecutado correctamente',
            'salida': salida.getvalue()
        })
    except Exception as e:
        sys.stdout = sys.__stdout__
        return JsonResponse({'error': str(e)}, status=500)


# ============================================================
# APIs DE EXPORTACIÓN
# ============================================================

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def api_exportar_csv(request):
    """API para exportar resultados a CSV."""
    try:
        resultados = ResultadoOptimizacion.objects.select_related('parametros').order_by('-fecha_ejecucion')
        
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="resultados_optimizacion.csv"'
        
        writer = csv.writer(response)
        writer.writerow(['ID', 'Fecha', 'Escenario', 'Distancia Total (km)', 'Población Atendida', '% Cubierto', 'Costo Total'])
        
        for r in resultados:
            writer.writerow([
                r.id,
                r.fecha_ejecucion.strftime('%Y-%m-%d %H:%M'),
                r.parametros.nombre_escenario if r.parametros else 'Sin escenario',
                r.datos_json.get('distancia_total_km', 0),
                r.datos_json.get('poblacion_atendida', 0),
                r.datos_json.get('porcentaje_cubierto', 0),
                r.datos_json.get('costo_total', 0),
            ])
        
        return response
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def api_exportar_geojson(request):
    """API para exportar centros seleccionados a GeoJSON."""
    try:
        resultado = ResultadoOptimizacion.objects.order_by('-fecha_ejecucion').first()
        
        if not resultado:
            return JsonResponse({'error': 'No hay resultados para exportar'}, status=404)
        
        features = []
        for centro in resultado.datos_json.get('centros', []):
            features.append({
                'type': 'Feature',
                'geometry': {
                    'type': 'Point',
                    'coordinates': [centro.get('lng', 0), centro.get('lat', 0)]
                },
                'properties': {
                    'nombre': centro.get('nombre', ''),
                    'id': centro.get('id', None),
                }
            })
        
        geojson = {
            'type': 'FeatureCollection',
            'features': features
        }
        
        response = HttpResponse(
            json.dumps(geojson, indent=2, ensure_ascii=False),
            content_type='application/json'
        )
        response['Content-Disposition'] = 'attachment; filename="centros_seleccionados.geojson"'
        
        return response
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)