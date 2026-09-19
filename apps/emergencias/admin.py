"""
Configuración del admin para el módulo de Emergencias.

Registra Evento y Reporte con filtros, búsqueda, acciones masivas
y visualización útil para la gestión de emergencias.
"""
from django.contrib import admin
from django.contrib.gis.admin import GISModelAdmin
from django.utils.html import format_html
from django.utils.safestring import mark_safe

from .models import Evento, Reporte


# ============================================================
# HELPERS
# ============================================================

def badge(texto: str, color: str = "#0066cc") -> str:
    """Genera un badge HTML con color."""
    return format_html(
        '<span style="background:{};color:white;padding:3px 10px;'
        'border-radius:12px;font-size:0.75rem;font-weight:600;">{}</span>',
        color, texto
    )


# ============================================================
# EVENTO
# ============================================================

@admin.register(Evento)
class EventoAdmin(admin.ModelAdmin):
    list_display = (
        'nombre', 'tipo_badge', 'fecha',
        'magnitud_fmt', 'estado_badge', 'total_zonas'
    )
    list_filter = ('tipo', 'activo', 'fecha')
    search_fields = ('nombre', 'descripcion')  # ← requerido para autocomplete
    ordering = ('-fecha',)
    list_per_page = 30
    date_hierarchy = 'fecha'

    actions = ('activar_eventos', 'desactivar_eventos')

    fieldsets = (
        ('Información del evento', {
            'fields': ('nombre', 'tipo', 'descripcion')
        }),
        ('Datos técnicos', {
            'fields': ('fecha', 'magnitud')
        }),
        ('Estado', {
            'fields': ('activo',)
        }),
    )

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.prefetch_related('zonas_afectadas')

    @admin.display(description='Tipo', ordering='tipo')
    def tipo_badge(self, obj):
        colores = {
            'inundacion': '#0066cc',
            'terremoto': '#dc3545',
            'deslizamiento': '#8b4513',
            'incendio': '#ff6600',
            'otro': '#6c757d',
        }
        return badge(
            obj.get_tipo_display(),
            colores.get(obj.tipo, '#6c757d')
        )

    @admin.display(description='Magnitud', ordering='magnitud')
    def magnitud_fmt(self, obj):
        if obj.magnitud is None:
            return '—'
        return f"{obj.magnitud:.2f}"

    @admin.display(description='Estado', ordering='activo')
    def estado_badge(self, obj):
        if obj.activo:
            return badge('✅ Activo', '#28a745')
        return badge('⛔ Cerrado', '#6c757d')

    @admin.display(description='Zonas')
    def total_zonas(self, obj):
        n = obj.zonas_afectadas.count()
        return badge(str(n), '#0066cc' if n else '#6c757d')

    @admin.action(description='Marcar eventos como activos')
    def activar_eventos(self, request, queryset):
        n = queryset.update(activo=True)
        self.message_user(request, f"{n} eventos marcados como activos.")

    @admin.action(description='Marcar eventos como cerrados')
    def desactivar_eventos(self, request, queryset):
        n = queryset.update(activo=False)
        self.message_user(request, f"{n} eventos marcados como cerrados.")


# ============================================================
# REPORTE
# ============================================================

@admin.register(Reporte)
class ReporteAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'autor_display', 'texto_corto',
        'fecha', 'tipo_destino', 'verificado_badge',
        'tiene_imagen'
    )
    list_filter = ('verificado', 'fecha')
    search_fields = ('autor', 'texto')
    list_select_related = ('zona_afectada', 'punto_demanda')
    ordering = ('-fecha',)
    list_per_page = 50
    date_hierarchy = 'fecha'
    readonly_fields = ('fecha', 'imagen_preview')

    fieldsets = (
        ('Autor y contenido', {
            'fields': ('autor', 'texto', 'fecha')
        }),
        ('Asociación', {
            'fields': ('zona_afectada', 'punto_demanda')
        }),
        ('Evidencia', {
            'fields': ('imagen', 'imagen_preview'),
            'classes': ('collapse',)
        }),
        ('Verificación', {
            'fields': ('verificado',)
        }),
    )

    actions = ('marcar_verificados', 'marcar_no_verificados', 'marcar_sospechosos')

    @admin.display(description='Autor', ordering='autor')
    def autor_display(self, obj):
        return obj.autor or '— Anónimo —'

    @admin.display(description='Texto')
    def texto_corto(self, obj):
        if not obj.texto:
            return '—'
        return obj.texto[:80] + ('...' if len(obj.texto) > 80 else '')

    @admin.display(description='Asociado a')
    def tipo_destino(self, obj):
        if obj.zona_afectada:
            return badge(f"🗺️ {obj.zona_afectada.nombre[:25]}", '#dc3545')
        if obj.punto_demanda:
            return badge(f"📍 {obj.punto_demanda.nombre[:25]}", '#0066cc')
        return badge('Sin asociar', '#6c757d')

    @admin.display(description='Verificado', ordering='verificado')
    def verificado_badge(self, obj):
        if obj.verificado:
            return badge('✅ Verificado', '#28a745')
        return badge('⏳ Pendiente', '#ffc107')

    @admin.display(boolean=True, description='Imagen')
    def tiene_imagen(self, obj):
        return bool(obj.imagen)

    @admin.display(description='Vista previa')
    def imagen_preview(self, obj):
        if not obj.imagen:
            return '—'
        return mark_safe(
            f'<a href="{obj.imagen.url}" target="_blank">'
            f'<img src="{obj.imagen.url}" style="max-width:300px;'
            f'border-radius:8px;box-shadow:0 2px 8px rgba(0,0,0,0.2);" />'
            f'</a>'
        )

    @admin.action(description='Marcar reportes como verificados')
    def marcar_verificados(self, request, queryset):
        n = queryset.update(verificado=True)
        self.message_user(request, f"{n} reportes marcados como verificados.")

    @admin.action(description='Marcar reportes como pendientes')
    def marcar_no_verificados(self, request, queryset):
        n = queryset.update(verificado=False)
        self.message_user(request, f"{n} reportes marcados como pendientes.")

    @admin.action(description='Marcar como sospechosos (eliminar)')
    def marcar_sospechosos(self, request, queryset):
        """Marca reportes como no verificados y los elimina."""
        n = queryset.count()
        queryset.delete()
        self.message_user(
            request,
            f"{n} reportes eliminados por ser sospechosos/spam."
        )