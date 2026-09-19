"""
Tests del módulo de reportes.

Cubre servicios de consulta, generación de archivos y seguridad.
"""
import os
from datetime import datetime, timezone as dt_tz

from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.contrib.gis.geos import Point, Polygon, MultiPolygon
from django.conf import settings

from apps.core.models import Estado, Parroquia, ZonaAfectada
from apps.emergencias.models import Evento

from . import services
from .generador_reportes import (
    generar_excel_zonas_afectadas,
    generar_pdf_zonas_afectadas,
    limpiar_reportes_antiguos,
    EXTENSIONES_PERMITIDAS,
)


User = get_user_model()


def _fecha():
    return datetime(2026, 1, 1, tzinfo=dt_tz.utc)


def _multipolygon(lng, lat):
    return MultiPolygon(Polygon([
        (lng - 0.5, lat - 0.5),
        (lng - 0.5, lat + 0.5),
        (lng + 0.5, lat + 0.5),
        (lng + 0.5, lat - 0.5),
        (lng - 0.5, lat - 0.5),
    ]))


class ServicesTest(TestCase):
    def setUp(self):
        self.estado = Estado.objects.create(
            nombre='Miranda',
            geom=_multipolygon(-66.5, 10.5),
        )
        self.parroquia = Parroquia.objects.create(
            nombre='Chacao',
            estado=self.estado,
            geom=_multipolygon(-66.85, 10.5),
            poblacion=50000,
        )
        self.evento = Evento.objects.create(
            nombre='Sismo Test', tipo='terremoto', fecha=_fecha(),
        )
        ZonaAfectada.objects.create(
            evento=self.evento,
            nombre='Zona A',
            geom=Polygon([(0, 0), (0, 1), (1, 1), (1, 0), (0, 0)]),
            nivel_alerta='alto',
            fecha_inicio=_fecha(),
            heridos=10,
            fallecidos=2,
            damnificados=100,
        )

    def test_df_zonas_no_vacio(self):
        df = services.df_zonas_afectadas()
        self.assertFalse(df.empty)
        self.assertIn('Nombre', df.columns)
        self.assertIn('Heridos', df.columns)

    def test_df_refugios_estructura(self):
        df = services.df_refugios()
        # No hay refugios → DataFrame vacío pero con columnas esperadas
        self.assertEqual(len(df), 0)

    def test_df_eventos(self):
        df = services.df_eventos()
        self.assertEqual(len(df), 1)
        self.assertEqual(df.iloc[0]['Nombre'], 'Sismo Test')

    def test_resumen_general(self):
        r = services.resumen_general()
        self.assertEqual(r['estados'], 1)
        self.assertEqual(r['parroquias'], 1)
        self.assertEqual(r['eventos'], 1)
        self.assertEqual(r['heridos'], 10)
        self.assertEqual(r['damnificados'], 100)


class GeneracionTest(TestCase):
    def setUp(self):
        self.evento = Evento.objects.create(
            nombre='Evento X', tipo='inundacion', fecha=_fecha(),
        )
        ZonaAfectada.objects.create(
            evento=self.evento,
            nombre='Zona Test',
            geom=Polygon([(0, 0), (0, 1), (1, 1), (1, 0), (0, 0)]),
            nivel_alerta='medio',
            fecha_inicio=_fecha(),
            damnificados=50,
        )

    def test_excel_zonas_se_genera(self):
        ruta = generar_excel_zonas_afectadas()
        self.assertIsNotNone(ruta)
        self.assertTrue(os.path.isfile(ruta))
        self.assertTrue(ruta.endswith('.xlsx'))

    def test_pdf_zonas_se_genera(self):
        ruta = generar_pdf_zonas_afectadas()
        self.assertIsNotNone(ruta)
        self.assertTrue(os.path.isfile(ruta))
        self.assertTrue(ruta.endswith('.pdf'))

    def test_excel_sin_datos_retorna_none(self):
        from .generador_reportes import generar_excel_zonas_afectadas as gen
        # Sin zonas → None
        ZonaAfectada.objects.all().delete()
        self.assertIsNone(gen())

    def test_limpiar_reportes_no_falla_si_vacio(self):
        n = limpiar_reportes_antiguos(dias=0)
        self.assertIsInstance(n, int)


class SeguridadDescargaTest(TestCase):
    """Verifica las defensas contra path traversal y extensiones."""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='staff', password='pass', is_staff=True,
        )
        self.client.force_login(self.user)

    def test_path_traversal_bloqueado(self):
        # Intento clásico
        response = self.client.get(
            '/api/reportes/descargar/../../../etc/passwd/'
        )
        # Django puede normalizar antes; probamos el endpoint con basename
        response = self.client.get(
            '/api/reportes/descargar/%2e%2e%2f%2e%2e%2fetc%2fpasswd'
        )
        # Debe ser 400 o 404, nunca 200
        self.assertIn(response.status_code, (400, 404))

    def test_extension_no_permitida_bloqueada(self):
        response = self.client.get('/api/reportes/descargar/malicioso.php/')
        self.assertEqual(response.status_code, 400)

    def test_extension_permitida_inexistente_retorna_404(self):
        response = self.client.get('/api/reportes/descargar/no_existe.pdf/')
        self.assertEqual(response.status_code, 404)

    def test_sin_login_denegado(self):
        self.client.logout()
        response = self.client.get('/api/reportes/descargar/test.pdf/')
        self.assertIn(response.status_code, (401, 403, 302))

    def test_parametros_invalidos(self):
        response = self.client.get(
            '/api/reportes/generar/?tipo=foo&contenido=bar'
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn('error', response.json())