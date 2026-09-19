"""
Administración del módulo `mapa`.

Este módulo no define modelos propios: gestiona el panel administrativo
mediante vistas, no mediante el Django admin. Los modelos que este panel
utiliza (PuntoDemanda, SitioCandidato, etc.) se registran en `apps.core.admin`.

Aquí personalizamos el índice del admin de Django para mejorar la
experiencia de los gestores.
"""
from django.contrib import admin


# ============================================================
# PERSONALIZACIÓN DEL ÍNDICE DEL ADMIN
# ============================================================

admin.site.index_title = 'CobijoVzla · Gestión de datos'
admin.site.site_header = 'CobijoVzla'
admin.site.site_title = 'CobijoVzla'