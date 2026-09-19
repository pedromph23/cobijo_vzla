"""
Configuración del admin de Django para el módulo Core.

Proporciona una interfaz completa para gestionar estados, parroquias,
refugios, zonas afectadas y parámetros de optimización.
"""
from django.contrib import admin
from django.contrib.gis.admin import GISModelAdmin
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from django.db.models import Count, Sum

from .models import (
    Estado,
    Parroquia,
    PuntoDemanda,
    SitioCandidato,
    RefugioExistente,
    ZonaAfectada,
    ParametrosModelo,
    ResultadoOptimizacion,
)


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
# ESTADO
# ============================================================

@admin.register(Estado)
class EstadoAdmin(GISModelAdmin):
    list_display = ('nombre', 'codigo_ine', 'total_parroquias', 'tiene_geom')
    search_fields = ('nombre', 'codigo_ine')
    ordering = ('nombre',)
    list_per_page = 30

    fieldsets = (
        ('Información básica', {
            'fields': ('nombre', 'codigo_ine')
        }),
        ('Geometría', {
            'fields': ('geom',),
            'classes': ('collapse',),
        }),
    )

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.annotate(_total_parroquias=Count('parroquias'))

    @admin.display(description='Parroquias', ordering='_total_parroquias')
    def total_parroquias(self, obj):
        n = getattr(obj, '_total_parroquias', 0)
        color = '#28a745' if n > 0 else '#6c757d'
        return badge(str(n), color)

    @admin.display(boolean=True, description='Geometría')
    def tiene_geom(self, obj):
        return obj.geom is not None


# ============================================================
# PARROQUIA
# ============================================================

@admin.register(Parroquia)
class ParroquiaAdmin(GISModelAdmin):
    list_display = (
        'nombre', 'estado', 'poblacion_fmt',
        'densidad_poblacional', 'indice_vulnerabilidad', 'tiene_geom'
    )
    list_filter = ('estado',)
    search_fields = ('nombre', 'codigo_ine', 'estado__nombre')
    ordering = ('estado__nombre', 'nombre')
    list_select_related = ('estado',)
    list_per_page = 50

    fieldsets = (
        ('Ubicación', {
            'fields': ('nombre', 'estado', 'codigo_ine')
        }),
        ('Datos demográficos', {
            'fields': (
                'poblacion',
                'densidad_poblacional',
                'indice_vulnerabilidad',
            )
        }),
        ('Geometría', {
            'fields': ('geom',),
            'classes': ('collapse',),
        }),
    )

    @admin.display(description='Población', ordering='poblacion')
    def poblacion_fmt(self, obj):
        return f"{obj.poblacion:,}".replace(',', '.')

    @admin.display(boolean=True, description='Geometría')
    def tiene_geom(self, obj):
        return obj.geom is not None


# ============================================================
# PUNTO DE DEMANDA
# ============================================================

@admin.register(PuntoDemanda)
class PuntoDemandaAdmin(GISModelAdmin):
    list_display = (
        'nombre', 'parroquia', 'poblacion_fmt',
        'vulnerabilidad_badge', 'coordenadas'
    )
    list_filter = ('parroquia__estado',)
    search_fields = ('nombre', 'descripcion', 'parroquia__nombre')
    list_select_related = ('parroquia', 'parroquia__estado')
    list_per_page = 50
    autocomplete_fields = ('parroquia',)

    fieldsets = (
        ('Información', {
            'fields': ('nombre', 'parroquia', 'ubicacion')
        }),
        ('Datos', {
            'fields': ('poblacion', 'vulnerabilidad', 'descripcion')
        }),
    )

    @admin.display(description='Población', ordering='poblacion')
    def poblacion_fmt(self, obj):
        return f"{obj.poblacion:,}".replace(',', '.')

    @admin.display(description='Vulnerabilidad', ordering='vulnerabilidad')
    def vulnerabilidad_badge(self, obj):
        v = obj.vulnerabilidad or 0
        if v >= 0.7:
            return badge(f"ALTA ({v:.2f})", '#dc3545')
        if v >= 0.4:
            return badge(f"MEDIA ({v:.2f})", '#ffc107')
        return badge(f"BAJA ({v:.2f})", '#28a745')

    @admin.display(description='Coordenadas')
    def coordenadas(self, obj):
        if not obj.ubicacion:
            return '—'
        return f"{obj.ubicacion.y:.4f}, {obj.ubicacion.x:.4f}"


# ============================================================
# SITIO CANDIDATO
# ============================================================

