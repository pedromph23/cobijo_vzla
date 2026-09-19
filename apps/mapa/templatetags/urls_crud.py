"""
Rutas del CRUD del panel.

Todas cuelgan de /panel/datos/...
"""
from django.urls import path
from . import crud_views

urlpatterns = [
    path(
        '<str:modelo_key>/',
        crud_views.CrudListView.as_view(),
        name='crud_list',
    ),
    path(
        '<str:modelo_key>/nuevo/',
        crud_views.CrudCreateView.as_view(),
        name='crud_create',
    ),
    path(
        '<str:modelo_key>/<int:pk>/editar/',
        crud_views.CrudUpdateView.as_view(),
        name='crud_update',
    ),
    path(
        '<str:modelo_key>/<int:pk>/borrar/',
        crud_views.CrudDeleteView.as_view(),
        name='crud_delete',
    ),
]