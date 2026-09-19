"""
Administración del módulo `publico`.

Este módulo sirve las APIs del portal público (mapa, búsqueda, reportes).
No define modelos propios: los reportes ciudadanos se registran en
`apps.emergencias.admin`.

Aquí no se registra nada, pero mantenemos el archivo por convención.
"""
from django.contrib import admin  # noqa: F401