@admin.register(SitioCandidato)
class SitioCandidatoAdmin(GISModelAdmin):
    list_display = (
        'nombre', 'capacidad_maxima', 'costo_apertura_fmt',
        'tipo_terreno', 'disponibilidad_badge', 'coordenadas'
    )
    list_filter = ('disponible', 'tipo_terreno')
    search_fields = ('nombre', 'tipo_terreno')
    list_per_page = 50

    actions = ('marcar_disponibles', 'marcar_no_disponibles')

    fieldsets = (
        ('Información', {
            'fields': ('nombre', 'ubicacion', 'tipo_terreno')
        }),
        ('Capacidad y costos', {
            'fields': (
                'capacidad_maxima',
                'costo_apertura',
                'costo_operacion',
            )
        }),
        ('Disponibilidad', {
            'fields': ('disponible',)
        }),
    )

    @admin.display(description='Costo apertura', ordering='costo_apertura')
    def costo_apertura_fmt(self, obj):
        if obj.costo_apertura:
            return f"${obj.costo_apertura:,.0f}"
        return '—'

    @admin.display(description='Estado', ordering='disponible')
    def disponibilidad_badge(self, obj):
        if obj.disponible:
            return badge('Disponible', '#28a745')
        return badge('No disponible', '#6c757d')

    @admin.display(description='Coordenadas')
    def coordenadas(self, obj):
        if not obj.ubicacion:
            return '—'
        return f"{obj.ubicacion.y:.4f}, {obj.ubicacion.x:.4f}"

    @admin.action(description='Marcar como disponibles')
    def marcar_disponibles(self, request, queryset):
        n = queryset.update(disponible=True)
        self.message_user(request, f"{n} sitios marcados como disponibles.")

    @admin.action(description='Marcar como no disponibles')
    def marcar_no_disponibles(self, request, queryset):
        n = queryset.update(disponible=False)
        self.message_user(request, f"{n} sitios marcados como no disponibles.")


# ============================================================
# REFUGIO EXISTENTE
# ============================================================

@admin.register(RefugioExistente)
class RefugioExistenteAdmin(GISModelAdmin):
    list_display = (
        'nombre', 'direccion_corta', 'ocupacion_badge',
        'estado_operativo', 'telefono', 'coordenadas'
    )
    list_filter = ('operativo',)
    search_fields = ('nombre', 'direccion', 'telefono')
    list_per_page = 50

    actions = ('marcar_operativos', 'marcar_no_operativos')

    fieldsets = (
        ('Información', {
            'fields': ('nombre', 'direccion', 'ubicacion')
        }),
        ('Capacidad', {
            'fields': ('capacidad_total', 'capacidad_disponible')
        }),
        ('Servicios y contacto', {
            'fields': ('servicios', 'telefono', 'horario')
        }),
        ('Estado', {
            'fields': ('operativo',)
        }),
    )

    @admin.display(description='Dirección')
    def direccion_corta(self, obj):
        return obj.direccion[:60] + ('...' if len(obj.direccion) > 60 else '')

    @admin.display(description='Ocupación')
    def ocupacion_badge(self, obj):
        if not obj.capacidad_total:
            return badge('Sin datos', '#6c757d')
        pct = (1 - obj.capacidad_disponible / obj.capacidad_total) * 100
        if pct >= 90:
            return badge(f"{pct:.0f}% LLENO", '#dc3545')
        if pct >= 70:
            return badge(f"{pct:.0f}%", '#ffc107')
        return badge(f"{pct:.0f}%", '#28a745')

    @admin.display(description='Operativo', ordering='operativo')
    def estado_operativo(self, obj):
        if obj.operativo:
            return badge('✅ Operativo', '#28a745')
        return badge('❌ No operativo', '#dc3545')

    @admin.display(description='Coordenadas')
    def coordenadas(self, obj):
        if not obj.ubicacion:
            return '—'
        return f"{obj.ubicacion.y:.4f}, {obj.ubicacion.x:.4f}"

    @admin.action(description='Marcar como operativos')
    def marcar_operativos(self, request, queryset):
        n = queryset.update(operativo=True)
        self.message_user(request, f"{n} refugios marcados como operativos.")

    @admin.action(description='Marcar como no operativos')
    def marcar_no_operativos(self, request, queryset):
        n = queryset.update(operativo=False)
        self.message_user(request, f"{n} refugios marcados como no operativos.")


# ============================================================
# ZONA AFECTADA
# ============================================================

