from django.urls import path
from . import views

urlpatterns = [
    path('', views.mapa_publico, name='mapa_publico'),
    path('reporte/', views.reporte_ciudadano_view, name='reporte_ciudadano'),
]