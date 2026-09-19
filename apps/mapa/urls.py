from django.urls import path, include
from . import views

urlpatterns = [
    path('', views.panel_control, name='panel_control'),
    path('admin/', views.panel_admin, name='panel_admin'),
    path('gestor/', views.panel_gestor, name='panel_gestor'),
    path('carga-datos/', views.carga_datos, name='carga_datos'),
    path('resultados/', views.resultados_view, name='resultados'),
    path('datos/', include('apps.mapa.urls_crud')),   # ← NUEVO
]