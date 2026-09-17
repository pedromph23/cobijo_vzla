import json
from django.core.management.base import BaseCommand
from django.contrib.gis.geos import Point, GEOSGeometry
from apps.core.models import RefugioExistente

class Command(BaseCommand):
    help = 'Importa hospitales, escuelas y plazas reales desde un archivo GeoJSON local de OpenStreetMap'

    def add_arguments(self, parser):
        parser.add_argument('archivo_geojson', type=str, help='Ruta al archivo GeoJSON local (ej: caracas_osm.geojson)')

    def handle(self, *args, **options):
        archivo = options['archivo_geojson']
        self.stdout.write(f"Leyendo archivo local de OpenStreetMap: {archivo}...")

        try:
            with open(archivo, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"No se pudo abrir el archivo: {e}"))
            return

        features = data.get('features', [])
        self.stdout.write(f"Se encontraron {len(features)} elementos en el archivo.")

        contador = 0
        for feature in features:
            props = feature.get('properties', {})
            geom_data = feature.get('geometry', {})

            # Obtener nombre
            tags = props.get('tags', props)
            nombre = tags.get('name')
            if not nombre:
                continue

            try:
                geom = GEOSGeometry(json.dumps(geom_data))
                centroid = geom.centroid
                lng, lat = centroid.x, centroid.y
            except Exception:
                continue

            tipo_lugar = tags.get('amenity') or tags.get('leisure', 'refugio')
            direccion = tags.get('addr:street', 'Ubicación registrada en OSM')

            # Sanitizar y truncar el teléfono a máximo 20 caracteres para evitar el DataError
            telefono_raw = tags.get('phone', 'S/N')
            telefono = str(telefono_raw)[:20] if telefono_raw else 'S/N'

            # Estimar capacidad según la infraestructura
            capacidad = 1000 if tipo_lugar == 'hospital' else (800 if tipo_lugar == 'school' else 2000)

            RefugioExistente.objects.update_or_create(
                nombre=nombre,
                defaults={
                    'direccion': str(direccion)[:300], # Asegurar límite de dirección también
                    'ubicacion': Point(lng, lat, srid=4326),
                    'capacidad_total': capacidad,
                    'capacidad_disponible': int(capacidad * 0.6),
                    'servicios': ['agua', 'medicina', 'primeros_auxilios'],
                    'operativo': True,
                    'telefono': telefono,
                    'horario': str(tags.get('opening_hours', '24/7'))[:100]
                }
            )
            contador += 1

        self.stdout.write(self.style.SUCCESS(f"¡Importación exitosa! Se guardaron {contador} instalaciones reales en la base de datos."))