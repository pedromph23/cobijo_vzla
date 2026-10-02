"""Validadores reutilizables para datos introducidos por usuarios."""
import re

from django.core.exceptions import ValidationError


PATRON_TEXTO_HUMANO = re.compile(r"^[^\W\d_]+(?:[ '\-][^\W\d_]+)*$", re.UNICODE)
PATRON_TELEFONO = re.compile(r"^\+?[0-9][0-9 ()\-]{6,18}[0-9]$|^\+?[0-9]{7,15}$")


def validar_texto_sin_numeros_ni_especiales(value):
    """Permite letras Unicode, espacios, apóstrofes y guiones; rechaza números y símbolos."""
    value = (value or '').strip()
    if value and not PATRON_TEXTO_HUMANO.fullmatch(value):
        raise ValidationError(
            'Use solamente letras, espacios, guiones o apóstrofes. No se permiten números ni símbolos.'
        )


def validar_telefono(value):
    """Valida teléfonos humanos sin permitir texto arbitrario."""
    value = (value or '').strip()
    if value and not PATRON_TELEFONO.fullmatch(value):
        raise ValidationError(
            'Introduzca un teléfono válido usando números y, opcionalmente, +, espacios, paréntesis o guiones.'
        )
