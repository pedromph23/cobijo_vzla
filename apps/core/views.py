"""
Vistas de utilidad del módulo Core.

Proporciona endpoints JSON con KPIs y estadísticas agregadas para
dashboards y reportes.
"""
from django.db.models import Count, Sum, Avg, Q
from django.http import JsonResponse
from django.views.decorators.http import require_GET

from .models import (
    Estado,
    Parroquia,
    RefugioExistente,
    ZonaAfectada,
    PuntoDemanda,
    ResultadoOptimizacion,
)


@require_GET
def api_kpis(request):
    """
    KPIs generales del sistema.

    Retorna un JSON con los principales indicadores para dashboards.
    """
    try:
        # Refugios
        refugios = RefugioExistente.objects.aggregate(
            total=Count('id'),
            operativos=Count('id', filter=Q(operativo=True)),
            capacidad_total=Sum('capacidad_total'),
            capacidad_disponible=Sum('capacidad_disponible'),
        )

        # Zonas activas
        zonas = ZonaAfectada.objects.filter(fecha_fin__isnull=True).aggregate(
            total=Count('id'),
            heridos=Sum('heridos'),
            fallecidos=Sum('fallecidos'),
            damnificados=Sum('damnificados'),
        )

        # Optimización
        ultima_opt = ResultadoOptimizacion.objects.first()

        return JsonResponse({
            'refugios': {
                'total': refugios['total'] or 0,
                'operativos': refugios['operativos'] or 0,
                'capacidad_total': refugios['capacidad_total'] or 0,
                'capacidad_disponible': refugios['capacidad_disponible'] or 0,
            },
            'zonas_activas': {
                'total': zonas['total'] or 0,
                'heridos': zonas['heridos'] or 0,
                'fallecidos': zonas['fallecidos'] or 0,
                'damnificados': zonas['damnificados'] or 0,
            },
            'territorio': {
                'estados': Estado.objects.count(),
                'parroquias': Parroquia.objects.count(),
            },
            'demanda': {
                'puntos': PuntoDemanda.objects.count(),
                'poblacion_afectada': PuntoDemanda.objects.aggregate(
                    total=Sum('poblacion')
                )['total'] or 0,
            },
            'optimizacion': {
                'resultados_guardados': ResultadoOptimizacion.objects.count(),
                'ultima_ejecucion': (
                    ultima_opt.fecha_ejecucion.isoformat()
                    if ultima_opt else None
                ),
                'ultima_cobertura': (
                    ultima_opt.porcentaje_cubierto
                    if ultima_opt else None
                ),
            },
        })

    except Exception as e:
        return JsonResponse(
            {'error': f'Error generando KPIs: {str(e)}'},
            status=500
        )


@require_GET
def api_refugios_criticos(request):
    """
    Lista de refugios con ocupación >= 80%.

    Útil para el dashboard: refugios que necesitan reabastecimiento.
    """
    try:
        refugios = RefugioExistente.objects.filter(
            operativo=True,
            capacidad_total__gt=0,
        )
        criticos = []
        for r in refugios:
            pct = r.porcentaje_ocupacion
            if pct >= 80:
                criticos.append({
                    'id': r.id,
                    'nombre': r.nombre,
                    'direccion': r.direccion,
                    'ocupacion': pct,
                    'capacidad_disponible': r.capacidad_disponible,
                    'telefono': r.telefono,
                })

        criticos.sort(key=lambda x: x['ocupacion'], reverse=True)
        return JsonResponse({'refugios': criticos, 'total': len(criticos)})

    except Exception as e:
        return JsonResponse(
            {'error': f'Error: {str(e)}'},
            status=500
        )