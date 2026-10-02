"""Tests del módulo mapa."""
from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.contrib.gis.geos import Point
from django.core.exceptions import ValidationError

from apps.core.models import PuntoDemanda, RefugioExistente
from apps.mapa.forms import PuntoDemandaForm, SitioCandidatoForm, RefugioExistenteForm, ZonaAfectadaForm

User = get_user_model()


class PermisosTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user_normal = User.objects.create_user(username='normal', password='pass1234')
        self.user_staff = User.objects.create_user(username='staff', password='pass1234', is_staff=True)

    def test_panel_sin_login_redirige(self):
        response = self.client.get('/panel/')
        self.assertEqual(response.status_code, 302)
        self.assertIn('/accounts/login/', response.url)

    def test_panel_usuario_normal_denegado(self):
        self.client.force_login(self.user_normal)
        response = self.client.get('/panel/')
        self.assertIn(response.status_code, (302, 403))

    def test_panel_staff_permitido(self):
        self.client.force_login(self.user_staff)
        response = self.client.get('/panel/')
        self.assertEqual(response.status_code, 200)


class ServiciosTest(TestCase):
    def setUp(self):
        RefugioExistente.objects.create(nombre='Refugio Test', direccion='Calle 1', ubicacion=Point(-66.9, 10.5), capacidad_total=100, capacidad_disponible=40, operativo=True)
        PuntoDemanda.objects.create(nombre='Punto Test', ubicacion=Point(-66.8, 10.4), poblacion=500)

    def test_estadisticas_estructura(self):
        from apps.mapa.services import obtener_estadisticas
        stats = obtener_estadisticas()
        self.assertEqual(stats['refugios'], 1)
        self.assertEqual(stats['puntos_demanda'], 1)

    def test_datos_mapa_estructura(self):
        from apps.mapa.services import obtener_datos_mapa
        datos = obtener_datos_mapa(limite_por_capa=10)
        self.assertIn('puntos_demanda', datos)
        self.assertIn('refugios', datos)
        self.assertIn('sitios_candidatos', datos)
        self.assertIn('zonas_afectadas', datos)
        self.assertEqual(len(datos['refugios']), 1)

    def test_datos_mapa_respeta_limite(self):
        from apps.mapa.services import obtener_datos_mapa
        for i in range(20):
            RefugioExistente.objects.create(nombre=f'Refugio {i}', direccion=f'Calle {i}', ubicacion=Point(-66.9 + i * 0.01, 10.5), capacidad_total=50, capacidad_disponible=25)
        datos = obtener_datos_mapa(limite_por_capa=5)
        self.assertLessEqual(len(datos['refugios']), 5)


class FormsTest(TestCase):
    def test_parsear_punto_valido(self):
        from apps.mapa.forms import _parsear_punto
        p = _parsear_punto('-66.9036,10.4806')
        self.assertAlmostEqual(p.x, -66.9036, places=4)
        self.assertAlmostEqual(p.y, 10.4806, places=4)

    def test_parsear_punto_con_espacio(self):
        from apps.mapa.forms import _parsear_punto
        p = _parsear_punto('-66.9036 10.4806')
        self.assertAlmostEqual(p.x, -66.9036, places=4)

    def test_parsear_punto_fuera_de_rango(self):
        from apps.mapa.forms import _parsear_punto
        with self.assertRaises(Exception):
            _parsear_punto('200,100')

    def test_parsear_punto_formato_invalido(self):
        from apps.mapa.forms import _parsear_punto
        with self.assertRaises(Exception):
            _parsear_punto('abc')

    def test_nombre_no_acepta_numeros(self):
        form = PuntoDemandaForm(data={'nombre': 'Sector 23', 'ubicacion': '-66.9,10.5', 'poblacion': 10, 'vulnerabilidad': 0.5, 'descripcion': ''})
        self.assertFalse(form.is_valid())
        self.assertIn('nombre', form.errors)

    def test_nombre_acepta_acentos(self):
        form = PuntoDemandaForm(data={'nombre': 'José Pérez', 'ubicacion': '-66.9,10.5', 'poblacion': 10, 'vulnerabilidad': 0.5, 'descripcion': ''})
        self.assertNotIn('nombre', form.errors)

    def test_telefono_rechaza_letras(self):
        form = RefugioExistenteForm(data={'nombre': 'Refugio Central', 'direccion': 'Calle Central', 'ubicacion': '-66.9,10.5', 'capacidad_total': 10, 'capacidad_disponible': 5, 'servicios': '', 'operativo': True, 'telefono': 'abc123', 'horario': ''})
        self.assertFalse(form.is_valid())
        self.assertIn('telefono', form.errors)

    def test_capacidad_disponible_no_supera_total(self):
        form = RefugioExistenteForm(data={'nombre': 'Refugio Central', 'direccion': 'Calle Central', 'ubicacion': '-66.9,10.5', 'capacidad_total': 10, 'capacidad_disponible': 20, 'servicios': '', 'operativo': True, 'telefono': '', 'horario': ''})
        self.assertFalse(form.is_valid())
        self.assertIn('capacidad_disponible', form.errors)


class APITest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='api', password='pass1234', is_staff=True)
        self.client.force_login(self.user)

    def test_api_estadisticas(self):
        response = self.client.get('/api/estadisticas/')
        self.assertEqual(response.status_code, 200)
        self.assertIn('refugios', response.json())

    def test_api_datos_mapa(self):
        response = self.client.get('/api/datos-mapa/')
        self.assertEqual(response.status_code, 200)
        self.assertIn('puntos_demanda', response.json())

    def test_api_sin_autenticar_denegado(self):
        self.client.logout()
        response = self.client.get('/api/estadisticas/')
        self.assertIn(response.status_code, (401, 403))
