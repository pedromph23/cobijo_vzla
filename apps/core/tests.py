"""
Tests unitarios del módulo Core.

Verifica propiedades calculadas y comportamientos clave de los modelos.
"""
from django.test import TestCase
from django.contrib.gis.geos import Point, Polygon, MultiPolygon

from .models import (
    Estado,
    Parroquia,
    RefugioExistente,
    ZonaAfectada,
    PuntoDemanda,
    ParametrosModelo,
)
from apps.emergencias.models import Evento


class EstadoModelTest(TestCase):
    def test_str(self):
        e = Estado.objects.create(nombre='Miranda')
        self.assertEqual(str(e), 'Miranda')

    def test_total_parroquias(self):
        e = Estado.objects.create(nombre='Miranda')
        self.assertEqual(e.total_parroquias, 0)
        Parroquia.objects.create(nombre='Chacao', estado=e)
        self.assertEqual(e.total_parroquias, 1)


class RefugioExistenteTest(TestCase):
    def setUp(self):
        self.refugio = RefugioExistente.objects.create(
            nombre='Refugio Test',
            direccion='Calle 1',
            ubicacion=Point(-66.9, 10.5),
            capacidad_total=100,
            capacidad_disponible=30,
        )

    def test_porcentaje_ocupacion(self):
        # 100 - 30 = 70 ocupados => 70%
        self.assertEqual(self.refugio.porcentaje_ocupacion, 70.0)

    def test_esta_lleno_false(self):
        self.assertFalse(self.refugio.esta_lleno)

    def test_esta_lleno_true(self):
        self.refugio.capacidad_disponible = 0
        self.refugio.save()
        self.assertTrue(self.refugio.esta_lleno)

    def test_lat_lng(self):
        self.assertAlmostEqual(self.refugio.lat, 10.5, places=4)
        self.assertAlmostEqual(self.refugio.lng, -66.9, places=4)

    def test_servicios_texto_vacio(self):
        self.assertEqual(self.refugio.servicios_texto, 'Sin servicios registrados')

    def test_servicios_texto(self):
        self.refugio.servicios = ['agua', 'comida']
        self.assertEqual(self.refugio.servicios_texto, 'agua, comida')


class ZonaAfectadaTest(TestCase):
    def setUp(self):
        self.evento = Evento.objects.create(
            nombre='Sismo Test',
            tipo='sismo',
            fecha='2026-01-01T00:00:00Z',
        )
        self.zona = ZonaAfectada.objects.create(
            evento=self.evento,
            nombre='Zona A',
            geom=Polygon([(0, 0), (0, 1), (1, 1), (1, 0), (0, 0)]),
            nivel_alerta='alto',
            fecha_inicio='2026-01-01T00:00:00Z',
            heridos=10,
            fallecidos=2,
            damnificados=100,
        )

    def test_total_afectados(self):
        self.assertEqual(self.zona.total_afectados, 112)

    def test_esta_activa(self):
        self.assertTrue(self.zona.esta_activa)

    def test_cerrar_zona(self):
        from django.utils import timezone
        self.zona.fecha_fin = timezone.now()
        self.zona.save()
        self.assertFalse(self.zona.esta_activa)


class ParametrosModeloTest(TestCase):
    def test_radio_cobertura_km(self):
        p = ParametrosModelo.objects.create(
            nombre_escenario='Test',
            tipo_modelo='pmediana',
            radio_cobertura=5000,
        )
        self.assertEqual(p.radio_cobertura_km, 5.0)


class KPIsAPITest(TestCase):
    def test_api_kpis_responde(self):
        response = self.client.get('/api/core/api/kpis/')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn('refugios', data)
        self.assertIn('zonas_activas', data)
        self.assertIn('territorio', data)