"""
Vistas CRUD genéricas para el panel.

Incluye:
- Listado.
- Creación.
- Edición.
- Eliminación.
- Control de permisos.
- Auditoría de CREATE, UPDATE y DELETE.
"""

import logging

from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.db.models import Q
from django.forms import modelform_factory
from django.shortcuts import render, get_object_or_404, redirect
from django.views.generic import View

from apps.core.audit import (
    registrar_auditoria,
    serializar_instancia,
)

from .permissions import (
    get_config,
    get_modelo_class,
    modelos_disponibles,
    obtener_permisos_usuario,
    tiene_permiso,
)


logger = logging.getLogger(__name__)


# ============================================================
# CONTEXTO
# ============================================================

def _contexto_base(request, modelo_key, config):
    """
    Construye el contexto común utilizado por las vistas CRUD.
    """

    return {
        'modelo_key': modelo_key,
        'config': config,
        'verbose_name': config['verbose_name'],
        'verbose_name_plural': config['verbose_name_plural'],
        'menu_modelos': modelos_disponibles(request.user),
        'acciones': obtener_permisos_usuario(
            request.user
        ).get(modelo_key, []),
    }


# ============================================================
# FORMULARIOS
# ============================================================

def _form_class(modelo_key):
    """
    Construye dinámicamente el ModelForm correspondiente
    al modelo configurado.
    """

    Model = get_modelo_class(modelo_key)

    return modelform_factory(
        Model,
        fields='__all__',
    )


# ============================================================
# AUDITORÍA
# ============================================================

def _registrar_auditoria_segura(
    request,
    *,
    accion,
    objeto=None,
    datos_anteriores=None,
    datos_nuevos=None,
    descripcion='',
    resultado='exitoso',
    modelo='',
    objeto_id='',
    objeto_repr='',
):
    """
    Registra una auditoría sin permitir que un fallo del sistema
    de auditoría interrumpa la operación CRUD.

    Esta función es deliberadamente defensiva porque la auditoría
    nunca debe impedir una operación válida del sistema.
    """

    try:
        return registrar_auditoria(
            request=request,
            accion=accion,
            objeto=objeto,
            datos_anteriores=datos_anteriores,
            datos_nuevos=datos_nuevos,
            descripcion=descripcion,
            resultado=resultado,
            modelo=modelo,
            objeto_id=objeto_id,
            objeto_repr=objeto_repr,
            usuario=(
                request.user
                if request is not None
                and getattr(
                    request.user,
                    'is_authenticated',
                    False,
                )
                else None
            ),
        )

    except Exception:
        logger.exception(
            "No se pudo registrar la auditoría CRUD: %s",
            accion,
        )

        return None


# ============================================================
# LISTADO
# ============================================================

class CrudListView(View):
    """
    Listado genérico de cualquier modelo configurado en
    MODELOS_CRUD.
    """

    def get(self, request, modelo_key):
        config = get_config(modelo_key)

        if not config:
            raise PermissionDenied(
                "Modelo no encontrado."
            )

        if not tiene_permiso(
            request.user,
            modelo_key,
            'ver',
        ):
            raise PermissionDenied(
                "Sin permiso para ver este modelo."
            )

        Model = get_modelo_class(modelo_key)

        qs = Model.objects.all()

        q = request.GET.get(
            'q',
            '',
        ).strip()

        if q:
            filtro = Q()

            for campo in config.get(
                'search_fields',
                [],
            ):
                filtro |= Q(
                    **{
                        f'{campo}__icontains': q
                    }
                )

            qs = qs.filter(filtro)

        qs = qs.order_by(
            *config.get(
                'ordering',
                ['-pk'],
            )
        )

        page = Paginator(
            qs,
            25,
        ).get_page(
            request.GET.get(
                'page',
                1,
            )
        )

        return render(
            request,
            'mapa/crud/crud_list.html',
            {
                **_contexto_base(
                    request,
                    modelo_key,
                    config,
                ),
                'page_obj': page,
                'query': q,
                'list_display': config.get(
                    'list_display',
                    ['pk'],
                ),
            },
        )


# ============================================================
# CREAR
# ============================================================

