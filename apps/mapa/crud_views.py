"""
Vistas CRUD genericas para el panel.
"""
import logging
from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.db.models import Q
from django.forms import modelform_factory
from django.shortcuts import render, get_object_or_404, redirect
from django.views.generic import View
from .permissions import (
    get_config, get_modelo_class, modelos_disponibles,
    obtener_permisos_usuario, tiene_permiso,
)

logger = logging.getLogger(__name__)


def _contexto_base(request, modelo_key, config):
    return {
        'modelo_key': modelo_key,
        'config': config,
        'verbose_name': config['verbose_name'],
        'verbose_name_plural': config['verbose_name_plural'],
        'menu_modelos': modelos_disponibles(request.user),
        'acciones': obtener_permisos_usuario(request.user).get(modelo_key, []),
    }


def _form_class(modelo_key):
    config = get_config(modelo_key)
    Model = get_modelo_class(modelo_key)
    return modelform_factory(Model, fields='__all__')


class CrudListView(View):
    def get(self, request, modelo_key):
        config = get_config(modelo_key)
        if not config:
            raise PermissionDenied("Modelo no encontrado.")
        if not tiene_permiso(request.user, modelo_key, 'ver'):
            raise PermissionDenied("Sin permiso para ver este modelo.")

        Model = get_modelo_class(modelo_key)
        qs = Model.objects.all()

        q = request.GET.get('q', '').strip()
        if q:
            filtro = Q()
            for campo in config.get('search_fields', []):
                filtro |= Q(**{f'{campo}__icontains': q})
            qs = qs.filter(filtro)

        qs = qs.order_by(*config.get('ordering', ['-pk']))
        page = Paginator(qs, 25).get_page(request.GET.get('page', 1))

        return render(request, 'mapa/crud/crud_list.html', {
            **_contexto_base(request, modelo_key, config),
            'page_obj': page,
            'query': q,
            'list_display': config.get('list_display', ['pk']),
        })


class CrudCreateView(View):
    def get(self, request, modelo_key):
        config = get_config(modelo_key)
        if not config:
            raise PermissionDenied("Modelo no encontrado.")
        if not tiene_permiso(request.user, modelo_key, 'crear'):
            raise PermissionDenied("Sin permiso para crear.")
        FormClass = _form_class(modelo_key)
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
            raise PermissionDenied("Sin permiso para crear.")
        FormClass = _form_class(modelo_key)
        form = FormClass(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            messages.success(request, f"{config['verbose_name']} creado.")
            return redirect('crud_list', modelo_key=modelo_key)
        return render(request, 'mapa/crud/crud_form.html', {
            **_contexto_base(request, modelo_key, config),
            'form': form, 'modo': 'crear',
        })


class CrudUpdateView(View):
    def get(self, request, modelo_key, pk):
        config = get_config(modelo_key)
        if not config:
            raise PermissionDenied("Modelo no encontrado.")
        if not tiene_permiso(request.user, modelo_key, 'editar'):
            raise PermissionDenied("Sin permiso para editar.")
        Model = get_modelo_class(modelo_key)
        obj = get_object_or_404(Model, pk=pk)
        FormClass = _form_class(modelo_key)
        return render(request, 'mapa/crud/crud_form.html', {
            **_contexto_base(request, modelo_key, config),
            'form': FormClass(instance=obj),
            'objeto': obj, 'modo': 'editar',
        })

    def post(self, request, modelo_key, pk):
        config = get_config(modelo_key)
        if not config:
            raise PermissionDenied("Modelo no encontrado.")
        if not tiene_permiso(request.user, modelo_key, 'editar'):
            raise PermissionDenied("Sin permiso para editar.")
        Model = get_modelo_class(modelo_key)
        obj = get_object_or_404(Model, pk=pk)
        FormClass = _form_class(modelo_key)
        form = FormClass(request.POST, request.FILES, instance=obj)
        if form.is_valid():
            form.save()
            messages.success(request, f"{config['verbose_name']} actualizado.")
            return redirect('crud_list', modelo_key=modelo_key)
        return render(request, 'mapa/crud/crud_form.html', {
            **_contexto_base(request, modelo_key, config),
            'form': form, 'objeto': obj, 'modo': 'editar',
        })


class CrudDeleteView(View):
    def get(self, request, modelo_key, pk):
        config = get_config(modelo_key)
        if not config:
            raise PermissionDenied("Modelo no encontrado.")
        if not tiene_permiso(request.user, modelo_key, 'borrar'):
            raise PermissionDenied("Sin permiso para borrar.")
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
            raise PermissionDenied("Sin permiso para borrar.")
        Model = get_modelo_class(modelo_key)
        obj = get_object_or_404(Model, pk=pk)
        nombre = str(obj)
        try:
            obj.delete()
            messages.success(request, f"{config['verbose_name']} «{nombre}» eliminado.")
        except Exception as e:
            logger.error(f"Error al borrar: {e}", exc_info=True)
            messages.error(request, f"No se pudo eliminar: {e}")
        return redirect('crud_list', modelo_key=modelo_key)
