"""
Administración de la bitácora de auditoría de CobijoVzla.

La bitácora es de solo lectura para los usuarios administrativos.
Permite consultar, filtrar y analizar las operaciones realizadas
en el sistema sin modificar los registros históricos.
"""

from django.contrib import admin
from django.utils.html import format_html

from .models import AuditLog


# ============================================================
# HELPERS
# ============================================================

def _badge(texto, color="#6c757d"):
    """Genera un badge visual para el listado del admin."""
    return format_html(
        '<span style="'
        'display:inline-block;'
        'padding:3px 9px;'
        'border-radius:999px;'
        'font-size:11px;'
        'font-weight:600;'
        'background:{};'
        'color:white;'
        'white-space:nowrap;'
        '">{}</span>',
        color,
        texto,
    )


# ============================================================
# ADMINISTRACIÓN DE AUDITORÍA
# ============================================================

@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):

    # --------------------------------------------------------
    # LISTADO
    # --------------------------------------------------------

    list_display = (
        "fecha_hora",
        "usuario_display",
        "accion_badge",
        "objeto_display",
        "resultado_badge",
        "ip",
    )

    list_filter = (
        "accion",
        "resultado",
        "modelo",
        "fecha_hora",
    )

    search_fields = (
        "usuario__username",
        "usuario__email",
        "modelo",
        "objeto_id",
        "objeto_repr",
        "descripcion",
        "ip",
        "ruta",
    )

    date_hierarchy = "fecha_hora"

    ordering = ("-fecha_hora",)

    list_per_page = 50

    list_select_related = ("usuario",)

    # --------------------------------------------------------
    # CAMPOS DE SOLO LECTURA
    # --------------------------------------------------------

    readonly_fields = (
        "fecha_hora",
        "usuario",
        "accion",
        "modelo",
        "objeto_id",
        "objeto_repr",
        "descripcion",
        "ip",
        "metodo_http",
        "ruta",
        "user_agent",
        "datos_anteriores",
        "datos_nuevos",
        "resultado",
    )

    # --------------------------------------------------------
    # FORMULARIO DE DETALLE
    # --------------------------------------------------------

    fieldsets = (
        (
            "Evento",
            {
                "fields": (
                    "fecha_hora",
                    "accion",
                    "resultado",
                    "usuario",
                ),
            },
        ),
        (
            "Objeto afectado",
            {
                "fields": (
                    "modelo",
                    "objeto_id",
                    "objeto_repr",
                    "descripcion",
                ),
            },
        ),
        (
            "Solicitud",
            {
                "fields": (
                    "ip",
                    "metodo_http",
                    "ruta",
                    "user_agent",
                ),
            },
        ),
        (
            "Cambios registrados",
            {
                "fields": (
                    "datos_anteriores",
                    "datos_nuevos",
                ),
                "classes": ("collapse",),
            },
        ),
    )

    # --------------------------------------------------------
    # VISUALIZACIÓN
    # --------------------------------------------------------

    @admin.display(
        description="Usuario",
        ordering="usuario__username",
    )
    def usuario_display(self, obj):
        if not obj.usuario:
            return _badge("Sistema", "#6c757d")

        nombre = obj.usuario.get_username()

        if obj.usuario.is_superuser:
            return _badge(nombre, "#6f42c1")

        if obj.usuario.is_staff:
            return _badge(nombre, "#0066cc")

        return nombre

    @admin.display(
        description="Acción",
        ordering="accion",
    )
    def accion_badge(self, obj):
        colores = {
            "LOGIN": "#198754",
            "LOGOUT": "#6c757d",
            "LOGIN_FAILED": "#dc3545",
            "CREATE": "#198754",
            "UPDATE": "#0066cc",
            "DELETE": "#dc3545",
            "IMPORT": "#fd7e14",
            "EXPORT": "#6f42c1",
            "OPTIMIZATION": "#0d6efd",
            "COMMAND": "#212529",
            "REPORT": "#20c997",
        }

        texto = obj.get_accion_display()

        return _badge(
            texto,
            colores.get(obj.accion, "#6c757d"),
        )

    @admin.display(
        description="Objeto",
    )
    def objeto_display(self, obj):
        if not obj.modelo:
            return "—"

        if obj.objeto_id:
            identificador = f"#{obj.objeto_id}"
        else:
            identificador = ""

        if obj.objeto_repr:
            nombre = obj.objeto_repr[:60]
        else:
            nombre = "Sin descripción"

        return format_html(
            '<strong>{}</strong> {}',
            f"{obj.modelo}",
            identificador,
        ) + format_html(
            '<br><span style="color:#6c757d;font-size:11px;">{}</span>',
            nombre,
        )

    @admin.display(
        description="Resultado",
        ordering="resultado",
    )
    def resultado_badge(self, obj):
        if obj.resultado == "exitoso":
            return _badge("Exitoso", "#198754")

        return _badge("Fallido", "#dc3545")

    # --------------------------------------------------------
    # SEGURIDAD
    # --------------------------------------------------------

    def has_add_permission(self, request):
        """
        La bitácora no puede ser creada manualmente desde Admin.
        """
        return False

    def has_change_permission(self, request, obj=None):
        """
        Los registros de auditoría son inmutables.
        """
        return False

    def has_delete_permission(self, request, obj=None):
        """
        Los registros no pueden eliminarse desde Admin.
        """
        return False

    # --------------------------------------------------------
    # ACCESO AL MODELO
    # --------------------------------------------------------

    def has_view_permission(self, request, obj=None):
        """
        Solo personal administrativo puede consultar la bitácora.

        Django Admin ya exige autenticación, pero mantenemos
        explícita la regla para evitar que un usuario autenticado
        no administrativo pueda acceder si posteriormente cambia
        la configuración de permisos.
        """
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.is_staff
        )

    # --------------------------------------------------------
    # CONTEXTO DEL ADMIN
    # --------------------------------------------------------

    def get_queryset(self, request):
        """
        Optimiza la consulta evitando consultas adicionales
        para obtener el usuario asociado a cada evento.
        """
        return (
            super()
            .get_queryset(request)
            .select_related("usuario")
        )