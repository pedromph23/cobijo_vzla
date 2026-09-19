"""
Vistas para la aplicación de mapa administrativo.

Los controladores son delgados: delegan la lógica de negocio a
`services.py` y la autorización a `decorators.py`.
"""
import csv
import json
import logging
import sys
from io import StringIO

from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse, HttpResponse
from django.core.management import call_command
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated

from apps.core.models import ParametrosModelo, ResultadoOptimizacion
from apps.optimizacion.optimizer import ejecutar_optimizacion
from apps.optimizacion.heatmap import generar_mapa_calor

from . import services
from .decorators import es_gestor, gestor_requerido

from django.shortcuts import redirect
from .decorators import admin_requerido, gestor_requerido, es_administrador, es_gestor


logger = logging.getLogger(__name__)


# ============================================================
# VISTAS DE PLANTILLAS
# ============================================================

@gestor_requerido
def panel_control(request):
    """Vista principal del panel de control."""
    parametros = ParametrosModelo.objects.order_by('-fecha_creacion')
    return render(request, 'admin/panel_control.html', {
        'parametros': parametros,
        'estadisticas': services.obtener_estadisticas(),
    })


@gestor_requerido
def carga_datos(request):
    """Vista para la página de gestión de datos."""
    return render(request, 'admin/carga_datos.html', {
        'estadisticas': services.obtener_estadisticas(),
    })


@gestor_requerido
def resultados_view(request):
    """Vista para la página de resultados de optimización."""
    resultados = (
        ResultadoOptimizacion.objects
        .select_related('parametros')
        .order_by('-fecha_ejecucion')[:10]
    )
    return render(request, 'admin/resultados.html', {
        'resultados': resultados,
    })


# ============================================================
# APIs DE MAPA ADMINISTRATIVO
# ============================================================

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def api_datos_mapa(request):
    """Datos completos para el mapa administrativo."""
    try:
        return JsonResponse(services.obtener_datos_mapa(), safe=False)
    except Exception as e:
        logger.error(f"Error en api_datos_mapa: {e}", exc_info=True)
        return JsonResponse({'error': str(e)}, status=500)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def api_estadisticas(request):
    """Estadísticas generales del sistema."""
    try:
        return JsonResponse(services.obtener_estadisticas())
    except Exception as e:
        logger.error(f"Error en api_estadisticas: {e}", exc_info=True)
        return JsonResponse({'error': str(e)}, status=500)


# ============================================================
# APIs DE OPTIMIZACIÓN
# ============================================================

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def api_ejecutar_optimizacion(request):
    """Ejecuta un modelo de optimización con los parámetros dados."""
    param_id = request.data.get('parametros_id')
    if not param_id:
        return JsonResponse({'error': 'Se requiere parametros_id'}, status=400)

    try:
        parametros = get_object_or_404(ParametrosModelo, pk=param_id)
        resultado = ejecutar_optimizacion(param_id)

        if not resultado:
            return JsonResponse(
                {'error': 'La optimización no devolvió resultados'},
                status=400,
            )
        if 'error' in resultado:
            return JsonResponse({'error': resultado['error']}, status=400)

        resultado_obj = ResultadoOptimizacion.objects.create(
            parametros=parametros,
            datos_json=resultado,
        )

        return JsonResponse({
            'resultado_id': resultado_obj.id,
            'datos': resultado,
            'mensaje': 'Optimización ejecutada correctamente',
        })
    except Exception as e:
        logger.error(f"Error en api_ejecutar_optimizacion: {e}", exc_info=True)
        return JsonResponse({'error': str(e)}, status=500)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def api_listar_resultados(request):
    """Lista los últimos 20 resultados de optimización."""
    try:
        resultados = (
            ResultadoOptimizacion.objects
            .select_related('parametros')
            .order_by('-fecha_ejecucion')[:20]
        )
        data = [
            {
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
            }
            for r in resultados
        ]
        return JsonResponse(data, safe=False)
    except Exception as e:
        logger.error(f"Error en api_listar_resultados: {e}", exc_info=True)
        return JsonResponse({'error': str(e)}, status=500)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def api_detalle_resultado(request, resultado_id):
    """Devuelve el detalle de un resultado específico."""
    try:
        resultado = get_object_or_404(
            ResultadoOptimizacion.objects.select_related('parametros'),
            pk=resultado_id,
        )
        data = {
            'id': resultado.id,
            'fecha': resultado.fecha_ejecucion.strftime('%Y-%m-%d %H:%M'),
            'escenario': (
                resultado.parametros.nombre_escenario
                if resultado.parametros else 'Sin escenario'
            ),
        }
        data.update(resultado.datos_json)
        return JsonResponse(data)
    except Exception as e:
        logger.error(f"Error en api_detalle_resultado: {e}", exc_info=True)
        return JsonResponse({'error': str(e)}, status=500)


