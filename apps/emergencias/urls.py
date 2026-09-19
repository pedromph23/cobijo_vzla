from django.urls import path
from . import views

urlpatterns = [
    path('api/eventos-activos/', views.api_eventos_activos, name='api_eventos_activos'),
    path('api/reportes-recientes/', views.api_reportes_recientes, name='api_reportes_recientes'),
    path('api/kpis/', views.api_emergencias_kpis, name='api_kpis'),
]