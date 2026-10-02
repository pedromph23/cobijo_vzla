from django.contrib.auth import get_user_model
from django.core import mail
from django.test import TestCase, override_settings

from .models import RegistroAuditoria


User = get_user_model()


@override_settings(
    EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend',
    DEFAULT_FROM_EMAIL='Cobijo VZLA <no-reply@cobijo.local>',
)
class AuthenticationAuditTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='usuario_test',
            email='usuario@example.com',
            password='ClaveSegura123!',
        )

    def test_password_reset_request_is_audited(self):
        response = self.client.post(
            '/accounts/password-reset/',
            {'email': 'usuario@example.com'},
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(len(mail.outbox), 1)
        self.assertTrue(
            RegistroAuditoria.objects.filter(
                accion='PASSWORD_RESET_REQUEST',
                resultado='exitoso',
            ).exists()
        )

    def test_password_change_success_is_audited(self):
        self.client.force_login(self.user)

        response = self.client.post(
            '/accounts/password-change/',
            {
                'old_password': 'ClaveSegura123!',
                'new_password1': 'NuevaClaveSegura456!',
                'new_password2': 'NuevaClaveSegura456!',
            },
        )

        self.assertEqual(response.status_code, 302)
        self.assertTrue(
            RegistroAuditoria.objects.filter(
                usuario=self.user,
                accion='PASSWORD_CHANGE',
                resultado='exitoso',
            ).exists()
        )

    def test_password_change_invalid_is_audited_without_secret(self):
        self.client.force_login(self.user)

        response = self.client.post(
            '/accounts/password-change/',
            {
                'old_password': 'incorrecta',
                'new_password1': 'NuevaClaveSegura456!',
                'new_password2': 'NuevaClaveSegura456!',
            },
        )

        self.assertEqual(response.status_code, 200)
        registro = RegistroAuditoria.objects.filter(
            usuario=self.user,
            accion='PASSWORD_CHANGE',
            resultado='rechazado',
        ).latest('fecha')
        texto = str(registro)
        self.assertNotIn('NuevaClaveSegura456!', texto)
        self.assertNotIn('incorrecta', texto)
