"""
Elimina la parroquia 'Inmaculada Concepción' (id=1271).

Contexto:
Esta parroquia fue cargada en la BD sin geometría y no existe en el
dataset oficial del .gdb (capa ven_admin3). Parece ser una parroquia
eclesiástica confundida con parroquia civil.

Verificaciones previas:
- Sin geometría.
- Sin historial en RegistroVersion.
- Cero referencias desde PuntoDemanda, SitioCandidato, RefugioExistente
  y ZonaAfectada.
- No aparece en el .gdb oficial.

Consecuencia:
Parroquia.objects.count() pasa de 1122 a 1121, coincidiendo exactamente
con el dataset del .gdb.
"""
from django.db import migrations


PARROQUIA_ID = 1271
NOMBRE = 'Inmaculada Concepción'


def eliminar(apps, schema_editor):
    Parroquia = apps.get_model('core', 'Parroquia')
    RegistroVersion = apps.get_model('core', 'RegistroVersion')

    try:
        p = Parroquia.objects.get(id=PARROQUIA_ID)
    except Parroquia.DoesNotExist:
        print(f'[0026] Parroquia id={PARROQUIA_ID} ya no existe. Nada que hacer.')
        return

    if p.nombre != NOMBRE:
        raise ValueError(
            f'La parroquia id={PARROQUIA_ID} se llama {p.nombre!r}, '
            f'se esperaba {NOMBRE!r}. Abortando por seguridad.'
        )

    RegistroVersion.objects.create(
        modelo='core.parroquia',
        objeto_id=str(p.id),
        operacion='eliminado',
        datos={
            'id': p.id,
            'nombre': p.nombre,
            'estado_id': p.estado_id,
            'codigo_ine': p.codigo_ine,
            'poblacion': p.poblacion,
            'densidad_poblacional': p.densidad_poblacional,
            'indice_vulnerabilidad': p.indice_vulnerabilidad,
            'motivo': 'Parroquia huérfana sin geometría, no existe en el .gdb oficial.',
        },
        ruta='migration:0026_eliminar_parroquia_huerfana',
    )

    p.delete()
    print(f'[0026] Parroquia {NOMBRE!r} eliminada.')
    print(f'[0026] Total parroquias restantes: {Parroquia.objects.count()}')


def revertir(apps, schema_editor):
    """Revierte recreando la parroquia."""
    Parroquia = apps.get_model('core', 'Parroquia')
    Estado = apps.get_model('core', 'Estado')

    if Parroquia.objects.filter(id=PARROQUIA_ID).exists():
        return

    try:
        estado = Estado.objects.get(nombre='Distrito Capital')
    except Estado.DoesNotExist:
        print('[0026 revert] No se pudo revertir: Estado "Distrito Capital" no existe.')
        return

    Parroquia.objects.create(
        id=PARROQUIA_ID,
        nombre=NOMBRE,
        estado=estado,
        poblacion=0,
        densidad_poblacional=0.0,
        indice_vulnerabilidad=0.5,
    )
    print(f'[0026 revert] Parroquia {NOMBRE!r} recreada sin geometría.')


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0025_actualizar_geometrias_estados'),
    ]

    operations = [
        migrations.RunPython(eliminar, revertir),
    ]
