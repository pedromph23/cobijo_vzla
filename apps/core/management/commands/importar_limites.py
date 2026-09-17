import json
from django.core.management.base import BaseCommand
from django.contrib.gis.geos import GEOSGeometry, MultiPolygon
from django.db import transaction
from apps.core.models import Estado, Parroquia


class Command(BaseCommand):
    help = 'Importa límites administrativos desde un archivo GeoJSON (estados y parroquias)'

    def add_arguments(self, parser):
        parser.add_argument('archivo_geojson', type=str, help='Ruta al archivo GeoJSON')
        parser.add_argument('--campo_estado', type=str, default='estado',
                            help='Nombre del campo de estado en properties')
        parser.add_argument('--campo_parroquia', type=str, default='parroquia',
                            help='Nombre del campo de parroquia en properties')

    def handle(self, *args, **options):
        archivo = options['archivo_geojson']
        # 1. Normalizar las opciones ingresadas por el usuario a minúsculas
        campo_estado = options['campo_estado'].lower()
        campo_parroquia = options['campo_parroquia'].lower()

        # 2. Diccionarios de búsqueda: Usar list(dict.fromkeys(...)) elimina los duplicados de esta lista
        posibles_estado = list(dict.fromkeys([
            campo_estado, 'adm1_es', 'name_1', 'adm1_name', 'estado', 'state', 'adm1_pcode'
        ]))
        posibles_parroquia = list(dict.fromkeys([
            campo_parroquia, 'adm3_es', 'name_3', 'adm3_name', 'parroquia', 'municipio', 'adm3_pcode'
        ]))

        try:
            with open(archivo, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except FileNotFoundError:
            self.stdout.write(self.style.ERROR(f"No se encontró el archivo: {archivo}"))
            return
        except json.JSONDecodeError:
            self.stdout.write(self.style.ERROR(f"El archivo {archivo} no es un JSON válido"))
            return

        total_features = len(data.get('features', []))
        self.stdout.write(f"Total de features a procesar: {total_features}")

        contador_estados = 0
        contador_parroquias = 0

        # 3. Transacción Atómica: Acelera la inserción de miles de polígonos x10 y 
        # asegura que si hay error, no se guarde información incompleta.
        with transaction.atomic():
            for feature in data.get('features', []):
                props = feature.get('properties', {})
                geometry = feature.get('geometry', None)

                if not props or not geometry:
                    continue

                # 4. MEJORA DE BÚSQUEDA: Convertir todas las claves del GeoJSON a minúsculas
                props_lower = {str(k).lower(): v for k, v in props.items() if v}

                # Buscar y sanitizar el nombre (Elimina espacios extra y capitaliza: "  CAracas " -> "Caracas")
                estado_nombre = next((str(props_lower[key]).strip().title() for key in posibles_estado if key in props_lower), None)
                parroquia_nombre = next((str(props_lower[key]).strip().title() for key in posibles_parroquia if key in props_lower), None)

                if not estado_nombre or not parroquia_nombre:
                    self.stdout.write(self.style.WARNING(
                        f"Feature omitida (no se detectó estado o parroquia). Keys disponibles: {list(props_lower.keys())}"
                    ))
                    continue

                try:
                    geom = GEOSGeometry(json.dumps(geometry))
                    # Convertir Polygon a MultiPolygon si es estrictamente necesario
                    if geom.geom_type == 'Polygon':
                        geom = MultiPolygon(geom)
                    elif geom.geom_type != 'MultiPolygon':
                        self.stdout.write(self.style.WARNING(
                            f"Geometría no soportada ({geom.geom_type}) en {estado_nombre}/{parroquia_nombre}. Omitida."
                        ))
                        continue
                except Exception as e:
                    self.stdout.write(self.style.ERROR(
                        f"Error de geometría en {estado_nombre}/{parroquia_nombre}: {e}"
                    ))
                    continue

                # 5. PREVENCIÓN DE DUPLICADOS: Ahora get_or_create operará sobre cadenas uniformes
                estado, created_est = Estado.objects.get_or_create(
                    nombre=estado_nombre,
                    defaults={'geom': geom}
                )
                
                # Actualizar geometría si el estado existía pero no la tenía
                if not created_est and not estado.geom:
                    estado.geom = geom
                    estado.save()
                    
                if created_est:
                    contador_estados += 1

                # Crear o actualizar la parroquia
                parroquia, created_parr = Parroquia.objects.update_or_create(
                    nombre=parroquia_nombre,
                    estado=estado,
                    defaults={'geom': geom}
                )
                
                if created_parr:
                    contador_parroquias += 1

        self.stdout.write(self.style.SUCCESS(
            f"¡Importación completada! Estados nuevos: {contador_estados} | Parroquias procesadas: {contador_parroquias}"
        ))