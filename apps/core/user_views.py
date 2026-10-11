"""Vistas de gestión de usuarios.

Solo accesibles para superusuarios, staff o miembros del grupo
'Administradores'. Permiten crear, listar, editar y desactivar usuarios.
"""
import logging

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.views.generic import View

from .dedup import similitud_nombres
from .user_forms import UserCreateForm, UserUpdateForm


logger = logging.getLogger(__name__)
User = get_user_model()


# ============================================================
# PERMISOS
# ============================================================

def _es_admin(user) -> bool:
    """Solo superuser, staff o grupo Administradores puede gestionar usuarios."""
    if not user or not user.is_authenticated:
        return False
    if user.is_superuser or user.is_staff:
        return True
    return user.groups.filter(name='Administradores').exists()


def _puede_gestionar(request_user, target_user) -> tuple[bool, str]:
    """Determina si request_user puede desactivar/reactivar a target_user.

    Reglas:
    - Nadie puede desactivarse a sí mismo.
    - Solo un superusuario puede modificar cuentas de superusuario.
    - Solo un superusuario puede modificar cuentas de staff.

    Returns:
        (puede, motivo) — motivo tiene el texto a mostrar si puede=False.
    """
    if not request_user or not request_user.is_authenticated:
        return False, 'Debes iniciar sesión.'

    if target_user == request_user:
        return False, 'No puedes desactivar ni borrar tu propia cuenta.'

    if target_user.is_superuser and not request_user.is_superuser:
        return False, 'Solo un superusuario puede modificar cuentas de superusuario.'

    if target_user.is_staff and not request_user.is_superuser:
        return False, 'Solo un superusuario puede modificar cuentas de staff.'

    return True, ''


def _puede_editar(request_user, target_user) -> tuple[bool, str]:
    """Similar a _puede_gestionar, pero permite auto-edición del perfil."""
    if not request_user or not request_user.is_authenticated:
        return False, 'Debes iniciar sesión.'

    if target_user == request_user:
        return True, ''

    if target_user.is_superuser and not request_user.is_superuser:
        return False, 'Solo un superusuario puede modificar cuentas de superusuario.'

    if target_user.is_staff and not request_user.is_superuser:
        return False, 'Solo un superusuario puede modificar cuentas de staff.'

    return True, ''


# ============================================================
# LISTADO
# ============================================================

class UserListView(View):
    """Listado paginado de usuarios con búsqueda."""

    def get(self, request):
        if not _es_admin(request.user):
            raise PermissionDenied('Solo administradores pueden gestionar usuarios.')

        qs = User.objects.all().prefetch_related('groups').order_by('username')

        q = (request.GET.get('q') or '').strip()
        if q:
            qs = qs.filter(
                Q(username__icontains=q) |
                Q(email__icontains=q) |
                Q(first_name__icontains=q) |
                Q(last_name__icontains=q)
            )

        grupo_filtro = request.GET.get('grupo')
        if grupo_filtro:
            qs = qs.filter(groups__name=grupo_filtro)

        page = Paginator(qs, 25).get_page(request.GET.get('page', 1))

        # Precalcular por usuario si el solicitante puede gestionarlo.
        for u in page:
            puede_edit, _ = _puede_editar(request.user, u)
            puede_gest, motivo = _puede_gestionar(request.user, u)
            u.puede_editar = puede_edit
            u.puede_gestionar = puede_gest
            u.motivo_bloqueo = motivo

        return render(request, 'admin/users/user_list.html', {
            'page_obj': page,
            'query': q,
            'grupo_filtro': grupo_filtro or '',
            'grupos': Group.objects.all().order_by('name'),
            'total': qs.count(),
        })


# ============================================================
# CREAR
# ============================================================

class UserCreateView(View):
    """Formulario de creación de usuario."""

    def get(self, request):
        if not _es_admin(request.user):
            raise PermissionDenied('Solo administradores pueden gestionar usuarios.')

        form = UserCreateForm()
        return render(request, 'admin/users/user_form.html', {
            'form': form,
            'modo': 'crear',
        })

    def post(self, request):
        if not _es_admin(request.user):
            raise PermissionDenied('Solo administradores pueden gestionar usuarios.')

        form = UserCreateForm(request.POST)
        if form.is_valid():
            user = form.save()
            logger.info(f'Usuario creado: {user.username} por {request.user.username}')
            messages.success(
                request,
                f'Usuario «{user.username}» creado correctamente. '
                f'Grupo: {user.groups.first().name if user.groups.exists() else "(sin grupo)"}.'
            )
            return redirect('user_list')

        return render(request, 'admin/users/user_form.html', {
            'form': form,
            'modo': 'crear',
        })


