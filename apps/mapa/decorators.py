"""
Decoradores de permisos para el panel administrativo.

Centraliza la lógica de autorización para evitar duplicación entre vistas.
"""
from functools import wraps
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied


def es_gestor(user) -> bool:
    """
    Verifica si el usuario puede acceder al panel de gestión.

    Un usuario es gestor si:
    - Es superusuario, o
    - Es staff, o
    - Pertenece al grupo 'Gestores'
    """
    if not user or not user.is_authenticated:
        return False
    return (
        user.is_superuser
        or user.is_staff
        or user.groups.filter(name='Gestores').exists()
    )


def gestor_requerido(view_func):
    """
    Decorador que combina login_required + verificación de gestor.

    Uso:
        @gestor_requerido
        def mi_vista(request): ...
    """
    @wraps(view_func)
    @login_required
    def wrapper(request, *args, **kwargs):
        if not es_gestor(request.user):
            raise PermissionDenied(
                "Necesita permisos de gestor para acceder a esta sección."
            )
        return view_func(request, *args, **kwargs)
    return wrapper