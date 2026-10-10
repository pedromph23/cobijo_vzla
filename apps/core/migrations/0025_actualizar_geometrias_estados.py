"""
Actualiza las geometrías de Estado con las del .gdb original.

Contexto:
Las geometrías de estado en la BD están ultra-simplificadas (área total
17,020 km²). Las reales suman ~913,000 km². Esto causaba falsos negativos
en operaciones espaciales entre niveles territoriales:

- Municipios que intersectan con su estado: 74/336.
- Parroquias que intersectan con su estado: 146/1121.

Fuente:
apps/core/data/estados_venezuela.json (extraído de ven_admin1 del .gdb,
simplificado con `-simplify 0.001` ≈ 100 m de tolerancia).

Estrategia:
- UPDATE de la geometría por nombre de estado (los nombres coinciden 25/25).
- Idempotente: si la geometría ya es correcta, no cambia nada sustancial.
- Reversible vía RegistroVersion (los signals de Django ya lo hacen).
"""
import json
from pathlib import Path

from django.contrib.gis.geos import GEOSGeometry, MultiPolygon, Polygon
from django.db import migrations


def _cargar_estados():
    data_path = Path(__file__).resolve().parent.parent / 'data' / 'estados_venezuela.json'
    if not data_path.exists():
        raise FileNotFoundError(f'No encontré {data_path}')
    with open(data_path, encoding='utf-8') as f:
        return json.load(f)


def _geojson_a_multipolygon(geom_dict):
    """Convierte un dict GeoJSON a MultiPolygon GEOS con SRID 4326."""
    geom = GEOSGeometry(json.dumps(geom_dict), srid=4326)
    if isinstance(geom, Polygon):
        geom = MultiPolygon(geom, srid=4326)
    elif not isinstance(geom, MultiPolygon):
        raise ValueError(f'Tipo de geometría inesperado: {geom.geom_type}')
    return geom


def actualizar_geometrias(apps, schema_editor):
    Estado = apps.get_model('core', 'Estado')

    estados_data = _cargar_estados()
    estados_por_nombre = {e.nombre: e for e in Estado.objects.all()}

    actualizados = 0
    sin_match = 0
    sin_cambio = 0

    for item in estados_data:
        estado = estados_por_nombre.get(item['nombre'])
        if not estado:
            sin_match += 1
            continue

        nueva_geom = _geojson_a_multipolygon(item['geom_geojson'])

        # Solo actualizar si la geometría cambia.
        if estado.geom and estado.geom.equals(nueva_geom):
            sin_cambio += 1
            continue

        estado.geom = nueva_geom
        estado.save(update_fields=['geom'])
        actualizados += 1

    print()
    print(f'[0025] Estados actualizados: {actualizados}')
    print(f'[0025] Sin cambio:           {sin_cambio}')
    print(f'[0025] Sin match por nombre: {sin_match}')
    print()

    # Verificación del área total
    from django.db import connection
    with connection.cursor() as c:
        c.execute('''
            SELECT ROUND(SUM(ST_Area(geom::geography))/1000000)
            FROM core_estado WHERE geom IS NOT NULL
        ''')
        total_km2 = c.fetchone()[0]
        print(f'[0025] Área total de estados: {total_km2:,} km² (real: ~916,445)')


def revertir(apps, schema_editor):
    """Revierte poniendo geom=NULL (no podemos recuperar la versión previa
    sin depender de RegistroVersion, que tiene la info si es necesario)."""
    Estado = apps.get_model('core', 'Estado')
    # No borramos: dejar las geometrías actuales es mejor que borrarlas.
    # Si fuera necesario revertir de verdad, se restauran desde RegistroVersion.
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0024_fix_unique_together_parroquia'),
    ]

    operations = [
        migrations.RunPython(actualizar_geometrias, revertir),
    ]
