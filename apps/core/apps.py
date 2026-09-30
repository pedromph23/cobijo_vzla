from django.apps import AppConfig


class CoreConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.core'
    verbose_name = 'Núcleo del sistema'

    def ready(self):
        from . import audit  # noqa: F401,E402
