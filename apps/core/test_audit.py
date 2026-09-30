from django.contrib.auth import get_user_model
from django.test import TestCase, RequestFactory, Client

from apps.core.audit import (
    ACCION_CREATE, ACCION_LOGIN, ACCION_LOGOUT,
    registrar_auditoria, sanitizar_datos, serializar_instancia,
)
from apps.core.models import AuditLog, Estado


User = get_user_model()


class AuditLogTest(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.user = User.objects.create_user(
            username='auditor',
            email='auditor@example.com',
            password='una-clave-de-prueba',
        )

    def _request(self):
        request = self.factory.post(
            '/panel/datos/core_estado/nuevo/',
            REMOTE_ADDR='10.20.30.40',
            HTTP_USER_AGENT='CobijoTest/1.0',
        )
        request.user = self.user
        return request

    def test_sanitiza_campos_sensibles(self):
        datos = sanitizar_datos({
            'nombre': 'Ejemplo',
            'password': 'NO-DEBE-GUARDARSE',
            'token': 'NO-DEBE-GUARDARSE',
            'nested': {'secret': 'NO-DEBE-GUARDARSE', 'valor': 1},
        })
        self.assertEqual(datos['nombre'], 'Ejemplo')
        self.assertNotIn('password', datos)
        self.assertNotIn('token', datos)
        self.assertNotIn('secret', datos['nested'])
        self.assertEqual(datos['nested']['valor'], 1)

    def test_registra_evento_con_contexto(self):
        estado = Estado.objects.create(nombre='Auditoría')
        registro = registrar_auditoria(
            self._request(),
            ACCION_CREATE,
            estado,
            descripcion='Creación de Estado.',
            datos_nuevos=serializar_instancia(estado),
        )
        self.assertIsNotNone(registro)
        registro.refresh_from_db()
        self.assertEqual(registro.usuario, self.user)
        self.assertEqual(registro.accion, ACCION_CREATE)
        self.assertEqual(registro.modelo, 'core.estado')
        self.assertEqual(registro.objeto_id, str(estado.pk))
        self.assertEqual(registro.ip, '10.20.30.40')
        self.assertEqual(registro.metodo_http, 'POST')
        self.assertEqual(registro.ruta, '/panel/datos/core_estado/nuevo/')
        self.assertEqual(registro.resultado, 'exitoso')
        self.assertEqual(registro.datos_nuevos['nombre'], 'Auditoría')

    def test_no_expone_password_del_usuario(self):
        registro = registrar_auditoria(
            self._request(),
            ACCION_CREATE,
            self.user,
            datos_nuevos=serializar_instancia(self.user),
        )
        self.assertIsNotNone(registro)
        self.assertNotIn('password', registro.datos_nuevos)

    def test_login_y_logout_generan_bitacora(self):
        client = Client()
        self.assertTrue(client.login(username='auditor', password='una-clave-de-prueba'))
        self.assertTrue(AuditLog.objects.filter(accion=ACCION_LOGIN, usuario=self.user).exists())
        client.logout()
        self.assertTrue(AuditLog.objects.filter(accion=ACCION_LOGOUT, usuario=self.user).exists())
