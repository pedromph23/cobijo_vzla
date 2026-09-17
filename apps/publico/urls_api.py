from django.urls import path
from . import views

urlpatterns = [
    path('refugios/', views.api_refugios_publicos, name='refugios_publicos'),
    path('zonas-afectadas/', views.api_zonas_afectadas, name='zonas_afectadas_publicas'),
    path('mapa-calor/', views.api_mapa_calor_publico, name='mapa_calor_publico'),
    path('buscar-lugar/', views.api_buscar_lugar, name='buscar_lugar'),
    path('reporte-ciudadano/', views.api_reporte_ciudadano, name='reporte_ciudadano_api'),
    path('info-emergencia/', views.api_info_emergencia, name='info_emergencia'),
]