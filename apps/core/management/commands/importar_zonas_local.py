import json
from django.core.management.base import BaseCommand
from django.contrib.gis.geos import Point, GEOSGeometry
from django.utils import timezone
from apps.core.models import ZonaAfectada
from apps.emergencias.models import Evento

class Command(BaseCommand):
    help = 'Importa zonas afectadas o puntos de emergencia desde un GeoJSON local'

    def add_arguments(self, parser):
        parser.add_argument('archivo_geojson', type=str, help='Ruta al archivo GeoJSON')

    def handle(self, *args, **options):
        archivo = options['archivo_geojson']
        self.stdout.write(f"Leyendo zonas desde: {archivo}...")

        try:
            with open(archivo, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error al abrir archivo: {e}"))
            return

        # Asegurar que exista un evento base asociado al sismo/emergencia
        evento, _ = Evento.objects.get_or_create(
            nombre='Emergencia Registrada OSM',
            defaults={
                'tipo': 'terremoto',
                'fecha': timezone.now(),
                'magnitud': 7.0,
                'descripcion': 'Incidencias extraídas de OpenStreetMap',
                'activo': True
            }
        )

        features = data.get('features', [])
        contador = 0

        for feature in features:
            props = feature.get('properties', {})
            geom_data = feature.get('geometry', {})

            tags = props.get('tags', props)
            nombre = tags.get('name') or f"Incidencia de Emergencia #{contador + 1}"

            try:
                geom = GEOSGeometry(json.dumps(geom_data))
                centroid = geom.centroid
                punto = Point(centroid.x, centroid.y, srid=4326)
            except Exception:
                continue

            # Determinar nivel de alerta según los tags de OSM
            alerta = 'alto' if 'collapsed' in str(tags) else 'medio'

            ZonaAfectada.objects.update_or_create(
                nombre=nombre[:200],
                defaults={
                    'evento': evento,
                    'descripcion': str(tags.get('description', 'Zona reportada con daños o infraestructura de emergencia.'))[:500],
                    'geom': punto,
                    'nivel_alerta': alerta,
                    'fecha_inicio': timezone.now(),
                    'heridos': 50 if alerta == 'alto' else 10,
                    'fallecidos': 5 if alerta == 'alto' else 0,
                    'damnificados': 200 if alerta == 'alto' else 50
                }
            )
            contador += 1

        self.stdout.write(self.style.SUCCESS(f"¡Se importaron {contador} zonas afectadas exitosamente!"))