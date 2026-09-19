"""
Rutas de la API del panel administrativo.

Organizadas por categoría para facilitar su lectura.
"""
from django.urls import path
from . import views

urlpatterns = [
    # --- Mapa ---
    path('datos-mapa/', views.api_datos_mapa, name='datos_mapa'),
    path('estadisticas/', views.api_estadisticas, name='estadisticas'),

    # --- Optimización ---
    path('ejecutar-optimizacion/', views.api_ejecutar_optimizacion, name='ejecutar_optimizacion'),
    path('listar-resultados/', views.api_listar_resultados, name='listar_resultados'),
    path('resultados/<int:resultado_id>/', views.api_detalle_resultado, name='detalle_resultado'),

    # --- Mapa de calor ---
    path('mapa-calor-admin/', views.api_mapa_calor, name='mapa_calor_admin'),

    # --- Comandos de gestión ---
    path('ejecutar-comando/', views.api_ejecutar_comando, name='ejecutar_comando'),

    # --- Exportación ---
    path('exportar-csv/', views.api_exportar_csv, name='exportar_csv'),
    path('exportar-geojson/', views.api_exportar_geojson, name='exportar_geojson'),
]