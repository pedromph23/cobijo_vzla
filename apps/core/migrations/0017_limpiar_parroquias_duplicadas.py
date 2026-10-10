"""
Limpia parroquias duplicadas detectadas por nombre normalizado + estado.

Contexto:
La BD tiene 149 pares duplicados de parroquias. Cada par tiene dos registros
idénticos salvo por la capitalización de preposiciones ("de", "la", "los").

Ejemplo:
  id=654  'Altagracia De La Montaña'   ← se queda
  id=1221 'Altagracia de la Montaña'   ← se elimina

Estrategia:
- Normalizar nombre (sin acentos, minúsculas, espacios normalizados).
- Agrupar por (estado_id, nombre_normalizado).
- Conservar el registro con ID MENOR.
- Guardar los datos del eliminado en RegistroVersion para trazabilidad.
- Eliminar el registro con ID MAYOR.

Verificado antes de aplicar:
- 149 grupos duplicados.
- Ambos registros tienen geometría.
- Poblaciones idénticas.
- Cero PuntoDemanda apuntan a parroquias duplicadas.
"""
from unicodedata import normalize, combining
from django.db import migrations


def _normalizar(s):
    s = ''.join(c for c in normalize('NFKD', s) if not combining(c))
    return ' '.join(s.lower().split())


def limpiar_duplicados(apps, schema_editor):
    Parroquia = apps.get_model('core', 'Parroquia')
    RegistroVersion = apps.get_model('core', 'RegistroVersion')

    # Agrupar por (estado_id, nombre_normalizado)
    grupos = {}
    for p in Parroquia.objects.all():
        key = (p.estado_id, _normalizar(p.nombre))
        grupos.setdefault(key, []).append(p)

    eliminados = 0
    for key, items in grupos.items():
        if len(items) <= 1:
            continue
        # Conservar ID menor
        items.sort(key=lambda x: x.id)
        superviviente = items[0]
        a_eliminar = items[1:]

        for p in a_eliminar:
            # Guardar snapshot en RegistroVersion antes de borrar
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
                    'motivo': f'duplicado de parroquia id={superviviente.id}',
                },
                ruta='migration:0017_limpiar_parroquias_duplicadas',
            )
            p.delete()
            eliminados += 1

    print(f'\n[0017] Parroquias duplicadas eliminadas: {eliminados}')
    print(f'[0017] Parroquias restantes: {Parroquia.objects.count()}')


def revertir(apps, schema_editor):
    # No hay reversión automática.
    # Los datos de los eliminados quedan en RegistroVersion con
    # ruta='migration:0017_limpiar_parroquias_duplicadas' para restauración manual.
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0016_restaurar_constraints_zonaafectada'),
    ]

    operations = [
        migrations.RunPython(limpiar_duplicados, revertir),
    ]
