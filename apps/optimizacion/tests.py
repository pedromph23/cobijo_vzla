"""
Tests del módulo de optimización.

Usa datasets pequeños (3-5 elementos) para que el solver termine rápido.
"""
from datetime import datetime, timezone as dt_tz

from django.test import TestCase
from django.contrib.gis.geos import Point, Polygon, MultiPolygon

from apps.core.models import (
    Estado, Parroquia, PuntoDemanda, SitioCandidato,
    ParametrosModelo, ZonaAfectada,
)
from apps.emergencias.models import Evento

from .heatmap import (
    normalizar, calcular_indice_necesidad, generar_mapa_calor,
    obtener_estadisticas_calor, Pesos, Limites,
)
from .optimizer import (
    ejecutar_optimizacion, OptimizacionError,
    _distancia_km, _validar_entrada, TIPOS_MODELO_VALIDOS,
)


def _fecha():
    return datetime(2026, 1, 1, tzinfo=dt_tz.utc)


def _multipolygon_cuadrado(lng: float, lat: float, tam: float = 0.5) -> MultiPolygon:
    """Crea un MultiPolygon cuadrado con centro en (lng, lat)."""
    poly = Polygon([
        (lng - tam, lat - tam),
        (lng - tam, lat + tam),
        (lng + tam, lat + tam),
        (lng + tam, lat - tam),
        (lng - tam, lat - tam),
    ])
    return MultiPolygon(poly)


# ============================================================
# TESTS: heatmap
# ============================================================

class NormalizarTest(TestCase):
    def test_valor_cero(self):
        self.assertEqual(normalizar(0, 100), 0.0)

    def test_valor_negativo(self):
        self.assertEqual(normalizar(-5, 100), 0.0)

    def test_valor_mitad(self):
        self.assertEqual(normalizar(50, 100), 0.5)

    def test_valor_mayor_que_max(self):
        self.assertEqual(normalizar(150, 100), 1.0)

    def test_none(self):
        self.assertEqual(normalizar(None, 100), 0.0)


class PesosTest(TestCase):
    def test_to_dict_tiene_todas_las_claves(self):
        d = Pesos.to_dict()
        for clave in ('densidad', 'vulnerabilidad', 'distancia',
                      'heridos', 'fallecidos', 'damnificados', 'reportes'):
            self.assertIn(clave, d)

    def test_from_request_defaults(self):
        from django.http import QueryDict
        q = QueryDict('')
        d = Pesos.from_request(q)
        self.assertEqual(d['densidad'], 1.0)

    def test_from_request_custom(self):
        from django.http import QueryDict
        q = QueryDict('densidad=2.5&heridos=0')
        d = Pesos.from_request(q)
        self.assertEqual(d['densidad'], 2.5)
        self.assertEqual(d['heridos'], 0)


class HeatmapTest(TestCase):
    def setUp(self):
        estado = Estado.objects.create(nombre='Test')
        self.parroquia = Parroquia.objects.create(
            nombre='Parroquia Test',
            estado=estado,
            geom=_multipolygon_cuadrado(-66.5, 10.5),
            poblacion=10000,
            densidad_poblacional=5000,
            indice_vulnerabilidad=0.6,
        )
        # Refugio operativo para que el cálculo de distancia funcione
        from apps.core.models import RefugioExistente
        RefugioExistente.objects.create(
            nombre='Refugio Test',
            direccion='Calle 1',
            ubicacion=Point(-66.5, 10.5),
            capacidad_total=100,
            capacidad_disponible=50,
            operativo=True,
        )

    def test_indice_necesidad_rango(self):
        indice = calcular_indice_necesidad(self.parroquia)
        self.assertGreaterEqual(indice, 0.0)
        self.assertLessEqual(indice, 1.0)

    def test_generar_mapa_calor(self):
        puntos = generar_mapa_calor(usar_cache=False)
        self.assertGreaterEqual(len(puntos), 1)
        p = puntos[0]
        self.assertIn('lat', p)
        self.assertIn('lng', p)
        self.assertIn('intensidad', p)
        self.assertIn('parroquia', p)

    def test_estadisticas_calor(self):
        stats = obtener_estadisticas_calor()
        self.assertIn('total', stats)
        self.assertIn('promedio', stats)
        self.assertIn('alto', stats)


# ============================================================
# TESTS: optimizer
# ============================================================

class DistanciaTest(TestCase):
    def test_distancia_none(self):
        self.assertEqual(_distancia_km(None, Point(0, 0)), float('inf'))

    def test_distancia_normal(self):
        d = _distancia_km(Point(-66.9, 10.5), Point(-66.8, 10.5))
        self.assertGreater(d, 0)
        self.assertLess(d, 20)  # ~11 km


class ValidacionTest(TestCase):
    def setUp(self):
        self.parametros = ParametrosModelo.objects.create(
            nombre_escenario='Test',
            tipo_modelo='pmediana',
            p=2,
        )

    def test_sin_demandas(self):
        with self.assertRaises(OptimizacionError):
            _validar_entrada([], [object()], self.parametros)

    def test_sin_candidatos(self):
        with self.assertRaises(OptimizacionError):
            _validar_entrada([object()], [], self.parametros)

    def test_tipo_invalido(self):
        self.parametros.tipo_modelo = 'invalido'
        with self.assertRaises(OptimizacionError):
            _validar_entrada([object()], [object()], self.parametros)


class OptimizacionTest(TestCase):
    """Test end-to-end con dataset mínimo."""

    def setUp(self):
        estado = Estado.objects.create(nombre='Test')
        self.parroquia = Parroquia.objects.create(
            nombre='Parroquia',
            estado=estado,
            geom=_multipolygon_cuadrado(-66.5, 10.5),
        )
        # 3 demandas
        for i, (lng, lat) in enumerate([(-66.9, 10.5), (-66.7, 10.5), (-66.5, 10.5)]):
            PuntoDemanda.objects.create(
                nombre=f'Demanda {i}',
                parroquia=self.parroquia,
                ubicacion=Point(lng, lat),
                poblacion=1000 * (i + 1),
                vulnerabilidad=0.5,
            )
        # 2 candidatos
        SitioCandidato.objects.create(
            nombre=f'Sitio {i}',
            ubicacion=Point(lng, lat),
            capacidad_maxima=10000,  # ← suficiente para toda la población
            disponible=True,
        )

    def _run(self, tipo):
        p = ParametrosModelo.objects.create(
            nombre_escenario=f'Test {tipo}',
            tipo_modelo=tipo,
            p=1,
            radio_cobertura=50000,
        )
        return ejecutar_optimizacion(p.id)

    def test_pmediana(self):
        r = self._run('pmediana')
        self.assertNotIn('error', r)
        self.assertEqual(r['total_centros'], 1)
        self.assertGreater(r['poblacion_atendida'], 0)
        self.assertIn('tiempo_ejecucion_seg', r)

    def test_pcentro(self):
        r = self._run('pcentro')
        self.assertNotIn('error', r)
        self.assertEqual(r['total_centros'], 1)

    def test_cobertura(self):
        r = self._run('cobertura')
        self.assertNotIn('error', r)
        self.assertEqual(r['total_centros'], 1)

    def test_capacidades(self):
        r = self._run('capacidades')
        self.assertNotIn('error', r)

    def test_parametros_inexistentes(self):
        r = ejecutar_optimizacion(99999)
        self.assertIn('error', r)
        self.assertEqual(r['tipo_error'], 'validacion')