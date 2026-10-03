"""
Vistas del módulo `mapa` (panel administrativo).

Los controladores son delgados: delegan la lógica de negocio a
`services.py` y la autorización a `decorators.py`.

Estructura:
- Vistas de plantilla: panel_control, panel_admin, panel_gestor,
  carga_datos, resultados_view
- APIs de mapa: datos_mapa, estadisticas
- APIs de optimización: ejecutar, listar, detalle
- APIs de mapa de calor
- APIs de comandos de gestión
- APIs de exportación (CSV, GeoJSON)
- Health check

La auditoría registra las operaciones administrativas relevantes:
- Optimización
- Comandos de gestión
- Exportaciones
"""

import csv
import json
import logging
import sys
from io import StringIO

from django.core.management import call_command
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated

from apps.core.audit import (
    ACCION_COMMAND,
    ACCION_EXPORT,
    ACCION_OPTIMIZATION,
    registrar_auditoria,
)
from apps.core.models import ParametrosModelo, ResultadoOptimizacion
from apps.optimizacion.heatmap import generar_mapa_calor
from apps.optimizacion.optimizer import ejecutar_optimizacion

from . import services
from .decorators import (
    EsAdministrador,
    admin_requerido,
    es_administrador,
    es_gestor,
    gestor_requerido,
)


logger = logging.getLogger(__name__)


# ============================================================
# VISTAS DE PLANTILLAS
# ============================================================

@gestor_requerido
def panel_control(request):
    """
    Dispatcher: redirige al panel específico según el grupo del usuario.

    - Administradores (super/staff/grupo Administradores) → panel_admin
    - Gestores → panel_gestor
    """
    if es_administrador(request.user):
        return redirect('panel_admin')

    return redirect('panel_gestor')


@admin_requerido
def panel_admin(request):
    """
    Panel completo para administradores.

    Incluye: mapa, datos (CRUD), optimización, reportes.
    """
    from .permissions import modelos_disponibles

    parametros = ParametrosModelo.objects.order_by('-fecha_creacion')

    return render(
        request,
        'admin/panel_admin.html',
        {
            'parametros': parametros,
            'estadisticas': services.obtener_estadisticas(),
            'menu_modelos': modelos_disponibles(request.user),
            'es_admin': True,
        },
    )


@gestor_requerido
def panel_gestor(request):
    """
    Panel operativo para gestores.

    Incluye: mapa, datos (CRUD limitado), reportes.
    SIN pestaña de optimización.
    """
    from .permissions import modelos_disponibles

    return render(
        request,
        'admin/panel_gestor.html',
        {
            'estadisticas': services.obtener_estadisticas(),
            'menu_modelos': modelos_disponibles(request.user),
            'es_admin': es_administrador(request.user),
        },
    )


@admin_requerido
def carga_datos(request):
    """Vista para la página de gestión de datos (solo administradores)."""
    return render(
        request,
        'admin/carga_datos.html',
        {
            'estadisticas': services.obtener_estadisticas(),
        },
    )


@gestor_requerido
def resultados_view(request):
    """Vista para la página de resultados de optimización."""
    resultados = (
        ResultadoOptimizacion.objects
        .select_related('parametros')
        .order_by('-fecha_ejecucion')[:10]
    )

    return render(
        request,
        'admin/resultados.html',
        {
            'resultados': resultados,
        },
    )


