"""
Decoradores de permisos para el panel administrativo.

Define 3 niveles de acceso:
- Superusuario: acceso total
- Administradores: gestión completa
- Gestores: uso operativo (sin configuración crítica)
"""
from functools import wraps
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied


# Grupos reconocidos por el sistema
GRUPO_ADMIN = 'Administradores'
GRUPO_GESTOR = 'Gestores'


# ============================================================
# HELPERS
# ============================================================

def _es_super(user) -> bool:
    return bool(user and user.is_authenticated and user.is_superuser)


def _es_staff(user) -> bool:
    return bool(user and user.is_authenticated and user.is_staff)


def _en_grupo(user, nombre: str) -> bool:
    if not user or not user.is_authenticated:
        return False
    return user.groups.filter(name=nombre).exists()


# ============================================================
# PERMISOS PÚBLICOS
# ============================================================

def es_administrador(user) -> bool:
    """
    Puede acceder al panel de administración completo.

    Criterios:
    - Superusuario, o
    - Staff, o
    - Pertenece al grupo 'Administradores'
    """
    if not user or not user.is_authenticated:
        return False
    return (
        user.is_superuser
        or user.is_staff
        or _en_grupo(user, GRUPO_ADMIN)
    )


def es_gestor(user) -> bool:
    """
    Puede acceder al panel operativo.

    Criterios:
    - Cumple con los criterios de administrador, O
    - Pertenece al grupo 'Gestores'
    """
    if not user or not user.is_authenticated:
        return False
    return es_administrador(user) or _en_grupo(user, GRUPO_GESTOR)


# ============================================================
# DECORADORES
# ============================================================

def admin_requerido(view_func):
    """
    Solo permite acceso a administradores (super/staff/grupo Administradores).
    """
    @wraps(view_func)
    @login_required
    def wrapper(request, *args, **kwargs):
        if not es_administrador(request.user):
            raise PermissionDenied(
                "Se requieren permisos de administrador para acceder."
            )
        return view_func(request, *args, **kwargs)
    return wrapper


def gestor_requerido(view_func):
    """
    Permite acceso a administradores y gestores.
    """
    @wraps(view_func)
    @login_required
    def wrapper(request, *args, **kwargs):
        if not es_gestor(request.user):
            raise PermissionDenied(
                "Necesita pertenecer al grupo Administradores o Gestores."
            )
        return view_func(request, *args, **kwargs)
    return wrapper