# ============================================================
# APIs DE MAPA DE CALOR
# ============================================================

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def api_mapa_calor(request):
    """Genera el mapa de calor con pesos personalizables."""
    try:
        pesos = {
            clave: float(request.query_params.get(clave, 1.0))
            for clave in (
                'densidad', 'vulnerabilidad', 'distancia',
                'heridos', 'fallecidos', 'damnificados', 'reportes',
            )
        }
        return JsonResponse(generar_mapa_calor(pesos), safe=False)
    except Exception as e:
        logger.error(f"Error en api_mapa_calor: {e}", exc_info=True)
        return JsonResponse({'error': str(e)}, status=500)


# ============================================================
# APIs DE COMANDOS DE GESTIÓN
# ============================================================

COMANDOS_PERMITIDOS = (
    'cargar_datos_prueba',
    'cargar_datos_masivos',
    'importar_limites',
)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def api_ejecutar_comando(request):
    """
    Ejecuta comandos de gestión predefinidos.

    ⚠️ Solo permite comandos de la whitelist COMANDOS_PERMITIDOS.
    Requiere que el usuario sea gestor o superusuario.
    """
    if not es_gestor(request.user):
        return JsonResponse(
            {'error': 'Se requieren permisos de gestor'},
            status=403,
        )

    comando = request.data.get('comando')
    if not comando:
        return JsonResponse({'error': 'Se requiere un comando'}, status=400)
    if comando not in COMANDOS_PERMITIDOS:
        return JsonResponse(
            {'error': f'Comando no permitido: {comando}'},
            status=400,
        )

    salida = StringIO()
    stdout_original = sys.stdout
    try:
        sys.stdout = salida
        call_command(comando)
        return JsonResponse({
            'success': True,
            'mensaje': f'Comando {comando} ejecutado correctamente',
            'salida': salida.getvalue(),
        })
    except Exception as e:
        logger.error(f"Error ejecutando comando {comando}: {e}", exc_info=True)
        return JsonResponse({'error': str(e)}, status=500)
    finally:
        sys.stdout = stdout_original


# ============================================================
# APIs DE EXPORTACIÓN
# ============================================================

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def api_exportar_csv(request):
    """Exporta los resultados de optimización a CSV."""
    try:
        resultados = (
            ResultadoOptimizacion.objects
            .select_related('parametros')
            .order_by('-fecha_ejecucion')
        )

        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = (
            'attachment; filename="resultados_optimizacion.csv"'
        )

        writer = csv.writer(response)
        writer.writerow([
            'ID', 'Fecha', 'Escenario', 'Distancia Total (km)',
            'Población Atendida', '% Cubierto', 'Costo Total',
        ])
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
        logger.error(f"Error en api_exportar_csv: {e}", exc_info=True)
        return JsonResponse({'error': str(e)}, status=500)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def api_exportar_geojson(request):
    """Exporta los centros del último resultado a GeoJSON."""
    try:
        resultado = ResultadoOptimizacion.objects.order_by('-fecha_ejecucion').first()
        if not resultado:
            return JsonResponse(
                {'error': 'No hay resultados para exportar'},
                status=404,
            )

        geojson = services.construir_geojson_centros(resultado.datos_json)
        response = HttpResponse(
            json.dumps(geojson, indent=2, ensure_ascii=False),
            content_type='application/geo+json',
        )
        response['Content-Disposition'] = (
            'attachment; filename="centros_seleccionados.geojson"'
        )
        return response
    except Exception as e:
        logger.error(f"Error en api_exportar_geojson: {e}", exc_info=True)
        return JsonResponse({'error': str(e)}, status=500)


# ============================================================
# HEALTH CHECK
# ============================================================

def health_check(request):
    """Endpoint público para verificación de salud del servicio."""
    return JsonResponse({
        'status': 'ok',
        'service': 'cobijo-vzla',
        'timestamp': __import__('django.utils.timezone', fromlist=['now']).now().isoformat(),
    })

    # ============================================================
# PANEL DE CONTROL (SEGÚN GRUPO)
# ============================================================

@gestor_requerido
def panel_control(request):
    """
    Dispatcher: redirige al panel específico según el grupo del usuario.

    - Administradores → panel_admin
    - Gestores → panel_gestor
    """
    if es_administrador(request.user):
        return redirect('panel_admin')
    return redirect('panel_gestor')


@admin_requerido
def panel_admin(request):
    """
    Panel completo para administradores.

    Incluye: mapa, datos, optimización, reportes y herramientas de gestión.
    """
    parametros = ParametrosModelo.objects.order_by('-fecha_creacion')
    return render(request, 'admin/panel_admin.html', {
        'parametros': parametros,
        'estadisticas': services.obtener_estadisticas(),
        'es_admin': True,
        'grupos_usuario': list(request.user.groups.values_list('name', flat=True)),
    })


@gestor_requerido
def panel_gestor(request):
    """
    Panel operativo para gestores.

    Incluye: mapa, datos (lectura), reportes. Sin configuración crítica.
    """
    return render(request, 'admin/panel_gestor.html', {
        'estadisticas': services.obtener_estadisticas(),
        'es_admin': es_administrador(request.user),
        'grupos_usuario': list(request.user.groups.values_list('name', flat=True)),
    })


@admin_requerido
def carga_datos(request):
    """Vista para la página de gestión de datos (solo administradores)."""
    return render(request, 'admin/carga_datos.html', {
        'estadisticas': services.obtener_estadisticas(),
    })