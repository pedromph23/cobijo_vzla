"""
Comando para cargar refugios DEMO marcados con [DEMO] en Supabase.

- Distribuye los refugios proporcionalmente al número de parroquias por estado.
- Usa el centroide de cada parroquia + jitter de ±50m.
- Prefijo [DEMO] permite eliminar todo con `python manage.py limpiar_demo`.
- Nunca sobrescribe datos reales.
- Nunca llama a save() por instancia (usa bulk_create por lotes).
"""
import random

from django.contrib.gis.geos import Point
from django.core.management.base import BaseCommand
from django.db import connection, transaction
from django.db.models import Count

from apps.core.models import Estado, Parroquia, RefugioExistente


PREFIJO = '[DEMO]'

TIPOS = {
    'escuela': {
        'prefijos_nombre': [
            'U.E. Bolivariana', 'U.E.N.', 'Escuela Básica',
            'Liceo Bolivariano', 'E.B.N.', 'U.E. Nacional',
        ],
        'capacidad_min': 200,
        'capacidad_max': 800,
        'peso': 0.55,
    },
    'plaza': {
        'prefijos_nombre': [
            'Plaza Bolívar de', 'Plaza Sucre de', 'Plaza Miranda de',
            'Plaza de', 'Plaza Pública de',
        ],
        'capacidad_min': 100,
        'capacidad_max': 400,
        'peso': 0.20,
    },
    'parque': {
        'prefijos_nombre': [
            'Parque Recreacional', 'Parque Metropolitano',
            'Parque', 'Parque Vecinal',
        ],
        'capacidad_min': 300,
        'capacidad_max': 1200,
        'peso': 0.25,
    },
}

NOMBRES_HEROES = [
    'Bolívar', 'Sucre', 'Miranda', 'Simón Rodríguez', 'Andrés Bello',
    'Rómulo Gallegos', 'Andrés Eloy Blanco', 'José Martí',
    'Francisco de Miranda', 'Teresa Carreño', 'Simón Bolívar',
    'Rafael Urdaneta', 'José Antonio Páez', 'Antonio José de Sucre',
    'Ezequiel Zamora', 'Cacique Guaicaipuro', 'Cacique Tiuna',
    'Cacique Chacao', 'Cacique Maragüey', 'Cacique Caricuao',
    'Manuel Piar', 'Santiago Mariño', 'José Félix Ribas',
    'Juan Bautista Arismendi', 'Luisa Cáceres de Arismendi',
]

SERVICIOS_POSIBLES = [
    'agua', 'alimentacion', 'medicina', 'primeros_auxilios',
    'higiene', 'atencion_medica', 'electricidad', 'internet',
]

HORARIOS = ['24/7', '07:00-18:00', '08:00-20:00', '06:00-22:00', 'Lun-Vie 08:00-17:00']

PREFIJOS_TELEFONO = ['412', '414', '416', '424', '426']


def _elegir_tipo(rng):
    r = rng.random()
    acum = 0
    for tipo, cfg in TIPOS.items():
        acum += cfg['peso']
        if r <= acum:
            return tipo
    return 'escuela'


def _generar_nombre(tipo, parroquia, rng):
    cfg = TIPOS[tipo]
    prefijo = rng.choice(cfg['prefijos_nombre'])
    nombre = rng.choice(NOMBRES_HEROES)
    if tipo == 'plaza' and prefijo.endswith('de'):
        return f'{PREFIJO} {prefijo} {parroquia.nombre}'
    return f'{PREFIJO} {prefijo} {nombre}'


def _generar_direccion(parroquia, rng):
    sector = rng.choice([
        'Centro', 'Casco Central', 'Urbanización', 'Barrio', 'Sector Norte',
        'Sector Sur', 'Sector Este', 'Sector Oeste', 'Zona Industrial',
    ])
    municipio = parroquia.municipio.nombre if parroquia.municipio else '—'
    return f'{sector} de {parroquia.nombre}, Municipio {municipio}, {parroquia.estado.nombre}'


def _generar_ubicacion(parroquia, rng):
    c = parroquia.centroide
    if c is None:
        return None
    lat, lng = c
    jitter = 0.0005  # ≈ 50 m
    lat_j = lat + rng.uniform(-jitter, jitter)
    lng_j = lng + rng.uniform(-jitter, jitter)
    return Point(lng_j, lat_j, srid=4326)


def _generar_capacidades(tipo, rng):
    cfg = TIPOS[tipo]
    total = rng.randint(cfg['capacidad_min'], cfg['capacidad_max'])
    if rng.random() < 0.3:
        disponible = rng.randint(0, max(1, int(total * 0.15)))
    else:
        disponible = rng.randint(int(total * 0.3), total)
    return total, disponible


def _generar_servicios(tipo, rng):
    if tipo == 'escuela':
        n = rng.randint(3, 6)
    elif tipo == 'plaza':
        n = rng.randint(1, 3)
    else:
        n = rng.randint(2, 4)
    return sorted(rng.sample(SERVICIOS_POSIBLES, n))


def _generar_telefono(rng):
    return f'+58 {rng.choice(PREFIJOS_TELEFONO)}-{rng.randint(1000000, 9999999)}'


