"""
Middleware de auditoría para acciones relevantes del sistema.

No registra cada GET de páginas o archivos estáticos para evitar ruido.
Registra mutaciones, APIs y autenticación, incluyendo su resultado HTTP.
"""
from django.utils.deprecation import MiddlewareMixin

from .audit import registrar_auditoria


class AuditoriaMiddleware(MiddlewareMixin):
    METODOS_MUTACION = {'POST', 'PUT', 'PATCH', 'DELETE'}

    def process_response(self, request, response):
        metodo = request.method
        ruta = request.path

        es_api = ruta.startswith('/api/')
        es_auth = ruta.startswith('/accounts/login') or ruta.startswith('/accounts/logout')
        es_mutacion = metodo in self.METODOS_MUTACION

        # La generación de reportes registra un evento enriquecido desde
        # apps.reportes; evitamos duplicarlo aquí.
        es_reporte_generacion = ruta == '/api/reportes/generar/'

        if (es_api or es_auth or es_mutacion) and not es_reporte_generacion:
            if response.status_code >= 500:
                resultado = 'error'
            elif response.status_code >= 400:
                resultado = 'rechazado'
            else:
                resultado = 'exitoso'

            if es_auth:
                accion = 'autenticacion'
            elif es_api:
                accion = f'api:{metodo.lower()}'
            else:
                accion = f'http:{metodo.lower()}'

            registrar_auditoria(
                request,
                accion=accion,
                resultado=resultado,
                detalle=f'HTTP {response.status_code}',
            )

        return response