class CrudCreateView(View):
    """
    Creación genérica de registros.
    """

    def get(self, request, modelo_key):
        config = get_config(modelo_key)

        if not config:
            raise PermissionDenied(
                "Modelo no encontrado."
            )

        if not tiene_permiso(
            request.user,
            modelo_key,
            'crear',
        ):
            raise PermissionDenied(
                "Sin permiso para crear."
            )

        FormClass = _form_class(modelo_key)

        return render(
            request,
            'mapa/crud/crud_form.html',
            {
                **_contexto_base(
                    request,
                    modelo_key,
                    config,
                ),
                'form': FormClass(),
                'modo': 'crear',
            },
        )

    def post(self, request, modelo_key):
        config = get_config(modelo_key)

        if not config:
            raise PermissionDenied(
                "Modelo no encontrado."
            )

        if not tiene_permiso(
            request.user,
            modelo_key,
            'crear',
        ):
            raise PermissionDenied(
                "Sin permiso para crear."
            )

        FormClass = _form_class(modelo_key)

        form = FormClass(
            request.POST,
            request.FILES,
        )

        if form.is_valid():

            try:
                # ------------------------------------------------
                # GUARDAR
                # ------------------------------------------------
                obj = form.save()

                # ------------------------------------------------
                # SERIALIZAR ESTADO NUEVO
                # ------------------------------------------------
                datos_nuevos = serializar_instancia(
                    obj
                )

                # ------------------------------------------------
                # AUDITORÍA CREATE
                # ------------------------------------------------
                _registrar_auditoria_segura(
                    request,
                    accion='CREATE',
                    objeto=obj,
                    datos_nuevos=datos_nuevos,
                    descripcion=(
                        f"{config['verbose_name']} creado."
                    ),
                    resultado='exitoso',
                )

                messages.success(
                    request,
                    (
                        f"{config['verbose_name']} "
                        f"creado."
                    ),
                )

                return redirect(
                    'crud_list',
                    modelo_key=modelo_key,
                )

            except Exception as exc:
                logger.exception(
                    "Error al crear %s",
                    modelo_key,
                )

                messages.error(
                    request,
                    (
                        f"No se pudo crear "
                        f"{config['verbose_name']}: "
                        f"{exc}"
                    ),
                )

        return render(
            request,
            'mapa/crud/crud_form.html',
            {
                **_contexto_base(
                    request,
                    modelo_key,
                    config,
                ),
                'form': form,
                'modo': 'crear',
            },
        )


# ============================================================
# EDITAR
# ============================================================

class CrudUpdateView(View):
    """
    Edición genérica de registros.

    La auditoría conserva:
    - estado anterior;
    - estado nuevo.
    """

    def get(self, request, modelo_key, pk):
        config = get_config(modelo_key)

        if not config:
            raise PermissionDenied(
                "Modelo no encontrado."
            )

        if not tiene_permiso(
            request.user,
            modelo_key,
            'editar',
        ):
            raise PermissionDenied(
                "Sin permiso para editar."
            )

        Model = get_modelo_class(modelo_key)

        obj = get_object_or_404(
            Model,
            pk=pk,
        )

        FormClass = _form_class(modelo_key)

        return render(
            request,
            'mapa/crud/crud_form.html',
            {
                **_contexto_base(
                    request,
                    modelo_key,
                    config,
                ),
                'form': FormClass(
                    instance=obj
                ),
                'objeto': obj,
                'modo': 'editar',
            },
        )

    def post(self, request, modelo_key, pk):
        config = get_config(modelo_key)

        if not config:
            raise PermissionDenied(
                "Modelo no encontrado."
            )

        if not tiene_permiso(
            request.user,
            modelo_key,
            'editar',
        ):
            raise PermissionDenied(
                "Sin permiso para editar."
            )

        Model = get_modelo_class(modelo_key)

        obj = get_object_or_404(
            Model,
            pk=pk,
        )

        # --------------------------------------------------------
        # FOTOGRAFÍA ANTERIOR
        # --------------------------------------------------------

        datos_anteriores = serializar_instancia(
            obj
        )

        FormClass = _form_class(modelo_key)

        form = FormClass(
            request.POST,
            request.FILES,
            instance=obj,
        )

        if form.is_valid():

            try:
                # ------------------------------------------------
                # GUARDAR CAMBIOS
                # ------------------------------------------------
                obj = form.save()

                # ------------------------------------------------
                # FOTOGRAFÍA NUEVA
                # ------------------------------------------------
                datos_nuevos = serializar_instancia(
                    obj
                )

                # ------------------------------------------------
                # AUDITORÍA UPDATE
                # ------------------------------------------------
                _registrar_auditoria_segura(
                    request,
                    accion='UPDATE',
                    objeto=obj,
                    datos_anteriores=datos_anteriores,
                    datos_nuevos=datos_nuevos,
                    descripcion=(
                        f"{config['verbose_name']} "
                        f"actualizado."
                    ),
                    resultado='exitoso',
                )

                messages.success(
                    request,
                    (
                        f"{config['verbose_name']} "
                        f"actualizado."
                    ),
                )

                return redirect(
                    'crud_list',
                    modelo_key=modelo_key,
                )

            except Exception as exc:
                logger.exception(
                    "Error al actualizar %s",
                    modelo_key,
                )

                messages.error(
                    request,
                    (
                        f"No se pudo actualizar "
                        f"{config['verbose_name']}: "
                        f"{exc}"
                    ),
                )

        return render(
            request,
            'mapa/crud/crud_form.html',
            {
                **_contexto_base(
                    request,
                    modelo_key,
                    config,
                ),
                'form': form,
                'objeto': obj,
                'modo': 'editar',
            },
        )