# ============================================================
# APIs DE MAPA ADMINISTRATIVO
# ============================================================

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def api_datos_mapa(request):
    """Datos completos para el mapa administrativo."""
    try:
        return JsonResponse(
            services.obtener_datos_mapa(),
            safe=False,
        )
    except Exception as e:
        logger.error(
            f"Error en api_datos_mapa: {e}",
            exc_info=True,
        )

        return JsonResponse(
            {'error': 'Error al obtener datos del mapa'},
            status=500,
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def api_estadisticas(request):
    """Estadísticas generales del sistema."""
    try:
        return JsonResponse(
            services.obtener_estadisticas()
        )
    except Exception as e:
        logger.error(
            f"Error en api_estadisticas: {e}",
            exc_info=True,
        )

        return JsonResponse(
            {'error': 'Error al obtener estadísticas'},
            status=500,
        )


# ============================================================
# APIs DE OPTIMIZACIÓN
# ============================================================

@api_view(['POST'])
@permission_classes([IsAuthenticated, EsAdministrador])
def api_ejecutar_optimizacion(request):
    """
    Ejecuta un modelo de optimización con los parámetros dados.

    Solo administradores.

    La operación queda registrada en la bitácora tanto si:
    - termina correctamente;
    - es rechazada por una validación;
    - ocurre un error interno.
    """
    param_id = request.data.get('parametros_id')

    if not param_id:
        registrar_auditoria(
            request=request,
            accion=ACCION_OPTIMIZATION,
            modelo='core.ParametrosModelo',
            descripcion='Intento de optimización sin parametros_id.',
            resultado='fallido',
        )

        return JsonResponse(
            {'error': 'Se requiere parametros_id'},
            status=400,
        )

    try:
        parametros = get_object_or_404(
            ParametrosModelo,
            pk=param_id,
        )

        resultado = ejecutar_optimizacion(param_id)

        # ----------------------------------------------------
        # Error controlado devuelto por el optimizador
        # ----------------------------------------------------
        if not resultado:
            registrar_auditoria(
                request=request,
                accion=ACCION_OPTIMIZATION,
                objeto=parametros,
                descripcion=(
                    f"Optimización sin resultado para el escenario "
                    f"«{parametros.nombre_escenario}»."
                ),
                datos_nuevos={
                    'escenario': parametros.nombre_escenario,
                    'tipo_modelo': parametros.tipo_modelo,
                    'parametros_id': parametros.id,
                },
                resultado='fallido',
            )

            return JsonResponse(
                {
                    'error': 'La optimización no devolvió resultados'
                },
                status=400,
            )

        # ----------------------------------------------------
        # El optimizador devuelve un error controlado
        # ----------------------------------------------------
        if 'error' in resultado:
            registrar_auditoria(
                request=request,
                accion=ACCION_OPTIMIZATION,
                objeto=parametros,
                descripcion=(
                    f"Optimización rechazada para el escenario "
                    f"«{parametros.nombre_escenario}»: "
                    f"{resultado.get('error', 'Error desconocido')}"
                ),
                datos_nuevos={
                    'escenario': parametros.nombre_escenario,
                    'tipo_modelo': parametros.tipo_modelo,
                    'parametros_id': parametros.id,
                    'tipo_error': resultado.get(
                        'tipo_error',
                        'desconocido',
                    ),
                },
                resultado='fallido',
            )

            return JsonResponse(
                {
                    'error': resultado['error']
                },
                status=400,
            )

        # ----------------------------------------------------
        # Guardar resultado
        # ----------------------------------------------------
        resultado_obj = ResultadoOptimizacion.objects.create(
            parametros=parametros,
            datos_json=resultado,
        )

        # ----------------------------------------------------
        # Auditoría resumida.
        #
        # NO guardamos todo el resultado de optimización en
        # AuditLog para evitar duplicar grandes estructuras JSON.
        # ----------------------------------------------------
        resumen_auditoria = {
            'resultado_id': resultado_obj.id,
            'parametros_id': parametros.id,
            'escenario': parametros.nombre_escenario,
            'tipo_modelo': parametros.tipo_modelo,
            'total_centros': resultado.get('total_centros', 0),
            'total_demandas': resultado.get('total_demandas', 0),
            'poblacion_atendida': resultado.get(
                'poblacion_atendida',
                0,
            ),
            'porcentaje_cubierto': resultado.get(
                'porcentaje_cubierto',
                0,
            ),
            'distancia_total_km': resultado.get(
                'distancia_total_km',
                0,
            ),
            'costo_total': resultado.get(
                'costo_total',
                0,
            ),
            'tiempo_ejecucion_seg': resultado.get(
                'tiempo_ejecucion_seg',
                0,
            ),
        }

        registrar_auditoria(
            request=request,
            accion=ACCION_OPTIMIZATION,
            objeto=resultado_obj,
            objeto_repr=(
                f"Resultado #{resultado_obj.id} — "
                f"{parametros.nombre_escenario}"
            ),
            datos_nuevos=resumen_auditoria,
            descripcion=(
                f"Optimización ejecutada correctamente para "
                f"el escenario «{parametros.nombre_escenario}»."
            ),
            resultado='exitoso',
        )

        return JsonResponse(
            {
                'resultado_id': resultado_obj.id,
                'datos': resultado,
                'mensaje': 'Optimización ejecutada correctamente',
            }
        )

    except Exception as e:
        logger.error(
            f"Error en api_ejecutar_optimizacion: {e}",
            exc_info=True,
        )

        # ----------------------------------------------------
        # Intentamos registrar también los errores inesperados.
        # La auditoría NUNCA debe ocultar el error original.
        # ----------------------------------------------------
        try:
            objeto = None

            if 'parametros' in locals():
                objeto = parametros

            registrar_auditoria(
                request=request,
                accion=ACCION_OPTIMIZATION,
                objeto=objeto,
                modelo='core.ParametrosModelo',
                objeto_id=str(param_id),
                descripcion=(
                    f"Error inesperado durante la optimización: {e}"
                ),
                datos_nuevos={
                    'parametros_id': param_id,
                },
                resultado='fallido',
            )
        except Exception as audit_error:
            logger.error(
                f"No se pudo registrar auditoría de optimización: "
                f"{audit_error}",
                exc_info=True,
            )

        return JsonResponse(
            {
                'error': 'Error al ejecutar la optimización'
            },
            status=500,
        )


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
                'fecha': r.fecha_ejecucion.strftime(
                    '%Y-%m-%d %H:%M'
                ),
                'escenario': (
                    r.parametros.nombre_escenario
                    if r.parametros
                    else 'Sin escenario'
                ),
                'tipo_modelo': (
                    r.parametros.tipo_modelo
                    if r.parametros
                    else ''
                ),
                'resumen': {
                    'distancia_total': r.datos_json.get(
                        'distancia_total_km'
                    ),
                    'poblacion_atendida': r.datos_json.get(
                        'poblacion_atendida'
                    ),
                    'porcentaje_cubierto': r.datos_json.get(
                        'porcentaje_cubierto'
                    ),
                    'costo_total': r.datos_json.get(
                        'costo_total'
                    ),
                },
                'centros': r.datos_json.get(
                    'centros',
                    []
                )[:5],
            }
            for r in resultados
        ]

        return JsonResponse(
            data,
            safe=False,
        )

    except Exception as e:
        logger.error(
            f"Error en api_listar_resultados: {e}",
            exc_info=True,
        )

        return JsonResponse(
            {'error': 'Error al listar resultados'},
            status=500,
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def api_detalle_resultado(request, resultado_id):
    """Devuelve el detalle de un resultado específico."""
    try:
        resultado = get_object_or_404(
            ResultadoOptimizacion.objects.select_related(
                'parametros'
            ),
            pk=resultado_id,
        )

        data = {
            'id': resultado.id,
            'fecha': resultado.fecha_ejecucion.strftime(
                '%Y-%m-%d %H:%M'
            ),
            'escenario': (
                resultado.parametros.nombre_escenario
                if resultado.parametros
                else 'Sin escenario'
            ),
        }

        data.update(resultado.datos_json)

        return JsonResponse(data)

    except Exception as e:
        logger.error(
            f"Error en api_detalle_resultado: {e}",
            exc_info=True,
        )

        return JsonResponse(
            {'error': 'Error al obtener el detalle'},
            status=500,
        )


# ============================================================
# APIs DE MAPA DE CALOR
# ============================================================

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def api_mapa_calor(request):
    """Genera el mapa de calor con pesos personalizables."""
    try:
        pesos = {
            clave: float(
                request.query_params.get(clave, 1.0)
            )
            for clave in (
                'densidad',
                'vulnerabilidad',
                'distancia',
                'heridos',
                'fallecidos',
                'damnificados',
                'reportes',
            )
        }

        return JsonResponse(
            generar_mapa_calor(pesos),
            safe=False,
        )

    except Exception as e:
        logger.error(
            f"Error en api_mapa_calor: {e}",
            exc_info=True,
        )

        return JsonResponse(
            {'error': 'Error al generar el mapa de calor'},
            status=500,
        )


# ============================================================
# APIs DE COMANDOS DE GESTIÓN
# ============================================================

COMANDOS_PERMITIDOS = (
    'cargar_datos_prueba',
    'cargar_datos_masivos',
    'importar_limites',
)


@api_view(['POST'])
@permission_classes([IsAuthenticated, EsAdministrador])
def api_ejecutar_comando(request):
    """
    Ejecuta comandos de gestión predefinidos.

    Solo permite comandos de la whitelist COMANDOS_PERMITIDOS y requiere
    permisos de administrador.

    La ejecución queda registrada en la bitácora.
    """
    comando = request.data.get('comando')

    if not comando:
        registrar_auditoria(
            request=request,
            accion=ACCION_COMMAND,
            modelo='django.core.management',
            descripcion='Intento de ejecutar comando sin especificarlo.',
            resultado='fallido',
        )

        return JsonResponse(
            {'error': 'Se requiere un comando'},
            status=400,
        )

    if comando not in COMANDOS_PERMITIDOS:
        registrar_auditoria(
            request=request,
            accion=ACCION_COMMAND,
            modelo='django.core.management',
            objeto_id=comando,
            objeto_repr=comando,
            descripcion=(
                f'Intento de ejecutar comando no permitido: {comando}'
            ),
            datos_nuevos={
                'comando': comando,
                'permitido': False,
            },
            resultado='fallido',
        )

        return JsonResponse(
            {
                'error': f'Comando no permitido: {comando}'
            },
            status=400,
        )

    salida = StringIO()
    stdout_original = sys.stdout

    try:
        sys.stdout = salida

        call_command(comando)

        salida_texto = salida.getvalue()

        # Evitamos almacenar una salida potencialmente enorme
        # en la bitácora.
        salida_resumen = salida_texto[:5000]

        registrar_auditoria(
            request=request,
            accion=ACCION_COMMAND,
            modelo='django.core.management',
            objeto_id=comando,
            objeto_repr=comando,
            descripcion=(
                f'Comando de gestión «{comando}» ejecutado '
                f'correctamente.'
            ),
            datos_nuevos={
                'comando': comando,
                'salida': salida_resumen,
                'salida_truncada': len(salida_texto) > 5000,
            },
            resultado='exitoso',
        )

        return JsonResponse(
            {
                'success': True,
                'mensaje': (
                    f'Comando {comando} ejecutado correctamente'
                ),
                'salida': salida_texto,
            }
        )

    except Exception as e:
        logger.error(
            f"Error ejecutando comando {comando}: {e}",
            exc_info=True,
        )

        try:
            registrar_auditoria(
                request=request,
                accion=ACCION_COMMAND,
                modelo='django.core.management',
                objeto_id=comando,
                objeto_repr=comando,
                descripcion=(
                    f'Error al ejecutar el comando '
                    f'«{comando}»: {e}'
                ),
                datos_nuevos={
                    'comando': comando,
                    'salida': salida.getvalue()[:5000],
                },
                resultado='fallido',
            )
        except Exception as audit_error:
            logger.error(
                f"No se pudo registrar auditoría del comando: "
                f"{audit_error}",
                exc_info=True,
            )

        return JsonResponse(
            {'error': 'Error al ejecutar el comando'},
            status=500,
        )

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

        response = HttpResponse(
            content_type='text/csv'
        )

        response['Content-Disposition'] = (
            'attachment; '
            'filename="resultados_optimizacion.csv"'
        )

        writer = csv.writer(response)

        writer.writerow([
            'ID',
            'Fecha',
            'Escenario',
            'Distancia Total (km)',
            'Población Atendida',
            '% Cubierto',
            'Costo Total',
        ])

        cantidad_exportada = 0

        for r in resultados:
            writer.writerow([
                r.id,
                r.fecha_ejecucion.strftime(
                    '%Y-%m-%d %H:%M'
                ),
                (
                    r.parametros.nombre_escenario
                    if r.parametros
                    else 'Sin escenario'
                ),
                r.datos_json.get(
                    'distancia_total_km',
                    0,
                ),
                r.datos_json.get(
                    'poblacion_atendida',
                    0,
                ),
                r.datos_json.get(
                    'porcentaje_cubierto',
                    0,
                ),
                r.datos_json.get(
                    'costo_total',
                    0,
                ),
            ])

            cantidad_exportada += 1

        registrar_auditoria(
            request=request,
            accion=ACCION_EXPORT,
            modelo='core.ResultadoOptimizacion',
            objeto_repr='resultados_optimizacion.csv',
            descripcion=(
                'Exportación de resultados de optimización a CSV.'
            ),
            datos_nuevos={
                'formato': 'CSV',
                'archivo': 'resultados_optimizacion.csv',
                'cantidad_registros': cantidad_exportada,
            },
            resultado='exitoso',
        )

        return response

    except Exception as e:
        logger.error(
            f"Error en api_exportar_csv: {e}",
            exc_info=True,
        )

        try:
            registrar_auditoria(
                request=request,
                accion=ACCION_EXPORT,
                modelo='core.ResultadoOptimizacion',
                objeto_repr='resultados_optimizacion.csv',
                descripcion=(
                    f'Error al exportar resultados a CSV: {e}'
                ),
                datos_nuevos={
                    'formato': 'CSV',
                    'archivo': 'resultados_optimizacion.csv',
                },
                resultado='fallido',
            )
        except Exception as audit_error:
            logger.error(
                f"No se pudo registrar auditoría de exportación CSV: "
                f"{audit_error}",
                exc_info=True,
            )

        return JsonResponse(
            {'error': 'Error al exportar CSV'},
            status=500,
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def api_exportar_geojson(request):
    """Exporta los centros del último resultado a GeoJSON."""
    try:
        resultado = (
            ResultadoOptimizacion.objects
            .select_related('parametros')
            .order_by('-fecha_ejecucion')
            .first()
        )

        if not resultado:
            registrar_auditoria(
                request=request,
                accion=ACCION_EXPORT,
                modelo='core.ResultadoOptimizacion',
                objeto_repr='centros_seleccionados.geojson',
                descripcion=(
                    'Intento de exportar GeoJSON sin resultados '
                    'de optimización disponibles.'
                ),
                datos_nuevos={
                    'formato': 'GeoJSON',
                    'archivo': 'centros_seleccionados.geojson',
                },
                resultado='fallido',
            )

            return JsonResponse(
                {
                    'error': 'No hay resultados para exportar'
                },
                status=404,
            )

        geojson = services.construir_geojson_centros(
            resultado.datos_json
        )

        cantidad_features = len(
            geojson.get('features', [])
        )

        response = HttpResponse(
            json.dumps(
                geojson,
                indent=2,
                ensure_ascii=False,
            ),
            content_type='application/geo+json',
        )

        response['Content-Disposition'] = (
            'attachment; '
            'filename="centros_seleccionados.geojson"'
        )

        registrar_auditoria(
            request=request,
            accion=ACCION_EXPORT,
            objeto=resultado,
            objeto_repr='centros_seleccionados.geojson',
            descripcion=(
                'Exportación de centros seleccionados a GeoJSON.'
            ),
            datos_nuevos={
                'formato': 'GeoJSON',
                'archivo': 'centros_seleccionados.geojson',
                'resultado_id': resultado.id,
                'cantidad_features': cantidad_features,
            },
            resultado='exitoso',
        )

        return response

    except Exception as e:
        logger.error(
            f"Error en api_exportar_geojson: {e}",
            exc_info=True,
        )

        try:
            registrar_auditoria(
                request=request,
                accion=ACCION_EXPORT,
                modelo='core.ResultadoOptimizacion',
                objeto_repr='centros_seleccionados.geojson',
                descripcion=(
                    f'Error al exportar GeoJSON: {e}'
                ),
                datos_nuevos={
                    'formato': 'GeoJSON',
                    'archivo': 'centros_seleccionados.geojson',
                },
                resultado='fallido',
            )
        except Exception as audit_error:
            logger.error(
                f"No se pudo registrar auditoría de exportación "
                f"GeoJSON: {audit_error}",
                exc_info=True,
            )

        return JsonResponse(
            {'error': 'Error al exportar GeoJSON'},
            status=500,
        )


# ============================================================
# HEALTH CHECK
# ============================================================

def health_check(request):
    """
    Endpoint público para verificación de salud del servicio.

    No se registra en AuditLog porque es una consulta técnica
    automática y generaría ruido innecesario en la bitácora.
    """
    from django.utils import timezone

    return JsonResponse({
        'status': 'ok',
        'service': 'cobijo-vzla',
        'timestamp': timezone.now().isoformat(),
    })
