"""Vistas de autenticación con trazabilidad de seguridad."""

from django.contrib.auth import views as auth_views

from .audit import registrar_auditoria


class PasswordChangeViewAudited(auth_views.PasswordChangeView):
    """Cambio voluntario de contraseña con auditoría sin registrar secretos."""

    def form_valid(self, form):
        response = super().form_valid(form)
        registrar_auditoria(
            self.request,
            accion='PASSWORD_CHANGE',
            detalle='El usuario cambió su contraseña correctamente.',
            modelo='User',
            objeto_id=self.request.user.pk,
        )
        return response

    def form_invalid(self, form):
        registrar_auditoria(
            self.request,
            accion='PASSWORD_CHANGE',
            resultado='rechazado',
            detalle='Intento de cambio de contraseña rechazado por validación.',
            modelo='User',
            objeto_id=self.request.user.pk,
        )
        return super().form_invalid(form)


class PasswordResetRequestView(auth_views.PasswordResetView):
    """Solicitud de recuperación sin revelar si el correo existe."""

    def form_valid(self, form):
        response = super().form_valid(form)
        registrar_auditoria(
            self.request,
            accion='PASSWORD_RESET_REQUEST',
            detalle='Se solicitó recuperación de contraseña.',
            modelo='User',
        )
        return response


class PasswordResetCompleteView(auth_views.PasswordResetCompleteView):
    """Confirma una recuperación de contraseña completada."""

    def get(self, request, *args, **kwargs):
        response = super().get(request, *args, **kwargs)
        registrar_auditoria(
            request,
            accion='PASSWORD_RESET_COMPLETED',
            detalle='Se completó una recuperación de contraseña.',
            modelo='User',
        )
        return response
