from django.urls import path
from . import views

urlpatterns = [
    path('generar/', views.api_generar_reporte, name='generar_reporte'),
    path('descargar/<str:nombre_archivo>/', views.api_descargar_reporte, name='descargar_reporte'),
    path('exportar-csv/', views.api_exportar_csv, name='exportar_csv'),
    path('exportar-geojson/', views.api_exportar_geojson, name='exportar_geojson'),
]