# ============================================================
# ELIMINAR
# ============================================================

class CrudDeleteView(View):
    """
    Eliminación genérica.

    IMPORTANTE:
    La auditoría DELETE se registra ANTES de eliminar
    el objeto porque después de obj.delete() ya no podemos
    depender de la instancia para reconstruir sus datos.
    """

    def get(self, request, modelo_key, pk):
        config = get_config(modelo_key)

        if not config:
            raise PermissionDenied(
                "Modelo no encontrado."
            )

        if not tiene_permiso(
            request.user,
            modelo_key,
            'borrar',
        ):
            raise PermissionDenied(
                "Sin permiso para borrar."
            )

        Model = get_modelo_class(modelo_key)

        obj = get_object_or_404(
            Model,
            pk=pk,
        )

        return render(
            request,
            'mapa/crud/crud_confirm_delete.html',
            {
                **_contexto_base(
                    request,
                    modelo_key,
                    config,
                ),
                'objeto': obj,
            },
        )

    def post(self, request, modelo_key, pk):
        config = get_config(modelo_key)

        if not config:
            raise PermissionDenied(
                "Modelo no encontrado."
            )

        if not tiene_permiso(
            request.user,
            modelo_key,
            'borrar',
        ):
            raise PermissionDenied(
                "Sin permiso para borrar."
            )

        Model = get_modelo_class(modelo_key)

        obj = get_object_or_404(
            Model,
            pk=pk,
        )

        # --------------------------------------------------------
        # GUARDAR INFORMACIÓN ANTES DE BORRAR
        # --------------------------------------------------------

        nombre = str(obj)

        objeto_id = str(
            obj.pk
        )

        modelo = obj._meta.label_lower

        datos_anteriores = serializar_instancia(
            obj
        )

        objeto_repr = str(obj)[:255]

        try:
            # ----------------------------------------------------
            # ELIMINAR OBJETO
            # ----------------------------------------------------

            obj.delete()

            # ----------------------------------------------------
            # AUDITORÍA DELETE
            #
            # No pasamos "objeto=obj" porque el objeto ya fue
            # eliminado. Utilizamos explícitamente los datos
            # capturados antes del DELETE.
            # ----------------------------------------------------

            _registrar_auditoria_segura(
                request,
                accion='DELETE',
                objeto=None,
                datos_anteriores=datos_anteriores,
                datos_nuevos=None,
                descripcion=(
                    f"{config['verbose_name']} "
                    f"eliminado."
                ),
                resultado='exitoso',
                modelo=modelo,
                objeto_id=objeto_id,
                objeto_repr=objeto_repr,
            )

            messages.success(
                request,
                (
                    f"{config['verbose_name']} "
                    f"«{nombre}» eliminado."
                ),
            )

        except Exception as exc:
            logger.exception(
                "Error al borrar %s",
                modelo_key,
            )

            # ----------------------------------------------------
            # Si la eliminación falló, registramos el fallo.
            # ----------------------------------------------------

            _registrar_auditoria_segura(
                request,
                accion='DELETE',
                objeto=None,
                datos_anteriores=datos_anteriores,
                datos_nuevos=None,
                descripcion=(
                    f"Error al eliminar "
                    f"{config['verbose_name']}."
                ),
                resultado='fallido',
                modelo=modelo,
                objeto_id=objeto_id,
                objeto_repr=objeto_repr,
            )

            messages.error(
                request,
                (
                    f"No se pudo eliminar "
                    f"{config['verbose_name']}: "
                    f"{exc}"
                ),
            )

        return redirect(
            'crud_list',
            modelo_key=modelo_key,
        )