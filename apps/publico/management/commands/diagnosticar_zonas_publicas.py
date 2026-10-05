from django.core.management.base import BaseCommand
from django.db.models import Q
from django.utils import timezone

from apps.core.models import ZonaAfectada


class Command(BaseCommand):
    help = 'Diagnostica por qué las zonas afectadas no aparecen en el portal público.'

    def handle(self, *args, **options):
        ahora = timezone.now()
        total = ZonaAfectada.objects.count()
        con_geom = ZonaAfectada.objects.filter(geom__isnull=False).count()
        iniciadas = ZonaAfectada.objects.filter(fecha_inicio__lte=ahora).count()
        vigentes = ZonaAfectada.objects.filter(
            fecha_inicio__lte=ahora,
        ).filter(Q(fecha_fin__isnull=True) | Q(fecha_fin__gte=ahora)).count()
        publicables = ZonaAfectada.objects.filter(
            fecha_inicio__lte=ahora,
            geom__isnull=False,
        ).filter(Q(fecha_fin__isnull=True) | Q(fecha_fin__gte=ahora)).count()

        self.stdout.write(self.style.MIGRATE_HEADING('Diagnóstico de zonas públicas'))
        self.stdout.write(f'Ahora: {ahora.isoformat()}')
        self.stdout.write(f'Total ZonaAfectada: {total}')
        self.stdout.write(f'Con geometría: {con_geom}')
        self.stdout.write(f'Con inicio ya ocurrido: {iniciadas}')
        self.stdout.write(f'Vigentes por fechas: {vigentes}')
        self.stdout.write(self.style.SUCCESS(f'Publicables por la API: {publicables}'))

        if publicables:
            self.stdout.write('\nZonas que debería devolver la API:')
            for zona in ZonaAfectada.objects.filter(
                fecha_inicio__lte=ahora,
                geom__isnull=False,
            ).filter(Q(fecha_fin__isnull=True) | Q(fecha_fin__gte=ahora)).order_by('-fecha_inicio')[:20]:
                self.stdout.write(
                    f'  #{zona.pk} | {zona.nombre} | inicio={zona.fecha_inicio.isoformat()} | '
                    f'fin={zona.fecha_fin.isoformat() if zona.fecha_fin else "NULL"} | '
                    f'geom={zona.geom.geom_type}'
                )
        elif total:
            self.stdout.write('\nDetalle de las últimas zonas registradas:')
            for zona in ZonaAfectada.objects.order_by('-fecha_inicio')[:20]:
                self.stdout.write(
                    f'  #{zona.pk} | {zona.nombre} | inicio={zona.fecha_inicio.isoformat()} | '
                    f'fin={zona.fecha_fin.isoformat() if zona.fecha_fin else "NULL"} | '
                    f'geom={"SI" if zona.geom else "NO"}'
                )
