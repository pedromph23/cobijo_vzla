"""
Vistas CRUD genéricas para el panel de gestión.

Cada vista verifica permisos con `permissions.py` antes de ejecutar.
"""
import logging

from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.db.models import Q
from django.forms import modelform_factory
from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse
from django.views.generic import View

from ..permissions import (
    MODELOS_CRUD,
    get_config,
    get_modelo_class,
    modelos_disponibles,
    obtener_permisos_usuario,
    tiene_permiso,
)


logger = logging.getLogger(__name__)


# ============================================================
# HELPERS
# ============================================================

def _contexto_base(request, modelo_key: str, config: dict) -> dict:
    """Contexto común a todas las vistas CRUD."""
    return {
        'modelo_key': modelo_key,
        'config': config,
        'verbose_name': config['verbose_name'],
        'verbose_name_plural': config['verbose_name_plural'],
        'menu_modelos': modelos_disponibles(request.user),
        'acciones': obtener_permisos_usuario(request.user).get(modelo_key, []),
    }


def _construir_form_class(config: dict):
    """Crea un ModelForm dinámico para el modelo dado."""
    Model = get_modelo_class(
        f"{config['app_label']}_{config['model_name'].lower()}"
    )
    # Para simplificar, exponemos todos los campos editables del modelo
    return modelform_factory(Model, fields='__all__')


# ============================================================
# CRUD - LISTA
# ============================================================

class CrudListView(View):
    """Lista los objetos de un modelo con búsqueda y paginación."""

    def get(self, request, modelo_key):
        config = get_config(modelo_key)
        if not config:
            raise PermissionDenied("Modelo no encontrado.")

        if not tiene_permiso(request.user, modelo_key, 'ver'):
            raise PermissionDenied("No tienes permiso para ver este modelo.")

        Model = get_modelo_class(modelo_key)
        qs = Model.objects.all()

        # Búsqueda
        q = request.GET.get('q', '').strip()
        if q:
            filtro = Q()
            for campo in config.get('search_fields', []):
                filtro |= Q(**{f'{campo}__icontains': q})
            qs = qs.filter(filtro)

        # Orden
        orden = config.get('ordering', ['-pk'])
        qs = qs.order_by(*orden)

        # Paginación simple (25 por página)
        from django.core.paginator import Paginator
        paginator = Paginator(qs, 25)
        page = paginator.get_page(request.GET.get('page', 1))

        return render(request, 'mapa/crud/crud_list.html', {
            **_contexto_base(request, modelo_key, config),
            'page_obj': page,
            'query': q,
            'list_display': config.get('list_display', ['pk']),
        })


# ============================================================
# CRUD - CREAR
# ============================================================

class CrudCreateView(View):
    """Formulario para crear un objeto nuevo."""

    def get(self, request, modelo_key):
        config = get_config(modelo_key)
        if not config:
            raise PermissionDenied("Modelo no encontrado.")
        if not tiene_permiso(request.user, modelo_key, 'crear'):
            raise PermissionDenied("No tienes permiso para crear este modelo.")

        FormClass = _construir_form_class(config)
        return render(request, 'mapa/crud/crud_form.html', {
            **_contexto_base(request, modelo_key, config),
            'form': FormClass(),
            'modo': 'crear',
        })

    def post(self, request, modelo_key):
        config = get_config(modelo_key)
        if not config:
            raise PermissionDenied("Modelo no encontrado.")
        if not tiene_permiso(request.user, modelo_key, 'crear'):
            raise PermissionDenied("No tienes permiso para crear este modelo.")

        FormClass = _construir_form_class(config)
        form = FormClass(request.POST, request.FILES)

        if form.is_valid():
            obj = form.save()
            messages.success(
                request,
                f"{config['verbose_name']} creado correctamente."
            )
            return redirect('crud_list', modelo_key=modelo_key)

        return render(request, 'mapa/crud/crud_form.html', {
            **_contexto_base(request, modelo_key, config),
            'form': form,
            'modo': 'crear',
        })


# ============================================================
# CRUD - EDITAR
# ============================================================

class CrudUpdateView(View):
    """Formulario para editar un objeto existente."""

    def get(self, request, modelo_key, pk):
        config = get_config(modelo_key)
        if not config:
            raise PermissionDenied("Modelo no encontrado.")
        if not tiene_permiso(request.user, modelo_key, 'editar'):
            raise PermissionDenied("No tienes permiso para editar.")

        Model = get_modelo_class(modelo_key)
        obj = get_object_or_404(Model, pk=pk)

        FormClass = _construir_form_class(config)
        return render(request, 'mapa/crud/crud_form.html', {
            **_contexto_base(request, modelo_key, config),
            'form': FormClass(instance=obj),
            'objeto': obj,
            'modo': 'editar',
        })

    def post(self, request, modelo_key, pk):
        config = get_config(modelo_key)
        if not config:
            raise PermissionDenied("Modelo no encontrado.")
        if not tiene_permiso(request.user, modelo_key, 'editar'):
            raise PermissionDenied("No tienes permiso para editar.")

        Model = get_modelo_class(modelo_key)
        obj = get_object_or_404(Model, pk=pk)

        FormClass = _construir_form_class(config)
        form = FormClass(request.POST, request.FILES, instance=obj)

        if form.is_valid():
            form.save()
            messages.success(
                request,
                f"{config['verbose_name']} actualizado correctamente."
            )
            return redirect('crud_list', modelo_key=modelo_key)

        return render(request, 'mapa/crud/crud_form.html', {
            **_contexto_base(request, modelo_key, config),
            'form': form,
            'objeto': obj,
            'modo': 'editar',
        })


# ============================================================
# CRUD - BORRAR
# ============================================================

class CrudDeleteView(View):
    """Confirmación y borrado de un objeto."""

    def get(self, request, modelo_key, pk):
        config = get_config(modelo_key)
        if not config:
            raise PermissionDenied("Modelo no encontrado.")
        if not tiene_permiso(request.user, modelo_key, 'borrar'):
            raise PermissionDenied("No tienes permiso para borrar.")

        Model = get_modelo_class(modelo_key)
        obj = get_object_or_404(Model, pk=pk)

        return render(request, 'mapa/crud/crud_confirm_delete.html', {
            **_contexto_base(request, modelo_key, config),
            'objeto': obj,
        })

    def post(self, request, modelo_key, pk):
        config = get_config(modelo_key)
        if not config:
            raise PermissionDenied("Modelo no encontrado.")
        if not tiene_permiso(request.user, modelo_key, 'borrar'):
            raise PermissionDenied("No tienes permiso para borrar.")

        Model = get_modelo_class(modelo_key)
        obj = get_object_or_404(Model, pk=pk)
        nombre = str(obj)

        try:
            obj.delete()
            messages.success(
                request,
                f"{config['verbose_name']} «{nombre}» eliminado."
            )
        except Exception as e:
            logger.error(f"Error al borrar {modelo_key}/{pk}: {e}", exc_info=True)
            messages.error(request, f"No se pudo eliminar: {e}")

        return redirect('crud_list', modelo_key=modelo_key)