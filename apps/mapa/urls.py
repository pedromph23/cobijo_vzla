from django.urls import path
from . import views

urlpatterns = [
    path('', views.panel_control, name='panel_control'),
    path('carga-datos/', views.carga_datos, name='carga_datos'),
    path('resultados/', views.resultados_view, name='resultados'),
]