def _distribuir_por_estado(estados, cantidad_total, rng):
    conteo = {e.id: e.n for e in estados}
    total_parroquias = sum(conteo.values()) or 1
    asignado = {}
    acumulado = 0
    for estado_id, n_parroquias in conteo.items():
        asig = round(cantidad_total * (n_parroquias / total_parroquias))
        asignado[estado_id] = asig
        acumulado += asig
    diff = cantidad_total - acumulado
    if diff != 0:
        estado_max = max(asignado, key=asignado.get)
        asignado[estado_max] += diff
    return asignado


class Command(BaseCommand):
    help = 'Carga N refugios DEMO marcados con [DEMO] en la BD'

    def add_arguments(self, parser):
        parser.add_argument('--cantidad', type=int, default=500)
        parser.add_argument('--seed', type=int, default=42)
        parser.add_argument('--dry-run', action='store_true')
        parser.add_argument('--yes', action='store_true')
        parser.add_argument('--batch-size', type=int, default=50)

    def handle(self, *args, **opts):
        cantidad = opts['cantidad']
        seed = opts['seed']
        dry_run = opts['dry_run']
        yes = opts['yes']
        batch_size = opts['batch_size']

        rng = random.Random(seed)

        host = connection.settings_dict.get('HOST', '')
        es_supabase = 'supabase' in host.lower() or 'aws-' in host.lower()

        self.stdout.write('')
        self.stdout.write(self.style.WARNING('=' * 60))
        self.stdout.write(self.style.WARNING('CARGA DE DATOS DEMO'))
        self.stdout.write(self.style.WARNING('=' * 60))
        self.stdout.write(f'Host BD:    {host or "(localhost)"}')
        self.stdout.write(f'Nombre BD:  {connection.settings_dict.get("NAME", "?")}')
        if es_supabase:
            self.stdout.write(self.style.ERROR('ADVERTENCIA: SUPABASE (PRODUCCION)'))
        self.stdout.write(f'Cantidad:   {cantidad} refugios')
        self.stdout.write(f'Prefijo:    {PREFIJO}')
        self.stdout.write(f'Seed:       {seed}')
        self.stdout.write(f'Dry-run:    {dry_run}')
        self.stdout.write(self.style.WARNING('=' * 60))
        self.stdout.write('')

        if not dry_run and not yes:
            if es_supabase:
                self.stdout.write(self.style.ERROR(
                    'Estas a punto de crear datos FICTICIOS en PRODUCCION.'
                ))
            respuesta = input('Continuar? Escribe SI para confirmar: ').strip()
            if respuesta != 'SI':
                self.stdout.write(self.style.WARNING('Cancelado.'))
                return

        self.stdout.write('Cargando parroquias...')
        estados = list(
            Estado.objects.annotate(n=Count('parroquias')).filter(n__gt=0)
        )
        if not estados:
            self.stdout.write(self.style.ERROR('No hay estados con parroquias.'))
            return

        distribucion = _distribuir_por_estado(estados, cantidad, rng)
        self.stdout.write(f'Distribucion calculada para {len(distribucion)} estados.')

        existentes = RefugioExistente.objects.filter(nombre__startswith=PREFIJO).count()
        if existentes > 0:
            self.stdout.write(self.style.WARNING(
                f'Ya existen {existentes} refugios DEMO. Se anadiran {cantidad} mas.'
            ))

        self.stdout.write('Generando refugios en memoria...')
        refugios = []
        for estado in estados:
            cuantos = distribucion.get(estado.id, 0)
            if cuantos == 0:
                continue
            parroquias = list(
                Parroquia.objects.filter(estado=estado)
                .exclude(geom__isnull=True)
                .select_related('municipio', 'estado')
            )
            if not parroquias:
                continue
            for _ in range(cuantos):
                parroquia = rng.choice(parroquias)
                tipo = _elegir_tipo(rng)
                ubicacion = _generar_ubicacion(parroquia, rng)
                if ubicacion is None:
                    continue
                cap_total, cap_disp = _generar_capacidades(tipo, rng)
                refugios.append(RefugioExistente(
                    nombre=_generar_nombre(tipo, parroquia, rng)[:200],
                    direccion=_generar_direccion(parroquia, rng)[:300],
                    parroquia=parroquia,
                    ubicacion=ubicacion,
                    capacidad_total=cap_total,
                    capacidad_disponible=cap_disp,
                    servicios=_generar_servicios(tipo, rng),
                    operativo=rng.random() < 0.9,
                    telefono=_generar_telefono(rng),
                    horario=rng.choice(HORARIOS),
                ))

        self.stdout.write(f'Generados {len(refugios)} refugios.')
        self.stdout.write('')
        self.stdout.write('Muestra de 5 refugios:')
        for r in refugios[:5]:
            self.stdout.write(f'  {r.nombre}')
            self.stdout.write(f'    -> {r.parroquia.nombre}, {r.parroquia.estado.nombre}')
            self.stdout.write(f'    -> cap {r.capacidad_total} / disp {r.capacidad_disponible}')
        self.stdout.write('')

        if dry_run:
            self.stdout.write(self.style.SUCCESS('DRY-RUN: no se escribio nada.'))
            return

        self.stdout.write('Insertando en la BD...')
        with transaction.atomic():
            RefugioExistente.objects.bulk_create(refugios, batch_size=batch_size)

        self.stdout.write(self.style.SUCCESS(
            f'OK: {len(refugios)} refugios DEMO creados.'
        ))
        self.stdout.write('')
        self.stdout.write('Para eliminarlos: python manage.py limpiar_demo')
