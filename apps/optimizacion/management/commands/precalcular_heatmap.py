"""
Comando para precalcular el heatmap.

Uso:
    python manage.py precalcular_heatmap

Útil para ejecutar tras cargar datos o como cron job periódico.
El resultado queda cacheado, así el primer usuario no espera 30s.
"""
import time
from django.core.management.base import BaseCommand
from django.core.cache import cache

from apps.optimizacion.heatmap import generar_mapa_calor, CACHE_TTL_HEATMAP


class Command(BaseCommand):
    help = 'Precalcula el heatmap y lo guarda en caché'

    def handle(self, *args, **options):
        self.stdout.write('Limpiando caché previo...')
        cache.clear()

        self.stdout.write('Generando heatmap (puede tardar)...')
        inicio = time.time()
        puntos = generar_mapa_calor(usar_cache=False)
        duracion = time.time() - inicio

        self.stdout.write(self.style.SUCCESS(
            f'✅ {len(puntos)} puntos generados en {duracion:.2f}s'
        ))
        self.stdout.write(
            f'Caché válido por {CACHE_TTL_HEATMAP // 60} minutos.'
        )