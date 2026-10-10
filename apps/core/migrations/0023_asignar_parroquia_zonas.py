"""
Asigna parroquia a cada ZonaAfectada existente usando geometría.

Algoritmo (mismo que 0022):
1. Buscar parroquia que contenga ST_PointOnSurface(zona.geom).
2. Fallback: parroquia con mayor área de intersección.

Idempotente: solo procesa zonas con parroquia_id IS NULL.
"""
from django.db import connection, migrations


def asignar_parroquias(apps, schema_editor):
    ZonaAfectada = apps.get_model('core', 'ZonaAfectada')

    total = ZonaAfectada.objects.count()
    sin_parroquia = ZonaAfectada.objects.filter(parroquia__isnull=True).count()

    print()
    print(f'[0023] Zonas totales:                    {total}')
    print(f'[0023] Zonas sin parroquia inicial:      {sin_parroquia}')
    print()

    if sin_parroquia == 0:
        print('[0023] Nada que hacer.')
        return

    # Paso 1: ST_Contains(parroquia.geom, ST_PointOnSurface(zona.geom))
    with connection.cursor() as c:
        c.execute("""
            UPDATE core_zonaafectada z
            SET parroquia_id = p.id
            FROM core_parroquia p
            WHERE z.parroquia_id IS NULL
              AND z.geom IS NOT NULL
              AND p.geom IS NOT NULL
              AND ST_Contains(p.geom, ST_PointOnSurface(z.geom))
        """)
        paso1 = c.rowcount
    print(f'[0023] Paso 1 (ST_Contains PointOnSurface): {paso1}')

    # Paso 2: fallback por mayor intersección
    with connection.cursor() as c:
        c.execute("""
            UPDATE core_zonaafectada z
            SET parroquia_id = sub.parroquia_id
            FROM (
                SELECT DISTINCT ON (z2.id)
                    z2.id AS zona_id,
                    p.id AS parroquia_id,
                    ST_Area(ST_Intersection(z2.geom, p.geom)) AS area
                FROM core_zonaafectada z2
                JOIN core_parroquia p
                  ON p.geom IS NOT NULL
                 AND ST_Intersects(z2.geom, p.geom)
                WHERE z2.parroquia_id IS NULL
                  AND z2.geom IS NOT NULL
                ORDER BY z2.id, ST_Area(ST_Intersection(z2.geom, p.geom)) DESC
            ) sub
            WHERE z.id = sub.zona_id
        """)
        paso2 = c.rowcount
    print(f'[0023] Paso 2 (mayor intersección):        {paso2}')

    con_parroquia = ZonaAfectada.objects.filter(parroquia__isnull=False).count()
    sin_parroquia_final = ZonaAfectada.objects.filter(parroquia__isnull=True).count()

    print()
    print(f'[0023] Zonas con parroquia:              {con_parroquia}')
    print(f'[0023] Zonas sin parroquia (final):      {sin_parroquia_final}')


def revertir(apps, schema_editor):
    ZonaAfectada = apps.get_model('core', 'ZonaAfectada')
    ZonaAfectada.objects.update(parroquia=None)


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0022_asignar_municipio_parroquias'),
    ]

    operations = [
        migrations.RunPython(asignar_parroquias, revertir),
    ]
