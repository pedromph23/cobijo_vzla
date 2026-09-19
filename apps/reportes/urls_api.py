"""
Rutas de la API de reportes.

Solo rutas propias del módulo: generar y descargar reportes.
Las rutas de exportación CSV/GeoJSON viven en `apps.mapa.urls_api`
porque usan datos de resultados de optimización, no de reportes.
"""
from django.urls import path
from . import views

urlpatterns = [
    path('generar/', views.api_generar_reporte, name='generar_reporte'),
    path('descargar/<str:nombre_archivo>/', views.api_descargar_reporte, name='descargar_reporte'),
]