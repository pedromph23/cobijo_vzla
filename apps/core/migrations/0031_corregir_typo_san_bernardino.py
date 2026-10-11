"""
Corrige el typo 'San Bernandino' -> 'San Bernardino' (falta la 'r').

La parroquia id=15 pertenece al Municipio Libertador, Distrito Capital.
Es la única instancia con ese typo en la BD.

Idempotente: si el nombre ya está correcto, no hace nada.
Reversible: revierte al nombre antiguo.
"""
from django.db import migrations


VIEJO = 'San Bernandino'
NUEVO = 'San Bernardino'
PARROQUIA_ID = 15


def corregir(apps, schema_editor):
    Parroquia = apps.get_model('core', 'Parroquia')

    try:
        p = Parroquia.objects.get(id=PARROQUIA_ID)
    except Parroquia.DoesNotExist:
        print(f'[0031] Parroquia id={PARROQUIA_ID} no existe. Nada que hacer.')
        return

    if p.nombre == NUEVO:
        print(f'[0031] Parroquia id={PARROQUIA_ID} ya está corregida.')
        return

    if p.nombre != VIEJO:
        raise ValueError(
            f'La parroquia id={PARROQUIA_ID} se llama {p.nombre!r}, '
            f'se esperaba {VIEJO!r}. Abortando por seguridad.'
        )

    p.nombre = NUEVO
    p.save(update_fields=['nombre'])
    print(f'[0031] Parroquia id={PARROQUIA_ID}: {VIEJO!r} -> {NUEVO!r}')


def revertir(apps, schema_editor):
    Parroquia = apps.get_model('core', 'Parroquia')

    try:
        p = Parroquia.objects.get(id=PARROQUIA_ID)
    except Parroquia.DoesNotExist:
        return

    if p.nombre == VIEJO:
        return

    p.nombre = VIEJO
    p.save(update_fields=['nombre'])
    print(f'[0031 revert] Parroquia id={PARROQUIA_ID}: {NUEVO!r} -> {VIEJO!r}')


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0030_fix_registroversion_modelo_simulacion'),
    ]

    operations = [
        migrations.RunPython(corregir, revertir),
    ]
