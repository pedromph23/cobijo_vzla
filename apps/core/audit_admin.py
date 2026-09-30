"""Registro administrativo de la bitácora de auditoría."""
from django.contrib import admin

from .models import AuditLog


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = (
        "fecha_hora", "usuario", "accion", "modelo",
        "objeto_id", "resultado", "ip",
    )
    list_filter = ("accion", "resultado", "modelo", "fecha_hora")
    search_fields = (
        "usuario__username", "usuario__email", "modelo",
        "objeto_id", "objeto_repr", "descripcion", "ip",
    )
    date_hierarchy = "fecha_hora"
    ordering = ("-fecha_hora",)
    list_per_page = 50
    readonly_fields = (
        "fecha_hora", "usuario", "accion", "modelo", "objeto_id",
        "objeto_repr", "descripcion", "ip", "metodo_http", "ruta",
        "user_agent", "datos_anteriores", "datos_nuevos", "resultado",
    )
    fieldsets = (
        ("Evento", {
            "fields": ("fecha_hora", "accion", "resultado", "usuario"),
        }),
        ("Objeto afectado", {
            "fields": ("modelo", "objeto_id", "objeto_repr", "descripcion"),
        }),
        ("Solicitud", {
            "fields": ("ip", "metodo_http", "ruta", "user_agent"),
        }),
        ("Cambios", {
            "fields": ("datos_anteriores", "datos_nuevos"),
            "classes": ("collapse",),
        }),
    )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
