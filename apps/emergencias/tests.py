"""
Tests unitarios del módulo de Emergencias.

Verifica propiedades y comportamientos clave de Evento y Reporte.
"""
from datetime import datetime, timezone as dt_timezone

from django.test import TestCase
from django.contrib.gis.geos import Polygon
from django.utils import timezone

from .models import Evento, Reporte
from apps.core.models import ZonaAfectada


def fecha(y, m, d, h=0, mi=0):
    """Helper: crea un datetime con timezone UTC."""
    return datetime(y, m, d, h, mi, tzinfo=dt_timezone.utc)


class EventoModelTest(TestCase):
    def setUp(self):
        self.evento = Evento.objects.create(
            nombre='Sismo Caracas',
            tipo='terremoto',
            fecha=fecha(2026, 1, 15, 10, 0),
            magnitud=6.5,
            activo=True,
        )

    def test_str(self):
        s = str(self.evento)
        self.assertIn('Sismo Caracas', s)
        self.assertIn('Terremoto', s)

    def test_color(self):
        self.assertEqual(self.evento.color, '#dc3545')

    def test_color_default(self):
        self.evento.tipo = 'otro'
        self.evento.save()
        self.assertEqual(self.evento.color, '#6c757d')

    def test_magnitud_fmt_con_valor(self):
        self.assertEqual(self.evento.magnitud_fmt, '6.50')

    def test_magnitud_fmt_sin_valor(self):
        self.evento.magnitud = None
        self.evento.save()
        self.assertEqual(self.evento.magnitud_fmt, '—')

    def test_esta_activo(self):
        self.assertTrue(self.evento.esta_activo)

    def test_total_zonas_vacio(self):
        self.assertEqual(self.evento.total_zonas, 0)


class ReporteModelTest(TestCase):
    def setUp(self):
        self.evento = Evento.objects.create(
            nombre='Evento X',
            tipo='inundacion',
            fecha=fecha(2026, 2, 1),
        )
        self.zona = ZonaAfectada.objects.create(
            evento=self.evento,
            nombre='Zona Test',
            geom=Polygon([(0, 0), (0, 1), (1, 1), (1, 0), (0, 0)]),
            nivel_alerta='medio',
            fecha_inicio=fecha(2026, 2, 1),
        )
        self.reporte = Reporte.objects.create(
            zona_afectada=self.zona,
            texto='Se necesita agua potable en la zona.',
            autor='Juan Pérez',
        )

    def test_str(self):
        s = str(self.reporte)
        self.assertIn('Reporte #', s)

    def test_autor_display(self):
        self.assertEqual(self.reporte.autor_display, 'Juan Pérez')

    def test_autor_display_anonimo(self):
        self.reporte.autor = ''
        self.reporte.save()
        self.assertEqual(self.reporte.autor_display, 'Anónimo')

    def test_texto_corto(self):
        texto_largo = 'x' * 200
        self.reporte.texto = texto_largo
        self.reporte.save()
        self.assertEqual(len(self.reporte.texto_corto), 103)  # 100 + '...'
        self.assertTrue(self.reporte.texto_corto.endswith('...'))

    def test_tiene_imagen_false(self):
        self.assertFalse(self.reporte.tiene_imagen)

    def test_asociado_a_zona(self):
        self.assertIn('Zona Test', self.reporte.asociado_a)

    def test_asociado_a_sin(self):
        self.reporte.zona_afectada = None
        self.reporte.punto_demanda = None
        self.reporte.save()
        self.assertEqual(self.reporte.asociado_a, 'Sin asociar')

    def test_color_estado_pendiente(self):
        self.assertEqual(self.reporte.color_estado, '#ffc107')

    def test_color_estado_verificado(self):
        self.reporte.verificado = True
        self.reporte.save()
        self.assertEqual(self.reporte.color_estado, '#28a745')


class EmergenciasAPITest(TestCase):
    def test_api_eventos_activos(self):
        Evento.objects.create(
            nombre='Test 1', tipo='otro',
            fecha=fecha(2026, 1, 1), activo=True
        )
        Evento.objects.create(
            nombre='Test 2', tipo='otro',
            fecha=fecha(2026, 1, 1), activo=False
        )
        response = self.client.get('/api/emergencias/api/eventos-activos/')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['total'], 1)

    def test_api_kpis(self):
        response = self.client.get('/api/emergencias/api/kpis/')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn('eventos', data)
        self.assertIn('reportes', data)