@admin.register(ZonaAfectada)
class ZonaAfectadaAdmin(GISModelAdmin):
    list_display = (
        'nombre', 'evento', 'nivel_alerta_badge',
        'total_afectados', 'esta_activa', 'fecha_inicio'
    )
    list_filter = ('nivel_alerta', 'evento', 'fecha_inicio')
    search_fields = ('nombre', 'descripcion', 'evento__nombre')
    list_select_related = ('evento',)
    list_per_page = 50
    date_hierarchy = 'fecha_inicio'
    autocomplete_fields = ('evento',)

    fieldsets = (
        ('Información', {
            'fields': ('evento', 'nombre', 'descripcion')
        }),
        ('Clasificación', {
            'fields': ('nivel_alerta', 'geom')
        }),
        ('Fechas', {
            'fields': ('fecha_inicio', 'fecha_fin')
        }),
        ('Afectación', {
            'fields': ('heridos', 'fallecidos', 'damnificados')
        }),
    )

    @admin.display(description='Alerta', ordering='nivel_alerta')
    def nivel_alerta_badge(self, obj):
        colores = {'alto': '#dc3545', 'medio': '#ffc107', 'bajo': '#28a745'}
        return badge(obj.get_nivel_alerta_display().upper(), colores.get(obj.nivel_alerta, '#6c757d'))

    @admin.display(description='Total afectados')
    def total_afectados(self, obj):
        return f"{obj.total_afectados:,}".replace(',', '.')

    @admin.display(boolean=True, description='Activa')
    def esta_activa(self, obj):
        return obj.fecha_fin is None


# ============================================================
# PARÁMETROS DE MODELO
# ============================================================

@admin.register(ParametrosModelo)
class ParametrosModeloAdmin(admin.ModelAdmin):
    list_display = (
        'nombre_escenario', 'tipo_modelo', 'p',
        'radio_cobertura_fmt', 'filtro_estado', 'fecha_creacion'
    )
    list_filter = ('tipo_modelo', 'filtro_estado')
    search_fields = ('nombre_escenario',)
    list_select_related = ('filtro_estado',)
    readonly_fields = ('fecha_creacion',)
    list_per_page = 30

    fieldsets = (
        ('Identificación', {
            'fields': ('nombre_escenario', 'tipo_modelo')
        }),
        ('Parámetros del modelo', {
            'fields': ('p', 'radio_cobertura', 'presupuesto')
        }),
        ('Ponderadores', {
            'fields': (
                'ponderador_vulnerabilidad',
                'ponderador_heridos',
                'ponderador_fallecidos',
                'ponderador_damnificados',
            )
        }),
        ('Filtros', {
            'fields': ('filtro_estado',)
        }),
        ('Metadata', {
            'fields': ('fecha_creacion',),
            'classes': ('collapse',),
        }),
    )

    @admin.display(description='Radio de cobertura')
    def radio_cobertura_fmt(self, obj):
        return f"{obj.radio_cobertura / 1000:.1f} km"


# ============================================================
# RESULTADO DE OPTIMIZACIÓN
# ============================================================

@admin.register(ResultadoOptimizacion)
class ResultadoOptimizacionAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'parametros', 'fecha_ejecucion',
        'resumen_centros', 'resumen_cobertura'
    )
    list_filter = ('fecha_ejecucion', 'parametros__tipo_modelo')
    search_fields = ('parametros__nombre_escenario',)
    list_select_related = ('parametros',)
    readonly_fields = ('parametros', 'fecha_ejecucion', 'datos_json_preview')
    list_per_page = 30
    date_hierarchy = 'fecha_ejecucion'

    fieldsets = (
        ('Metadata', {
            'fields': ('parametros', 'fecha_ejecucion')
        }),
        ('Resultado', {
            'fields': ('datos_json_preview',)
        }),
    )

    def has_add_permission(self, request):
        # Los resultados se generan automáticamente
        return False

    @admin.display(description='Centros')
    def resumen_centros(self, obj):
        n = len((obj.datos_json or {}).get('centros', []))
        return badge(f"{n} centros", '#0066cc')

    @admin.display(description='Cobertura')
    def resumen_cobertura(self, obj):
        pct = (obj.datos_json or {}).get('porcentaje_cubierto', 0)
        if pct >= 80:
            return badge(f"{pct}%", '#28a745')
        if pct >= 50:
            return badge(f"{pct}%", '#ffc107')
        return badge(f"{pct}%", '#dc3545')

    @admin.display(description='Vista previa del resultado')
    def datos_json_preview(self, obj):
        if not obj.datos_json:
            return '—'
        resumen = {
            'centros': len(obj.datos_json.get('centros', [])),
            'distancia_total_km': obj.datos_json.get('distancia_total_km'),
            'poblacion_atendida': obj.datos_json.get('poblacion_atendida'),
            'porcentaje_cubierto': obj.datos_json.get('porcentaje_cubierto'),
            'costo_total': obj.datos_json.get('costo_total'),
        }
        html = '<ul style="margin:0;padding-left:1rem;">'
        for k, v in resumen.items():
            html += f'<li><strong>{k.replace("_", " ").title()}:</strong> {v}</li>'
        html += '</ul>'
        return mark_safe(html)


# ============================================================
# TÍTULOS DEL ADMIN
# ============================================================

admin.site.site_header = "CobijoVzla · Administración"
admin.site.site_title = "CobijoVzla"
admin.site.index_title = "Panel de gestión de datos"