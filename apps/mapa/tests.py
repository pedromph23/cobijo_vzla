"""
Tests del módulo `mapa`.

Verifica permisos, servicios y endpoints del panel administrativo.
"""
from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.contrib.gis.geos import Point

from apps.core.models import PuntoDemanda, RefugioExistente


User = get_user_model()


class PermisosTest(TestCase):
    """Verifica que solo los gestores accedan al panel."""

    def setUp(self):
        self.client = Client()
        self.user_normal = User.objects.create_user(
            username='normal', password='pass1234'
        )
        self.user_staff = User.objects.create_user(
            username='staff', password='pass1234', is_staff=True
        )

    def test_panel_sin_login_redirige(self):
        response = self.client.get('/panel/')
        self.assertEqual(response.status_code, 302)
        self.assertIn('/accounts/login/', response.url)

    def test_panel_usuario_normal_denegado(self):
        self.client.force_login(self.user_normal)
        response = self.client.get('/panel/')
        # Django redirige a login por user_passes_test o devuelve 403
        self.assertIn(response.status_code, (302, 403))

    def test_panel_staff_permitido(self):
        self.client.force_login(self.user_staff)
        response = self.client.get('/panel/')
        self.assertEqual(response.status_code, 200)


class ServiciosTest(TestCase):
    """Verifica que los servicios devuelvan datos coherentes."""

    def setUp(self):
        RefugioExistente.objects.create(
            nombre='Refugio Test',
            direccion='Calle 1',
            ubicacion=Point(-66.9, 10.5),
            capacidad_total=100,
            capacidad_disponible=40,
            operativo=True,
        )
        PuntoDemanda.objects.create(
            nombre='Punto Test',
            ubicacion=Point(-66.8, 10.4),
            poblacion=500,
        )

    def test_estadisticas_estructura(self):
        from apps.mapa.services import obtener_estadisticas
        stats = obtener_estadisticas()
        self.assertIn('refugios', stats)
        self.assertIn('puntos_demanda', stats)
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
            RefugioExistente.objects.create(
                nombre=f'Refugio {i}',
                direccion=f'Calle {i}',
                ubicacion=Point(-66.9 + i * 0.01, 10.5),
                capacidad_total=50,
                capacidad_disponible=25,
            )
        datos = obtener_datos_mapa(limite_por_capa=5)
        self.assertLessEqual(len(datos['refugios']), 5)


class FormsTest(TestCase):
    """Verifica que los formularios parseen correctamente."""

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
        from django import forms
        from apps.mapa.forms import _parsear_punto
        with self.assertRaises(forms.ValidationError):
            _parsear_punto('200,100')

    def test_parsear_punto_formato_invalido(self):
        from django import forms
        from apps.mapa.forms import _parsear_punto
        with self.assertRaises(forms.ValidationError):
            _parsear_punto('abc')


class APITest(TestCase):
    """Verifica que las APIs respondan correctamente."""

    def setUp(self):
        self.client = Client()

        self.user_normal = User.objects.create_user(
            username='api_normal', password='pass1234'
        )
        self.user_gestor = User.objects.create_user(
            username='api_gestor', password='pass1234'
        )
        self.user_admin_grupo = User.objects.create_user(
            username='api_admin_grupo', password='pass1234'
        )
        self.user_staff = User.objects.create_user(
            username='api_staff', password='pass1234', is_staff=True
        )
        self.user_superuser = User.objects.create_superuser(
            username='api_superuser',
            password='pass1234',
            email='super@example.com',
        )

        grupo_gestor, _ = Group.objects.get_or_create(name='Gestores')
        self.user_gestor.groups.add(grupo_gestor)

        grupo_admin, _ = Group.objects.get_or_create(name='Administradores')
        self.user_admin_grupo.groups.add(grupo_admin)

        self.admin_users = (
            self.user_staff,
            self.user_admin_grupo,
            self.user_superuser,
        )
        self.denied_users = (
            self.user_normal,
            self.user_gestor,
        )

        self.client.force_login(self.user_staff)

    def _assert_admin_api_allowed(self, method, url):
        response = getattr(self.client, method)(url, {})
        # La autorización pasa; el endpoint continúa con su validación funcional.
        self.assertEqual(response.status_code, 400)

    def test_api_estadisticas(self):
        response = self.client.get('/api/estadisticas/')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn('refugios', data)

    def test_api_datos_mapa(self):
        response = self.client.get('/api/datos-mapa/')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn('puntos_demanda', data)

    def test_api_sin_autenticar_denegado(self):
        self.client.logout()
        response = self.client.get('/api/estadisticas/')
        self.assertIn(response.status_code, (401, 403))

    def test_administradores_pueden_acceder_a_optimizacion(self):
        for user in self.admin_users:
            with self.subTest(username=user.username):
                self.client.force_login(user)
                self._assert_admin_api_allowed(
                    'post',
                    '/api/ejecutar-optimizacion/',
                )

    def test_gestor_y_usuario_normal_no_pueden_ejecutar_optimizacion(self):
        for user in self.denied_users:
            with self.subTest(username=user.username):
                self.client.force_login(user)
                response = self.client.post('/api/ejecutar-optimizacion/', {})
                self.assertEqual(response.status_code, 403)

    def test_administradores_pueden_ejecutar_comandos(self):
        for user in self.admin_users:
            with self.subTest(username=user.username):
                self.client.force_login(user)
                self._assert_admin_api_allowed(
                    'post',
                    '/api/ejecutar-comando/',
                )

    def test_gestor_y_usuario_normal_no_pueden_ejecutar_comandos(self):
        for user in self.denied_users:
            with self.subTest(username=user.username):
                self.client.force_login(user)
                response = self.client.post('/api/ejecutar-comando/', {})
                self.assertEqual(response.status_code, 403)

    def test_no_autenticado_no_puede_ejecutar_apis_criticas(self):
        self.client.logout()

        for url in (
            '/api/ejecutar-optimizacion/',
            '/api/ejecutar-comando/',
        ):
            with self.subTest(url=url):
                response = self.client.post(url, {})
                self.assertIn(response.status_code, (401, 403))
