"""Señales para conservar instantáneas históricas de entidades operativas."""
from django.db.models.signals import post_delete, post_save, pre_delete
from django.dispatch import receiver

from .history import registrar_version, serializar_instancia
from apps.emergencias.models import Evento\n\nfrom .models import (
    PuntoDemanda, SitioCandidato, RefugioExistente, ZonaAfectada,
    ParametrosModelo, RegistroVersion,
)

MODELOS = (PuntoDemanda, SitioCandidato, RefugioExistente, ZonaAfectada, ParametrosModelo, Evento)

def _request(instance):
    return getattr(instance, "_audit_request", None)

@receiver(post_save)
def registrar_guardado(sender, instance, created, **kwargs):
    if sender not in MODELOS or isinstance(instance, RegistroVersion):
        return
    registrar_version(_request(instance), instance, "creado" if created else "actualizado")

@receiver(pre_delete)
def preparar_eliminacion(sender, instance, **kwargs):
    if sender not in MODELOS or isinstance(instance, RegistroVersion):
        return
    instance._historial_eliminado = serializar_instancia(instance)

@receiver(post_delete)
def registrar_eliminacion(sender, instance, **kwargs):
    if sender not in MODELOS or isinstance(instance, RegistroVersion):
        return
    registrar_version(_request(instance), instance, "eliminado", getattr(instance, "_historial_eliminado", None))
