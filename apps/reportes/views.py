"""
Vistas para la generación de reportes.
"""

from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import JsonResponse, FileResponse, HttpResponse
from django.shortcuts import render
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework import status

import csv
import json
import os

from apps.core.models import ResultadoOptimizacion


def es_gestor(user):
    return user.groups.filter(name='Gestores').exists() or user.is_superuser


# ============================================================
# VISTAS DE PLANTILLAS
# ============================================================

@login_required
@user_passes_test(es_gestor)
def pagina_reportes(request):
    """Página principal de reportes."""
    return render(request, 'admin/reportes.html')


# ============================================================
# APIs DE REPORTES
# ============================================================

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def api_generar_reporte(request):
    """
    API para generar reportes.
    
    Query params:
        tipo: 'excel' o 'pdf'
        contenido: 'zonas' o 'general'
    """
    try:
        tipo = request.query_params.get('tipo', 'excel')
        contenido = request.query_params.get('contenido', 'general')
        
        # Importar generador aquí para evitar errores si pandas no está instalado
        try:
            from .generador_reportes import (
                generar_excel_zonas_afectadas,
                generar_excel_estadisticas_generales,
                generar_pdf_zonas_afectadas,
                generar_pdf_estadisticas_generales,
            )
        except ImportError as e:
            return JsonResponse(
                {'error': f'Faltan dependencias: {str(e)}. Instale pandas, openpyxl y reportlab.'},
                status=500
            )
        
        if tipo == 'excel':
            if contenido == 'zonas':
                ruta = generar_excel_zonas_afectadas()
            else:
                ruta = generar_excel_estadisticas_generales()
        elif tipo == 'pdf':
            if contenido == 'zonas':
                ruta = generar_pdf_zonas_afectadas()
            else:
                ruta = generar_pdf_estadisticas_generales()
        else:
            return JsonResponse({'error': 'Tipo no válido. Use "excel" o "pdf"'}, status=400)
        
        if not ruta:
            return JsonResponse({'error': 'No hay datos para generar el reporte'}, status=404)
        
        return JsonResponse({
            'success': True,
            'mensaje': 'Reporte generado correctamente',
            'archivo': os.path.basename(ruta),
            'ruta': ruta,
        })
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def api_descargar_reporte(request, nombre_archivo):
    """API para descargar un reporte generado."""
    try:
        from django.conf import settings
        
        ruta = os.path.join(settings.MEDIA_ROOT, 'reportes', nombre_archivo)
        
        if not os.path.exists(ruta):
            return JsonResponse({'error': 'Archivo no encontrado'}, status=404)
        
        return FileResponse(open(ruta, 'rb'), as_attachment=True, filename=nombre_archivo)
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


# ============================================================
# APIs DE EXPORTACIÓN (CSV y GeoJSON)
# ============================================================

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def api_exportar_csv(request):
    """Exporta resultados de optimización a CSV."""
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
    """Exporta centros seleccionados a GeoJSON."""
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