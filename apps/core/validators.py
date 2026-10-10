"""Validadores reutilizables para datos introducidos por usuarios."""
import re

from django.core.exceptions import ValidationError


PATRON_TEXTO_HUMANO = re.compile(r"^[^\W\d_]+(?:[ '\-][^\W\d_]+)*$", re.UNICODE)
PATRON_TELEFONO = re.compile(r"^\+?[0-9][0-9 ()\-]{6,18}[0-9]$|^\+?[0-9]{7,15}$")
PATRON_TEXTO_OPERATIVO = re.compile(r"^[\wÀ-ÿ0-9 .,;:'\-/#()°ºª%+&]+$", re.UNICODE)


def validar_texto_sin_numeros_ni_especiales(value):
    """Permite letras Unicode, espacios, apóstrofes y guiones; rechaza números y símbolos."""
    value = (value or '').strip()
    if value and not PATRON_TEXTO_HUMANO.fullmatch(value):
        raise ValidationError(
            'Use solamente letras, espacios, guiones o apóstrofes. No se permiten números ni símbolos.'
        )


def validar_texto_operativo(value):
    """Valida texto de nombres de lugares/direcciones que legítimamente puede contener números."""
    value = (value or '').strip()
    if value and not PATRON_TEXTO_OPERATIVO.fullmatch(value):
        raise ValidationError(
            'El texto contiene caracteres no permitidos. Revise la información e inténtelo nuevamente.'
        )


def validar_telefono(value):
    """Valida teléfonos humanos sin permitir texto arbitrario."""
    value = (value or '').strip()
    if value and not PATRON_TELEFONO.fullmatch(value):
        raise ValidationError(
            'Introduzca un teléfono válido usando números y, opcionalmente, +, espacios, paréntesis o guiones.'
        )


PATRON_NOMBRE_OPERATIVO = re.compile(r"^[A-Za-zÀ-ÿ0-9 .'_-]+$", re.UNICODE)
PATRON_VOCAL = re.compile(r"[aeiouáéíóúüñAEIOUÁÉÍÓÚÜÑ]", re.UNICODE)
PATRON_CONSONANTE = re.compile(r"[bcdfghjklmnñpqrstvwxyzBCDFGHJKLMNÑPQRSTVWXYZ]", re.UNICODE)


def validar_nombre_operativo(value, min_longitud=3, max_longitud=200, etiqueta='El nombre'):
    """Valida nombres de entidades operativas (estados, parroquias, refugios, eventos, etc.).

    Reglas:
    - Longitud entre min_longitud y max_longitud.
    - Solo letras (con acentos), números, espacios, puntos, guiones, guiones bajos y apóstrofes.
    - Al menos una vocal.
    - Al menos una consonante.
    - No más del 40% de caracteres pueden ser dígitos.
    """
    value = (value or '').strip()
    if not value:
        raise ValidationError(f'{etiqueta} es obligatorio.')
    if len(value) < min_longitud:
        raise ValidationError(f'{etiqueta} debe tener al menos {min_longitud} caracteres.')
    if len(value) > max_longitud:
        raise ValidationError(f'{etiqueta} no debe superar {max_longitud} caracteres.')
    if not PATRON_NOMBRE_OPERATIVO.fullmatch(value):
        raise ValidationError(
            f'{etiqueta} solo puede contener letras, números, espacios, puntos, '
            'guiones, guiones bajos y apóstrofes.'
        )
    if not PATRON_VOCAL.search(value):
        raise ValidationError(f'{etiqueta} debe contener al menos una vocal.')
    if not PATRON_CONSONANTE.search(value):
        raise ValidationError(f'{etiqueta} debe contener al menos una consonante.')
    digitos = sum(c.isdigit() for c in value)
    if digitos / len(value) >= 0.4:
        raise ValidationError(f'{etiqueta} tiene demasiados números. Añada texto descriptivo.')
    return value


def validar_imagen_real(
    archivo,
    *,
    min_ancho: int = 100,
    min_alto: int = 100,
    max_ancho: int = 10000,
    max_alto: int = 10000,
    max_bytes: int = 10 * 1024 * 1024,
):
    """Valida que un archivo subido sea una imagen real y no un archivo
    renombrado con extensión de imagen.

    Verifica:
    - Tamaño máximo (default 10 MB).
    - Contenido real es una imagen válida (usando Pillow).
    - Dimensiones mínimas y máximas razonables.

    Args:
        archivo: UploadedFile o FieldFile.
        min_ancho, min_alto: dimensiones mínimas (default 100x100).
        max_ancho, max_alto: dimensiones máximas (default 10000x10000).
        max_bytes: peso máximo en bytes (default 10 MB).

    Raises:
        ValidationError: si el archivo no cumple los requisitos.
    """
    from PIL import Image, UnidentifiedImageError

    if not archivo:
        return

    # Tamaño
    if hasattr(archivo, 'size') and archivo.size > max_bytes:
        mb = max_bytes / (1024 * 1024)
        raise ValidationError(f'El archivo no debe superar los {mb:.0f} MB.')

    # Contenido real: usar Pillow para verificar.
    try:
        # En UploadedFile el archivo puede estar en .file
        file_obj = getattr(archivo, 'file', archivo)
        # Rebobinar por si acaso
        try:
            file_obj.seek(0)
        except Exception:
            pass

        with Image.open(file_obj) as img:
            img.verify()  # consume el archivo, hay que reabrir

        try:
            file_obj.seek(0)
        except Exception:
            pass

        with Image.open(file_obj) as img:
            ancho, alto = img.size
    except (UnidentifiedImageError, Exception) as exc:
        raise ValidationError(
            'El archivo no es una imagen válida o está corrupto.'
        ) from exc

    # Dimensiones
    if ancho < min_ancho or alto < min_alto:
        raise ValidationError(
            f'La imagen es demasiado pequeña. Mínimo {min_ancho}x{min_alto} píxeles.'
        )
    if ancho > max_ancho or alto > max_alto:
        raise ValidationError(
            f'La imagen es demasiado grande. Máximo {max_ancho}x{max_alto} píxeles.'
        )
