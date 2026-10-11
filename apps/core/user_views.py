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

        # Prevenir auto-desactivación
        if user_obj == request.user and not user_obj.is_active:
            messages.warning(request, 'No puedes desactivar tu propia cuenta.')

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
        form = UserUpdateForm(request.POST, instance=user_obj)

        if form.is_valid():
            # Prevenir auto-desactivación
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
        return render(request, 'admin/users/user_confirm_delete.html', {
            'objeto': user_obj,
        })

    def post(self, request, pk):
        if not _es_admin(request.user):
            raise PermissionDenied('Solo administradores pueden gestionar usuarios.')

        user_obj = get_object_or_404(User, pk=pk)

        # Prevenir auto-desactivación
        if user_obj == request.user:
            messages.error(request, 'No puedes desactivar tu propia cuenta.')
            return redirect('user_list')

        # Prevenir desactivar al último superuser
        if user_obj.is_superuser and User.objects.filter(is_superuser=True).count() <= 1:
            messages.error(request, 'No puedes desactivar al último superusuario.')
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
        user_obj.is_active = True
        user_obj.save(update_fields=['is_active'])
        logger.info(f'Usuario reactivado: {user_obj.username} por {request.user.username}')
        messages.success(request, f'Usuario «{user_obj.username}» reactivado.')
        return redirect('user_list')