# ============================================================
# EDITAR
# ============================================================

class UserUpdateView(View):
    """Formulario de edición de usuario."""

    def get(self, request, pk):
        if not _es_admin(request.user):
            raise PermissionDenied('Solo administradores pueden gestionar usuarios.')

        user_obj = get_object_or_404(User, pk=pk)

        puede, motivo = _puede_editar(request.user, user_obj)
        if not puede:
            messages.error(request, motivo)
            return redirect('user_list')

        form = UserUpdateForm(instance=user_obj)
        return render(request, 'admin/users/user_form.html', {
            'form': form,
            'objeto': user_obj,
            'modo': 'editar',
        })

    def post(self, request, pk):
        if not _es_admin(request.user):
            raise PermissionDenied('Solo administradores pueden gestionar usuarios.')

        user_obj = get_object_or_404(User, pk=pk)

        puede, motivo = _puede_editar(request.user, user_obj)
        if not puede:
            messages.error(request, motivo)
            return redirect('user_list')

        form = UserUpdateForm(request.POST, instance=user_obj)

        if form.is_valid():
            # Prevenir auto-desactivación vía el formulario
            if user_obj == request.user and not form.cleaned_data.get('is_active'):
                messages.error(request, 'No puedes desactivar tu propia cuenta.')
                return render(request, 'admin/users/user_form.html', {
                    'form': form, 'objeto': user_obj, 'modo': 'editar',
                })

            user = form.save()
            logger.info(f'Usuario editado: {user.username} por {request.user.username}')
            messages.success(request, f'Usuario «{user.username}» actualizado.')
            return redirect('user_list')

        return render(request, 'admin/users/user_form.html', {
            'form': form,
            'objeto': user_obj,
            'modo': 'editar',
        })


# ============================================================
# DESACTIVAR / ELIMINAR
# ============================================================

class UserDeleteView(View):
    """Confirma desactivación de usuario (soft delete).

    No borra el usuario, solo lo desactiva (is_active=False).
    Esto preserva la trazabilidad de auditoría.
    """

    def get(self, request, pk):
        if not _es_admin(request.user):
            raise PermissionDenied('Solo administradores pueden gestionar usuarios.')

        user_obj = get_object_or_404(User, pk=pk)

        puede, motivo = _puede_gestionar(request.user, user_obj)
        if not puede:
            messages.error(request, motivo)
            return redirect('user_list')

        return render(request, 'admin/users/user_confirm_delete.html', {
            'objeto': user_obj,
        })

    def post(self, request, pk):
        if not _es_admin(request.user):
            raise PermissionDenied('Solo administradores pueden gestionar usuarios.')

        user_obj = get_object_or_404(User, pk=pk)

        puede, motivo = _puede_gestionar(request.user, user_obj)
        if not puede:
            messages.error(request, motivo)
            return redirect('user_list')

        user_obj.is_active = False
        user_obj.save(update_fields=['is_active'])
        logger.info(f'Usuario desactivado: {user_obj.username} por {request.user.username}')
        messages.success(request, f'Usuario «{user_obj.username}» desactivado.')
        return redirect('user_list')


# ============================================================
# REACTIVAR
# ============================================================

class UserReactivateView(View):
    """Reactiva un usuario previamente desactivado."""

    def post(self, request, pk):
        if not _es_admin(request.user):
            raise PermissionDenied('Solo administradores pueden gestionar usuarios.')

        user_obj = get_object_or_404(User, pk=pk)

        puede, motivo = _puede_gestionar(request.user, user_obj)
        if not puede:
            messages.error(request, motivo)
            return redirect('user_list')

        user_obj.is_active = True
        user_obj.save(update_fields=['is_active'])
        logger.info(f'Usuario reactivado: {user_obj.username} por {request.user.username}')
        messages.success(request, f'Usuario «{user_obj.username}» reactivado.')
        return redirect('user_list')
