from django.urls import path
from . import views

urlpatterns = [
    # APIs de mapa
    path('datos-mapa/', views.api_datos_mapa, name='datos_mapa'),
    path('estadisticas/', views.api_estadisticas, name='estadisticas'),
    
    # APIs de optimización
    path('ejecutar-optimizacion/', views.api_ejecutar_optimizacion, name='ejecutar_optimizacion'),
    path('listar-resultados/', views.api_listar_resultados, name='listar_resultados'),
    path('resultados/<int:resultado_id>/', views.api_detalle_resultado, name='detalle_resultado'),
    
    # APIs de mapa de calor
    path('mapa-calor-admin/', views.api_mapa_calor, name='mapa_calor_admin'),
    
    # APIs de gestión
    path('ejecutar-comando/', views.api_ejecutar_comando, name='ejecutar_comando'),
    
    # APIs de exportación
    path('exportar-csv/', views.api_exportar_csv, name='exportar_csv'),
    path('exportar-geojson/', views.api_exportar_geojson, name='exportar_geojson'),
]