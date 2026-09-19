"""
Vistas de utilidad del módulo de Emergencias.

Proporciona endpoints JSON con información de eventos activos y
reportes recientes para dashboards.
"""
from django.db.models import Count, Q
from django.http import JsonResponse
from django.views.decorators.http import require_GET
from django.utils import timezone
from datetime import timedelta

from .models import Evento, Reporte
from apps.core.models import ZonaAfectada


@require_GET
def api_eventos_activos(request):
    """
    Lista de eventos activos con conteo de zonas asociadas.

    Retorna JSON apto para dashboards y mapas.
    """
    try:
        eventos = Evento.objects.filter(activo=True).annotate(
            n_zonas=Count('zonas_afectadas')
        ).order_by('-fecha')

        data = [
            {
                'id': e.id,
                'nombre': e.nombre,
                'tipo': e.tipo,
                'tipo_display': e.get_tipo_display(),
                'color': e.color,
                'fecha': e.fecha.isoformat(),
                'magnitud': e.magnitud,
                'total_zonas': e.n_zonas,
                'descripcion': e.descripcion,
            }
            for e in eventos
        ]
        return JsonResponse({'eventos': data, 'total': len(data)})

    except Exception as e:
        return JsonResponse(
            {'error': f'Error: {str(e)}'},
            status=500
        )


@require_GET
def api_reportes_recientes(request):
    """
    Reportes ciudadanos de los últimos 7 días (por defecto).

    Query params:
        ?dias=7   → ventana de tiempo
        ?limite=50 → máximo de reportes
    """
    try:
        dias = int(request.GET.get('dias', 7))
        limite = min(int(request.GET.get('limite', 50)), 200)

        desde = timezone.now() - timedelta(days=dias)
        reportes = (
            Reporte.objects
            .filter(fecha__gte=desde)
            .select_related('zona_afectada', 'punto_demanda')
            .order_by('-fecha')[:limite]
        )

        data = [
            {
                'id': r.id,
                'autor': r.autor_display,
                'texto': r.texto_corto,
                'fecha': r.fecha.isoformat(),
                'verificado': r.verificado,
                'tiene_imagen': r.tiene_imagen,
                'imagen_url': r.imagen.url if r.imagen else None,
                'asociado_a': r.asociado_a,
                'zona_id': r.zona_afectada_id,
                'punto_id': r.punto_demanda_id,
            }
            for r in reportes
        ]

        return JsonResponse({
            'reportes': data,
            'total': len(data),
            'dias': dias,
        })

    except Exception as e:
        return JsonResponse(
            {'error': f'Error: {str(e)}'},
            status=500
        )


@require_GET
def api_emergencias_kpis(request):
    """
    KPIs agregados de emergencias para dashboards.
    """
    try:
        eventos = Evento.objects.aggregate(
            total=Count('id'),
            activos=Count('id', filter=Q(activo=True)),
        )

        zonas = ZonaAfectada.objects.filter(fecha_fin__isnull=True).aggregate(
            total=Count('id'),
        )

        hace_24h = timezone.now() - timedelta(hours=24)
        hace_7d = timezone.now() - timedelta(days=7)

        return JsonResponse({
            'eventos': {
                'total': eventos['total'] or 0,
                'activos': eventos['activos'] or 0,
            },
            'zonas_activas': zonas['total'] or 0,
            'reportes': {
                'ultimas_24h': Reporte.objects.filter(fecha__gte=hace_24h).count(),
                'ultimos_7d': Reporte.objects.filter(fecha__gte=hace_7d).count(),
                'pendientes_verificar': Reporte.objects.filter(verificado=False).count(),
            },
        })

    except Exception as e:
        return JsonResponse(
            {'error': f'Error: {str(e)}'},
            status=500
        )