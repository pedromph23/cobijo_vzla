"""
Comando para eliminar todos los datos DEMO de la base de datos.

Borra SOLO los registros que tienen el prefijo [DEMO] en el nombre.
Nunca toca datos reales.
"""
from django.core.management.base import BaseCommand
from django.db import connection, transaction
from django.db.models import Q

from apps.core.models import RefugioExistente, SitioCandidato, PuntoDemanda

PREFIJO = '[DEMO]'


class Command(BaseCommand):
    help = 'Elimina todos los registros DEMO ([DEMO] en el nombre)'

    def add_arguments(self, parser):
        parser.add_argument('--yes', action='store_true')
        parser.add_argument('--dry-run', action='store_true')
        parser.add_argument(
            '--modelo',
            choices=['refugio', 'sitio', 'punto', 'todos'],
            default='todos'
        )

    def handle(self, *args, **opts):
        dry_run = opts['dry_run']
        yes = opts['yes']
        modelo = opts['modelo']

        host = connection.settings_dict.get('HOST', '')
        es_supabase = 'supabase' in host.lower() or 'aws-' in host.lower()

        filtros = Q(nombre__startswith=PREFIJO)
        counts = {}
        if modelo in ('refugio', 'todos'):
            counts['RefugioExistente'] = RefugioExistente.objects.filter(filtros).count()
        if modelo in ('sitio', 'todos'):
            counts['SitioCandidato'] = SitioCandidato.objects.filter(filtros).count()
        if modelo in ('punto', 'todos'):
            counts['PuntoDemanda'] = PuntoDemanda.objects.filter(filtros).count()

        self.stdout.write('')
        self.stdout.write(self.style.WARNING('=' * 60))
        self.stdout.write(self.style.WARNING('LIMPIEZA DE DATOS DEMO'))
        self.stdout.write(self.style.WARNING('=' * 60))
        self.stdout.write(f'Host:     {host or "(localhost)"}')
        if es_supabase:
            self.stdout.write(self.style.ERROR('ADVERTENCIA: SUPABASE (PRODUCCION)'))
        self.stdout.write('')
        self.stdout.write('Registros a eliminar:')
        for k, v in counts.items():
            self.stdout.write(f'  {k:25s} {v:>6}')
        total = sum(counts.values())
        self.stdout.write(f'  {"TOTAL":25s} {total:>6}')
        self.stdout.write('')

        if total == 0:
            self.stdout.write(self.style.SUCCESS('No hay datos DEMO para eliminar.'))
            return

        if dry_run:
            self.stdout.write(self.style.SUCCESS('DRY-RUN: no se elimino nada.'))
            return

        if not yes:
            self.stdout.write(self.style.ERROR(
                f'Se van a ELIMINAR {total} registros marcados como [DEMO].'
            ))
            respuesta = input('Confirmar? Escribe BORRAR para continuar: ').strip()
            if respuesta != 'BORRAR':
                self.stdout.write(self.style.WARNING('Cancelado.'))
                return

        with transaction.atomic():
            if modelo in ('refugio', 'todos'):
                n, _ = RefugioExistente.objects.filter(filtros).delete()
                self.stdout.write(f'  Borrados {n} refugios')
            if modelo in ('sitio', 'todos'):
                n, _ = SitioCandidato.objects.filter(filtros).delete()
                self.stdout.write(f'  Borrados {n} sitios')
            if modelo in ('punto', 'todos'):
                n, _ = PuntoDemanda.objects.filter(filtros).delete()
                self.stdout.write(f'  Borrados {n} puntos')

        self.stdout.write(self.style.SUCCESS(
            f'OK: {total} registros eliminados.'
        ))
