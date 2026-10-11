"""
Actualiza los registros históricos en RegistroVersion que apuntan al
nombre antiguo 'apps.core.models.ParametrosModelo'.

Necesario porque RegistroVersion.modelo almacena la ruta completa del
modelo como string. Tras el rename del modelo, esos registros quedarían
huérfanos.

Idempotente y reversible.
"""
from django.db import migrations


VIEJO = 'apps.core.models.ParametrosModelo'
NUEVO = 'apps.core.models.Simulacion'


def actualizar(apps, schema_editor):
    RegistroVersion = apps.get_model('core', 'RegistroVersion')
    n = RegistroVersion.objects.filter(modelo=VIEJO).update(modelo=NUEVO)
    print(f'\n[0030] Registros históricos actualizados: {n}')


def revertir(apps, schema_editor):
    RegistroVersion = apps.get_model('core', 'RegistroVersion')
    n = RegistroVersion.objects.filter(modelo=NUEVO).update(modelo=VIEJO)
    print(f'\n[0030 revert] Registros revertidos: {n}')


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0029_rename_parametrosmodelo_simulacion'),
    ]

    operations = [
        migrations.RunPython(actualizar, revertir),
    ]
