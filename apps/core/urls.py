from django.urls import path
from . import views

urlpatterns = [
    path('api/kpis/', views.api_kpis, name='api_kpis'),
    path('api/refugios-criticos/', views.api_refugios_criticos, name='api_refugios_criticos'),
]