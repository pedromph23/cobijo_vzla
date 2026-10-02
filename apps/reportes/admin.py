"""
Administración y bitácora del módulo de reportes.
"""
from django.contrib import admin

from .models import RegistroReporte


@admin.register(RegistroReporte)
class RegistroReporteAdmin(admin.ModelAdmin):
    list_display = (
        'fecha_generacion', 'usuario', 'tipo', 'contenido',
        'resultado', 'fecha_desde', 'fecha_hasta', 'archivo', 'ip',
    )
    list_filter = ('resultado', 'tipo', 'contenido', 'fecha_generacion')
    search_fields = ('usuario__username', 'archivo', 'detalle', 'ip')
    readonly_fields = (
        'usuario', 'fecha_generacion', 'tipo', 'contenido',
        'fecha_desde', 'fecha_hasta', 'archivo', 'resultado',
        'detalle', 'ip', 'user_agent',
    )
    date_hierarchy = 'fecha_generacion'
    list_select_related = ('usuario',)
    list_per_page = 50

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser
