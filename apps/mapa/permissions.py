"""
Sistema de permisos para el CRUD del panel.
"""
from typing import Dict, List, Optional
from django.apps import apps


MODELOS_CRUD: Dict[str, Dict] = {
    'core_estado': {
        'app_label': 'core', 'model_name': 'Estado',
        'verbose_name': 'Estado', 'verbose_name_plural': 'Estados',
        'icon': 'fa-flag',
        'list_display': ['nombre', 'codigo_ine'],
        'search_fields': ['nombre', 'codigo_ine'],
        'ordering': ['nombre'],
    },
    'core_parroquia': {
        'app_label': 'core', 'model_name': 'Parroquia',
        'verbose_name': 'Parroquia', 'verbose_name_plural': 'Parroquias',
        'icon': 'fa-map',
        'list_display': ['nombre', 'estado', 'poblacion'],
        'search_fields': ['nombre', 'codigo_ine'],
        'ordering': ['estado__nombre', 'nombre'],
    },
    'core_puntodemanda': {
        'app_label': 'core', 'model_name': 'PuntoDemanda',
        'verbose_name': 'Punto de demanda', 'verbose_name_plural': 'Puntos de demanda',
        'icon': 'fa-users',
        'list_display': ['nombre', 'parroquia', 'poblacion', 'vulnerabilidad'],
        'search_fields': ['nombre', 'descripcion'],
        'ordering': ['nombre'],
    },
    'core_sitiocandidato': {
        'app_label': 'core', 'model_name': 'SitioCandidato',
        'verbose_name': 'Sitio candidato', 'verbose_name_plural': 'Sitios candidatos',
        'icon': 'fa-building',
        'list_display': ['nombre', 'capacidad_maxima', 'disponible'],
        'search_fields': ['nombre', 'tipo_terreno'],
        'ordering': ['nombre'],
    },
    'core_refugioexistente': {
        'app_label': 'core', 'model_name': 'RefugioExistente',
        'verbose_name': 'Refugio existente', 'verbose_name_plural': 'Refugios existentes',
        'icon': 'fa-home',
        'list_display': ['nombre', 'direccion', 'capacidad_total', 'operativo'],
        'search_fields': ['nombre', 'direccion', 'telefono'],
        'ordering': ['nombre'],
    },
    'core_zonaafectada': {
        'app_label': 'core', 'model_name': 'ZonaAfectada',
        'verbose_name': 'Zona afectada', 'verbose_name_plural': 'Zonas afectadas',
        'icon': 'fa-exclamation-triangle',
        'list_display': ['nombre', 'nivel_alerta', 'heridos', 'damnificados'],
        'search_fields': ['nombre', 'descripcion'],
        'ordering': ['-fecha_inicio'],
    },
    'core_parametrosmodelo': {
        'app_label': 'core', 'model_name': 'ParametrosModelo',
        'verbose_name': 'Parametro', 'verbose_name_plural': 'Parametros',
        'icon': 'fa-cog',
        'list_display': ['nombre_escenario', 'tipo_modelo', 'p'],
        'search_fields': ['nombre_escenario'],
        'ordering': ['-fecha_creacion'],
    },
    'emergencias_evento': {
        'app_label': 'emergencias', 'model_name': 'Evento',
        'verbose_name': 'Evento', 'verbose_name_plural': 'Eventos',
        'icon': 'fa-bolt',
        'list_display': ['nombre', 'tipo', 'fecha', 'activo'],
        'search_fields': ['nombre', 'descripcion'],
        'ordering': ['-fecha'],
    },
    'emergencias_reporte': {
        'app_label': 'emergencias', 'model_name': 'Reporte',
        'verbose_name': 'Reporte', 'verbose_name_plural': 'Reportes',
        'icon': 'fa-comment-dots',
        'list_display': ['id', 'autor', 'fecha', 'verificado'],
        'search_fields': ['autor', 'texto'],
        'ordering': ['-fecha'],
    },
}

PERMISOS_POR_GRUPO: Dict[str, Dict[str, List[str]]] = {
    'Administradores': {
        k: ['ver', 'crear', 'editar', 'borrar'] for k in MODELOS_CRUD.keys()
    },
    'Gestores': {
        'core_puntodemanda': ['ver', 'crear', 'editar'],
        'core_refugioexistente': ['ver', 'editar'],
        'core_zonaafectada': ['ver', 'editar'],
        'core_sitiocandidato': ['ver'],
        'core_parametrosmodelo': ['ver'],
        'emergencias_evento': ['ver', 'editar'],
        'emergencias_reporte': ['ver', 'editar'],
    },
}


def obtener_permisos_usuario(user) -> Dict[str, List[str]]:
    if not user or not user.is_authenticated:
        return {}
    if user.is_superuser or user.is_staff:
        return {k: ['ver', 'crear', 'editar', 'borrar'] for k in MODELOS_CRUD}
    permisos = {}
    for nombre in user.groups.values_list('name', flat=True):
        for mk, acciones in PERMISOS_POR_GRUPO.get(nombre, {}).items():
            s = set(permisos.get(mk, [])) | set(acciones)
            permisos[mk] = sorted(s)
    return permisos


def tiene_permiso(user, modelo_key: str, accion: str) -> bool:
    if modelo_key not in MODELOS_CRUD or accion not in ('ver', 'crear', 'editar', 'borrar'):
        return False
    return accion in obtener_permisos_usuario(user).get(modelo_key, [])


def modelos_disponibles(user) -> List[Dict]:
    permisos = obtener_permisos_usuario(user)
    out = []
    for key, cfg in MODELOS_CRUD.items():
        acciones = permisos.get(key, [])
        if 'ver' in acciones:
            out.append({
                'key': key,
                'app_label': cfg['app_label'],
                'model_name': cfg['model_name'],
                'verbose_name': cfg['verbose_name'],
                'verbose_name_plural': cfg['verbose_name_plural'],
                'icon': cfg.get('icon', 'fa-table'),
                'acciones': acciones,
            })
    return out


def get_modelo_class(modelo_key: str):
    if modelo_key not in MODELOS_CRUD:
        raise ValueError(f"Modelo no registrado: {modelo_key}")
    cfg = MODELOS_CRUD[modelo_key]
    return apps.get_model(cfg['app_label'], cfg['model_name'])


def get_config(modelo_key: str) -> Optional[Dict]:
    return MODELOS_CRUD.get(modelo_key)
