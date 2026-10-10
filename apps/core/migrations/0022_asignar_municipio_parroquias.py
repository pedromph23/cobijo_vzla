"""
Asigna municipio a cada parroquia existente usando geometría.

Algoritmo:
1. Por cada parroquia sin municipio, buscar municipio que contenga su
   ST_PointOnSurface y que sea del mismo estado.
2. Si no hay match directo, buscar municipio con mayor intersección de área
   dentro del mismo estado.
3. Si no hay match, dejar municipio=NULL para revisión manual.

PostGIS garantiza eficiencia con índices GiST en ambos lados.

Idempotente: solo procesa parroquias con municipio_id IS NULL.
"""
from django.db import connection, migrations


def asignar_municipios(apps, schema_editor):
    Parroquia = apps.get_model('core', 'Parroquia')
    Municipio = apps.get_model('core', 'Municipio')

    total = Parroquia.objects.count()
    sin_municipio_inicial = Parroquia.objects.filter(municipio__isnull=True).count()

    print()
    print(f'[0022] Parroquias totales:                {total}')
    print(f'[0022] Parroquias sin municipio inicial:  {sin_municipio_inicial}')
    print()

    if sin_municipio_inicial == 0:
        print('[0022] Nada que hacer.')
        return

    # =========================================================
    # Paso 1: asignar por ST_Contains(ST_PointOnSurface(parroquia))
    # =========================================================
    with connection.cursor() as c:
        c.execute("""
            UPDATE core_parroquia p
            SET municipio_id = m.id
            FROM core_municipio m
            WHERE p.municipio_id IS NULL
              AND p.geom IS NOT NULL
              AND p.estado_id = m.estado_id
              AND ST_Contains(m.geom, ST_PointOnSurface(p.geom))
        """)
        paso1 = c.rowcount

    print(f'[0022] Paso 1 (ST_Contains PointOnSurface): {paso1}')

    # =========================================================
    # Paso 2: para los que quedan, asignar por mayor intersección
    # =========================================================
    with connection.cursor() as c:
        c.execute("""
            UPDATE core_parroquia p
            SET municipio_id = sub.municipio_id
            FROM (
                SELECT DISTINCT ON (p2.id)
                    p2.id AS parroquia_id,
                    m.id AS municipio_id,
                    ST_Area(ST_Intersection(p2.geom, m.geom)) AS area_interseccion
                FROM core_parroquia p2
                JOIN core_municipio m ON m.estado_id = p2.estado_id
                WHERE p2.municipio_id IS NULL
                  AND p2.geom IS NOT NULL
                  AND m.geom IS NOT NULL
                  AND ST_Intersects(p2.geom, m.geom)
                ORDER BY p2.id, ST_Area(ST_Intersection(p2.geom, m.geom)) DESC
            ) sub
            WHERE p.id = sub.parroquia_id
        """)
        paso2 = c.rowcount

    print(f'[0022] Paso 2 (mayor intersección):        {paso2}')

    # =========================================================
    # Resultado
    # =========================================================
    con_municipio = Parroquia.objects.filter(municipio__isnull=False).count()
    sin_municipio = Parroquia.objects.filter(municipio__isnull=True).count()

    print()
    print(f'[0022] Parroquias con municipio:          {con_municipio}')
    print(f'[0022] Parroquias sin municipio (final):  {sin_municipio}')

    if sin_municipio > 0:
        print()
        print(f'[0022] Parroquias que quedan sin municipio (primeras 20):')
        for p in Parroquia.objects.filter(municipio__isnull=True).order_by('estado__nombre', 'nombre')[:20]:
            print(f'  id={p.id} {p.nombre!r} ({p.estado.nombre})')


def revertir(apps, schema_editor):
    """Revierte poniendo municipio=NULL en todas las parroquias."""
    Parroquia = apps.get_model('core', 'Parroquia')
    Parroquia.objects.update(municipio=None)


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0021_poblar_municipios'),
    ]

    operations = [
        migrations.RunPython(asignar_municipios, revertir),
    ]
