"""
Administración del módulo de reportes.

Este módulo no define modelos propios: genera archivos Excel/PDF a partir
de datos existentes en `core` y `emergencias`.

Aquí no se registra nada. Los modelos origen se registran en sus apps
respectivas.
"""
from django.contrib import admin  # noqa: F401