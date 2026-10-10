"""
Pobla el modelo Municipio con los 336 municipios de Venezuela.

Fuente: apps/core/data/municipios_venezuela.json
Extraído de ven_admin_boundaries.gdb (capa ven_admin2) con ogr2ogr
y simplificado con -simplify 0.005 para reducir peso.

Estrategia:
- Idempotente: si un municipio ya existe (nombre + estado), no duplica.
- Usa apps.get_model para el modelo histórico.
- Convierte GeoJSON a MultiPolygon GEOS.
"""
import json
from pathlib import Path

from django.contrib.gis.geos import GEOSGeometry, MultiPolygon, Polygon
from django.db import migrations


def _cargar_municipios():
    data_path = Path(__file__).resolve().parent.parent / 'data' / 'municipios_venezuela.json'
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


def poblar_municipios(apps, schema_editor):
    Municipio = apps.get_model('core', 'Municipio')
    Estado = apps.get_model('core', 'Estado')

    estados_por_nombre = {e.nombre: e for e in Estado.objects.all()}
    municipios_data = _cargar_municipios()

    creados = 0
    existentes = 0
    sin_estado = 0

    for m in municipios_data:
        estado = estados_por_nombre.get(m['estado'])
        if not estado:
            sin_estado += 1
            continue

        if Municipio.objects.filter(nombre=m['nombre'], estado=estado).exists():
            existentes += 1
            continue

        geom = _geojson_a_multipolygon(m['geom_geojson'])

        Municipio.objects.create(
            nombre=m['nombre'],
            estado=estado,
            codigo_ine=m.get('codigo_ine', '') or None,
            geom=geom,
            poblacion=0,
            densidad_poblacional=0.0,
            indice_vulnerabilidad=0.5,
        )
        creados += 1

    print()
    print(f'[0021] Municipios creados:    {creados}')
    print(f'[0021] Ya existentes:         {existentes}')
    print(f'[0021] Sin estado coincidente: {sin_estado}')
    print(f'[0021] Total en BD:           {Municipio.objects.count()}')


def revertir(apps, schema_editor):
    """Revierte eliminando todos los municipios creados por esta migración."""
    Municipio = apps.get_model('core', 'Municipio')
    Municipio.objects.all().delete()


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0020_zonaafectada_parroquia_fk'),
    ]

    operations = [
        migrations.RunPython(poblar_municipios, revertir),
    ]
