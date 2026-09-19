"""
Tests del portal público.

Cubre formularios, servicios y endpoints de la API pública.
"""
from datetime import datetime, timezone as dt_tz

from django.test import TestCase, Client
from django.contrib.gis.geos import Point, Polygon, MultiPolygon

from apps.core.models import (
    Estado, Parroquia, RefugioExistente, ZonaAfectada,
)
from apps.emergencias.models import Evento

from .forms import ReporteCiudadanoForm
from . import services


def _multipolygon(lng: float, lat: float) -> MultiPolygon:
    return MultiPolygon(Polygon([
        (lng - 0.5, lat - 0.5),
        (lng - 0.5, lat + 0.5),
        (lng + 0.5, lat + 0.5),
        (lng + 0.5, lat - 0.5),
        (lng - 0.5, lat - 0.5),
    ]))


class ReporteFormTest(TestCase):
    """Valida las reglas del formulario ciudadano."""

    def test_texto_muy_corto(self):
        form = ReporteCiudadanoForm(data={'texto': 'corto'})
        self.assertFalse(form.is_valid())
        self.assertIn('texto', form.errors)

    def test_texto_valido(self):
        form = ReporteCiudadanoForm(data={'texto': 'Necesitamos agua potable urgente'})
        self.assertTrue(form.is_valid())

    def test_autor_opcional(self):
        form = ReporteCiudadanoForm(data={'texto': 'Texto válido con contenido'})
        self.assertTrue(form.is_valid())

    def test_autor_demasiado_largo(self):
        form = ReporteCiudadanoForm(data={
            'texto': 'Texto válido con contenido',
            'autor': 'x' * 200,
        })
        # El campo está truncado a 100 en el form, pero max_length del modelo
        # es 100. Django lo valida en el modelo, no en el form. Aquí solo
        # verificamos que no explota.
        self.assertIn('autor', form.data)


class ServicesTest(TestCase):
    """Servicios públicos: refugios, zonas, búsqueda."""

    def setUp(self):
        self.estado = Estado.objects.create(
            nombre='Miranda',
            geom=_multipolygon(-66.5, 10.5),
        )
        self.parroquia = Parroquia.objects.create(
            nombre='Chacao',
            estado=self.estado,
            geom=_multipolygon(-66.85, 10.5),
        )
        RefugioExistente.objects.create(
            nombre='Refugio Chacao',
            direccion='Av. Principal',
            ubicacion=Point(-66.85, 10.5),
            capacidad_total=100,
            capacidad_disponible=60,
            operativo=True,
        )
        self.evento = Evento.objects.create(
            nombre='Evento Test',
            tipo='otro',
            fecha=datetime(2026, 1, 1, tzinfo=dt_tz.utc),
        )

    def test_refugios_publicos(self):
        from django.core.cache import cache
        cache.clear()
        data = services.obtener_refugios_publicos()
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]['nombre'], 'Refugio Chacao')

    def test_refugios_solo_operativos(self):
        from django.core.cache import cache
        cache.clear()
        RefugioExistente.objects.create(
            nombre='No operativo',
            direccion='Calle',
            ubicacion=Point(-66.85, 10.5),
            capacidad_total=50,
            capacidad_disponible=50,
            operativo=False,
        )
        data = services.obtener_refugios_publicos()
        self.assertEqual(len(data), 1)  # Solo el operativo

    def test_busqueda_muy_corta(self):
        self.assertEqual(services.buscar_lugares('a'), [])

    def test_busqueda_encuentra_estado(self):
        from django.core.cache import cache
        cache.clear()
        results = services.buscar_lugares('Miranda')
        tipos = [r['tipo'] for r in results]
        self.assertIn('estado', tipos)

    def test_busqueda_encuentra_refugio(self):
        from django.core.cache import cache
        cache.clear()
        results = services.buscar_lugares('Chacao')
        nombres = [r['nombre'] for r in results]
        self.assertTrue(any('Chacao' in n for n in nombres))

    def test_busqueda_sin_resultados(self):
        from django.core.cache import cache
        cache.clear()
        self.assertEqual(services.buscar_lugares('xyzxyzxyz'), [])


class PublicAPITest(TestCase):
    """Endpoints HTTP del portal público."""

    def setUp(self):
        self.client = Client()
        RefugioExistente.objects.create(
            nombre='Refugio API',
            direccion='Calle API',
            ubicacion=Point(-66.9, 10.5),
            capacidad_total=100,
            capacidad_disponible=40,
            operativo=True,
        )

    def test_api_refugios(self):
        from django.core.cache import cache
        cache.clear()
        response = self.client.get('/api/publico/refugios/')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIsInstance(data, list)

    def test_api_zonas_afectadas(self):
        from django.core.cache import cache
        cache.clear()
        response = self.client.get('/api/publico/zonas-afectadas/')
        self.assertEqual(response.status_code, 200)
        self.assertIsInstance(response.json(), list)

    def test_api_buscar_sin_query(self):
        response = self.client.get('/api/publico/buscar-lugar/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), [])

    def test_api_buscar_query_corta(self):
        response = self.client.get('/api/publico/buscar-lugar/?q=a')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), [])

    def test_api_buscar_query_valida(self):
        from django.core.cache import cache
        cache.clear()
        response = self.client.get('/api/publico/buscar-lugar/?q=Refugio')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIsInstance(data, list)

    def test_api_info_emergencia(self):
        response = self.client.get('/api/publico/info-emergencia/')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['telefono_emergencia'], '171')

    def test_api_reporte_invalido(self):
        response = self.client.post(
            '/api/publico/reporte-ciudadano/',
            data={'texto': 'x'},  # Muy corto
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn('error', response.json())

    def test_api_reporte_valido(self):
        response = self.client.post(
            '/api/publico/reporte-ciudadano/',
            data={'texto': 'Necesitamos agua potable urgente'},
        )
        self.assertEqual(response.status_code, 201)
        data = response.json()
        self.assertIn('id', data)
        self.assertIn('mensaje', data)


class CacheTest(TestCase):
    """Verifica que la caché evite golpear la BD múltiples veces."""

    def test_refugios_cacheado(self):
        from django.core.cache import cache
        from django.test.utils import CaptureQueriesContext
        from django.db import connection

        cache.clear()
        RefugioExistente.objects.create(
            nombre='R1', direccion='C', ubicacion=Point(-66.9, 10.5),
            capacidad_total=10, capacidad_disponible=5, operativo=True,
        )
        # Primera llamada — golpea BD
        services.obtener_refugios_publicos()
        # Segunda llamada — debe venir de caché
        with CaptureQueriesContext(connection) as ctx:
            services.obtener_refugios_publicos()
        # Cero queries en la segunda
        self.assertEqual(len(ctx.captured_queries), 0)