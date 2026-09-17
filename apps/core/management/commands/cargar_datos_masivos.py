import random
from django.core.management.base import BaseCommand
from django.contrib.gis.geos import Point
from apps.core.models import (Estado, Parroquia, PuntoDemanda,
                              SitioCandidato, RefugioExistente,
                              ZonaAfectada, ParametrosModelo)
from apps.emergencias.models import Evento, Reporte

class Command(BaseCommand):
    help = 'Genera 1500 puntos de demanda y otros datos de prueba en todas las parroquias'

    def handle(self, *args, **options):
        self.stdout.write('Iniciando generación de datos masivos...')

        # Obtener todas las parroquias
        parroquias = list(Parroquia.objects.all())
        if not parroquias:
            self.stdout.write(self.style.ERROR('No hay parroquias importadas. Ejecute primero importar_limites.'))
            return

        # 1) Crear 1500 puntos de demanda
        self.stdout.write('Creando 1500 puntos de demanda...')
        for i in range(1500):
            parroquia = random.choice(parroquias)
            # Obtener centroide de la parroquia
            centroide = parroquia.geom.centroid
            # Añadir offset aleatorio (hasta 0.02 grados ~ 2 km) para variar
            lat = centroide.y + random.uniform(-0.02, 0.02)
            lng = centroide.x + random.uniform(-0.02, 0.02)
            # Ajustar para que no se salga mucho (opcional, se podría validar)
            punto = Point(lng, lat, srid=4326)
            PuntoDemanda.objects.create(
                nombre=f'Comunidad {i+1}',
                parroquia=parroquia,
                ubicacion=punto,
                poblacion=random.randint(100, 5000),
                vulnerabilidad=round(random.uniform(0.2, 1.0), 2),
                descripcion=f'Punto de demanda generado automáticamente #{i+1}'
            )
            if (i+1) % 300 == 0:
                self.stdout.write(f'  {i+1} puntos creados...')

        # 2) Crear 300 sitios candidatos
        self.stdout.write('Creando 300 sitios candidatos...')
        for i in range(300):
            parroquia = random.choice(parroquias)
            centroide = parroquia.geom.centroid
            lat = centroide.y + random.uniform(-0.02, 0.02)
            lng = centroide.x + random.uniform(-0.02, 0.02)
            SitioCandidato.objects.create(
                nombre=f'Sitio Candidato {i+1}',
                ubicacion=Point(lng, lat, srid=4326),
                capacidad_maxima=random.randint(50, 1000),
                costo_apertura=random.randint(1000, 50000),
                costo_operacion=random.randint(500, 10000),
                tipo_terreno=random.choice(['terreno', 'edificio', 'cancha', 'escuela', 'iglesia']),
                disponible=True
            )

        # 3) Crear 200 refugios existentes
        self.stdout.write('Creando 200 refugios existentes...')
        servicios_posibles = [
            ['agua', 'comida'],
            ['agua', 'comida', 'medicina'],
            ['medicina'],
            ['agua'],
            ['comida', 'medicina'],
            ['agua', 'medicina'],
        ]
        for i in range(200):
            parroquia = random.choice(parroquias)
            centroide = parroquia.geom.centroid
            lat = centroide.y + random.uniform(-0.02, 0.02)
            lng = centroide.x + random.uniform(-0.02, 0.02)
            RefugioExistente.objects.create(
                nombre=f'Refugio {i+1}',
                direccion=f'Dirección {i+1}, {parroquia.nombre}',
                ubicacion=Point(lng, lat, srid=4326),
                capacidad_total=random.randint(50, 500),
                capacidad_disponible=random.randint(0, 500),
                servicios=random.choice(servicios_posibles),
                operativo=True,
                telefono=f'+58-{random.randint(200, 999)}-{random.randint(1000000, 9999999)}',
                horario='24 horas'
            )

        # 4) Crear algunos eventos y zonas afectadas (100 zonas)
        self.stdout.write('Creando eventos y zonas afectadas...')
        eventos_data = [
            ('Inundación general', 'inundacion', 7.0),
            ('Sismo moderado', 'terremoto', 5.5),
            ('Deslizamiento', 'deslizamiento', 4.0),
            ('Incendio forestal', 'incendio', 6.0),
            ('Inundación costera', 'inundacion', 6.5),
            ('Sismo fuerte', 'terremoto', 7.8),
        ]
        eventos = []
        for nombre, tipo, magnitud in eventos_data:
            evento = Evento.objects.create(
                nombre=nombre,
                tipo=tipo,
                fecha='2026-08-31T10:00:00Z',
                magnitud=magnitud,
                descripcion=f'Evento {nombre} generado para pruebas',
                activo=True
            )
            eventos.append(evento)

        for i in range(100):
            evento = random.choice(eventos)
            parroquia = random.choice(parroquias)
            centroide = parroquia.geom.centroid
            lat = centroide.y + random.uniform(-0.02, 0.02)
            lng = centroide.x + random.uniform(-0.02, 0.02)
            nivel = random.choice(['bajo', 'medio', 'alto'])
            ZonaAfectada.objects.create(
                evento=evento,
                nombre=f'Zona Afectada {i+1} - {parroquia.nombre}',
                descripcion=f'Descripción de zona afectada {i+1}',
                geom=Point(lng, lat, srid=4326),
                nivel_alerta=nivel,
                fecha_inicio='2026-08-31T10:00:00Z',
                heridos=random.randint(0, 50),
                fallecidos=random.randint(0, 10),
                damnificados=random.randint(0, 300)
            )

        # 5) Crear 200 reportes ciudadanos
        self.stdout.write('Creando reportes ciudadanos...')
        zonas = list(ZonaAfectada.objects.all())
        for i in range(200):
            Reporte.objects.create(
                zona_afectada=random.choice(zonas) if zonas else None,
                autor=f'Ciudadano {i+1}',
                texto=f'Reporte de prueba #{i+1}: Necesitamos ayuda en la zona.',
                verificado=random.choice([True, False])
            )

        # 6) Crear algunos parámetros de modelo por defecto
        self.stdout.write('Creando parámetros de modelo...')
        ParametrosModelo.objects.create(
            nombre_escenario='Escenario Masivo p=20',
            tipo_modelo='pmediana',
            p=20,
            radio_cobertura=5000,
            ponderador_vulnerabilidad=1.0,
            ponderador_heridos=1.0,
            ponderador_fallecidos=2.0,
            ponderador_damnificados=1.0,
        )

        self.stdout.write(self.style.SUCCESS('Generación de datos masivos completada exitosamente.'))
        self.stdout.write(self.style.SUCCESS(f'Total: 1500 puntos de demanda, 300 sitios candidatos, 200 refugios, 100 zonas afectadas, 200 reportes.'))