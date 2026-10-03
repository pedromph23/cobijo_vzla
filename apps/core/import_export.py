"""
Servicios centralizados de importación y exportación JSON.

Características:
- Exportación segura de modelos permitidos.
- Importación JSON con validación estricta.
- Soporte para ForeignKey por ID u objeto {"id": ...}.
- Soporte para geometrías GeoJSON.
- Modos "crear" y "actualizar".
- Importaciones completamente atómicas.
- Límite máximo de registros.
- Auditoría de operaciones exitosas y fallidas.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from datetime import date, datetime, time
from decimal import Decimal
from typing import Any

from django.apps import apps
from django.contrib.gis.geos import GEOSGeometry
from django.core.exceptions import ValidationError
from django.db import models, transaction
from django.utils import timezone

from .audit import registrar_auditoria


logger = logging.getLogger(__name__)


# ============================================================
# CONFIGURACIÓN
# ============================================================

MAX_REGISTROS_IMPORTACION = 5000
MAX_REGISTROS_EXPORTACION = 5000


# Modelos que pueden participar en importación/exportación.
#
# IMPORTANTE:
# "auditlog" NO está incluido.
#
MODELOS_PERMITIDOS = {
    "estado": "core.Estado",
    "parroquia": "core.Parroquia",
    "puntodemanda": "core.PuntoDemanda",
    "sitiocandidato": "core.SitioCandidato",
    "refugioexistente": "core.RefugioExistente",
    "zonaafectada": "core.ZonaAfectada",
    "parametrosmodelo": "core.ParametrosModelo",
    "resultadooptimizacion": "core.ResultadoOptimizacion",
}


# Campos que pueden viajar en JSON pero no representan un campo
# editable normal del modelo.
CAMPOS_CONTROL = {
    "id",
}


# ============================================================
# RESULTADO
# ============================================================

@dataclass
class ResultadoImportacion:
    """
    Resultado de una importación JSON.
    """

    total: int = 0
    creados: int = 0
    actualizados: int = 0
    omitidos: int = 0


# ============================================================
# RESOLUCIÓN DE MODELOS
# ============================================================

def _normalizar_nombre_modelo(nombre: Any) -> str:
    """
    Normaliza el nombre lógico del modelo.
    """

    if not isinstance(nombre, str):
        raise ValueError("El modelo debe ser una cadena.")

    return nombre.strip().lower()


def _obtener_modelo(nombre_modelo: str):
    """
    Obtiene la clase Django asociada a un modelo permitido.
    """

    nombre = _normalizar_nombre_modelo(nombre_modelo)

    ruta = MODELOS_PERMITIDOS.get(nombre)

    if not ruta:
        raise ValueError(
            f"Modelo no permitido para importación/exportación: {nombre_modelo}"
        )

    try:
        return apps.get_model(ruta)
    except LookupError as exc:
        raise ValueError(
            f"No se pudo resolver el modelo configurado: {ruta}"
        ) from exc


# ============================================================
# UTILIDADES
# ============================================================

def _es_fk(field) -> bool:
    """
    Indica si un campo es una ForeignKey.
    """

    return isinstance(field, models.ForeignKey)


def _es_geometry_field(field) -> bool:
    """
    Detecta campos GIS.
    """

    return (
        getattr(field, "geom_type", None) is not None
        or field.__class__.__name__.lower().endswith("geometryfield")
    )


def _valor_a_json(valor: Any) -> Any:
    """
    Convierte valores Python/Django a estructuras JSON serializables.
    """

    if valor is None:
        return None

    if isinstance(valor, (str, int, float, bool)):
        return valor

    if isinstance(valor, Decimal):
        return str(valor)

    if isinstance(valor, datetime):
        return valor.isoformat()

    if isinstance(valor, date):
        return valor.isoformat()

    if isinstance(valor, time):
        return valor.isoformat()

    if isinstance(valor, GEOSGeometry):
        try:
            return json.loads(valor.geojson)
        except Exception:
            return valor.wkt

    if isinstance(valor, dict):
        return {
            str(k): _valor_a_json(v)
            for k, v in valor.items()
        }

    if isinstance(valor, (list, tuple, set)):
        return [
            _valor_a_json(v)
            for v in valor
        ]

    return str(valor)


# ============================================================
# GEOMETRÍAS
# ============================================================

def _convertir_geometria(valor: Any) -> GEOSGeometry:
    """
    Convierte GeoJSON/WKT a GEOSGeometry.

    Acepta:
        {
            "type": "Point",
            "coordinates": [-66.9036, 10.4806]
        }

    o una cadena JSON equivalente.

    También acepta WKT.
    """

    if isinstance(valor, GEOSGeometry):
        geometria = valor.clone()

    elif isinstance(valor, dict):
        try:
            geometria = GEOSGeometry(
                json.dumps(valor)
            )
        except Exception as exc:
            raise ValueError(
                f"Geometría GeoJSON inválida: {exc}"
            ) from exc

    elif isinstance(valor, str):
        texto = valor.strip()

        if not texto:
            raise ValueError(
                "La geometría no puede estar vacía."
            )

        try:
            # Primero intentamos JSON / GeoJSON.
            if texto.startswith("{"):
                geometria = GEOSGeometry(texto)
            else:
                # Luego WKT.
                geometria = GEOSGeometry(texto)

        except Exception as exc:
            raise ValueError(
                f"Geometría inválida: {exc}"
            ) from exc

    else:
        raise ValueError(
            "El valor de geometría debe ser un objeto GeoJSON, "
            "una cadena JSON/WKT o una GEOSGeometry."
        )

    if geometria.srid is None:
        geometria.srid = 4326

    return geometria


# ============================================================
# FOREIGN KEY
# ============================================================

def _resolver_foreign_key(field, valor: Any):
    """
    Resuelve una ForeignKey.

    Formatos aceptados:

        "estado": 5

    o:

        "estado": {
            "id": 5
        }
    """

    modelo_relacionado = field.remote_field.model
    nombre_campo = field.name

    if valor is None:
        if getattr(field, "null", False):
            return None

        raise ValueError(
            f"La relación '{nombre_campo}' no puede ser nula."
        )

    # --------------------------------------------------------
    # Formato objeto
    # --------------------------------------------------------

    if isinstance(valor, dict):

        if "id" not in valor:
            raise ValueError(
                f"La relación '{nombre_campo}' debe contener 'id'."
            )

        valor = valor["id"]

    # --------------------------------------------------------
    # Validación del ID
    # --------------------------------------------------------

    try:
        pk = int(valor)
    except (TypeError, ValueError) as exc:
        raise ValueError(
            f"El ID de la relación '{nombre_campo}' no es válido: {valor!r}."
        ) from exc

    try:
        return modelo_relacionado.objects.get(
            pk=pk
        )

    except modelo_relacionado.DoesNotExist as exc:
        raise ValueError(
            f"No existe {modelo_relacionado.__name__} con id={pk}."
        ) from exc


# ============================================================
# CONVERSIÓN DE VALORES
# ============================================================

def _convertir_valor(field, valor: Any):
    """
    Convierte un valor JSON al tipo esperado por Django.
    """

    if valor is None:
        return None

    # ForeignKey
    if _es_fk(field):
        return _resolver_foreign_key(
            field,
            valor,
        )

    # Geometría
    if _es_geometry_field(field):
        return _convertir_geometria(
            valor,
        )

    # JSONField
    if isinstance(field, models.JSONField):
        return valor

    # DateTimeField
    if isinstance(field, models.DateTimeField):

        if isinstance(valor, datetime):
            resultado = valor
        elif isinstance(valor, str):
            try:
                resultado = datetime.fromisoformat(
                    valor.replace("Z", "+00:00")
                )
            except ValueError as exc:
                raise ValueError(
                    f"Fecha/hora inválida: {valor!r}."
                ) from exc
        else:
            raise ValueError(
                f"Valor inválido para DateTimeField: {valor!r}."
            )

        if timezone.is_naive(resultado):
            resultado = timezone.make_aware(
                resultado,
                timezone.get_current_timezone(),
            )

        return resultado

    # DateField
    if isinstance(field, models.DateField):
        if isinstance(valor, date):
            return valor

        if isinstance(valor, str):
            try:
                return date.fromisoformat(valor)
            except ValueError as exc:
                raise ValueError(
                    f"Fecha inválida: {valor!r}."
                ) from exc

        raise ValueError(
            f"Valor inválido para DateField: {valor!r}."
        )

    # TimeField
    if isinstance(field, models.TimeField):
        if isinstance(valor, time):
            return valor

        if isinstance(valor, str):
            try:
                return time.fromisoformat(valor)
            except ValueError as exc:
                raise ValueError(
                    f"Hora inválida: {valor!r}."
                ) from exc

        raise ValueError(
            f"Valor inválido para TimeField: {valor!r}."
        )

    # Decimal
    if isinstance(field, models.DecimalField):
        try:
            return Decimal(str(valor))
        except Exception as exc:
            raise ValueError(
                f"Valor decimal inválido: {valor!r}."
            ) from exc

    # Integer
    if isinstance(
        field,
        (
            models.IntegerField,
            models.BigIntegerField,
            models.SmallIntegerField,
            models.PositiveIntegerField,
            models.PositiveSmallIntegerField,
        ),
    ):
        try:
            return int(valor)
        except (TypeError, ValueError) as exc:
            raise ValueError(
                f"Valor entero inválido: {valor!r}."
            ) from exc

    # Float
    if isinstance(
        field,
        (
            models.FloatField,
        ),
    ):
        try:
            return float(valor)
        except (TypeError, ValueError) as exc:
            raise ValueError(
                f"Valor decimal inválido: {valor!r}."
            ) from exc

    # Boolean
    if isinstance(field, models.BooleanField):

        if isinstance(valor, bool):
            return valor

        if isinstance(valor, str):
            texto = valor.strip().lower()

            if texto in {
                "true",
                "1",
                "si",
                "sí",
                "yes",
            }:
                return True

            if texto in {
                "false",
                "0",
                "no",
            }:
                return False

        if isinstance(valor, int):
            return bool(valor)

        raise ValueError(
            f"Valor booleano inválido: {valor!r}."
        )

    # Texto
    if isinstance(
        field,
        (
            models.CharField,
            models.TextField,
            models.EmailField,
            models.URLField,
        ),
    ):
        return str(valor)

    return valor


# ============================================================
# NORMALIZACIÓN DE REGISTROS
# ============================================================

def _normalizar_registro(modelo, registro: Any) -> dict[str, Any]:
    """
    Valida y transforma un registro JSON.

    IMPORTANTE:
    El campo "id" es permitido como metadato de importación,
    pero NO se pasa como campo editable al modelo.

    Esto corrige el problema donde una exportación contenía:

        {
            "id": 1,
            "nombre": "...",
            ...
        }

    y el importador rechazaba "id".
    """

    if not isinstance(registro, dict):
        raise ValidationError(
            "Cada registro debe ser un objeto JSON."
        )

    # Campos reales del modelo.
    campos_modelo = {
        field.name: field
        for field in modelo._meta.concrete_fields
    }

    # "id" puede ser utilizado como identificador de importación.
    campos_permitidos = (
        set(campos_modelo.keys())
        | CAMPOS_CONTROL
    )

    for nombre in registro.keys():

        if nombre not in campos_permitidos:
            raise ValidationError(
                f"Campo no permitido para "
                f"{modelo.__name__}: {nombre}"
            )

    datos_modelo = {}

    for nombre, valor in registro.items():

        # ----------------------------------------------------
        # ID:
        # Se acepta, pero no se manda al constructor/save.
        # ----------------------------------------------------

        if nombre in CAMPOS_CONTROL:
            continue

        field = campos_modelo[nombre]

        try:
            datos_modelo[nombre] = _convertir_valor(
                field,
                valor,
            )

        except (ValueError, TypeError, ValidationError) as exc:

            raise ValidationError(
                [
                    f"Error procesando el campo "
                    f"'{nombre}': {exc}"
                ]
            ) from exc

    return datos_modelo


# ============================================================
# ID DEL REGISTRO
# ============================================================

def _obtener_id_registro(registro: dict[str, Any]):
    """
    Obtiene el ID del registro si fue suministrado.
    """

    if "id" not in registro:
        return None

    valor = registro["id"]

    if valor in (None, ""):
        return None

    try:
        return int(valor)
    except (TypeError, ValueError) as exc:
        raise ValidationError(
            [
                f"El campo 'id' debe ser un entero. "
                f"Valor recibido: {valor!r}."
            ]
        ) from exc


# ============================================================
# IMPORTACIÓN
# ============================================================

def importar_json(
    payload: dict[str, Any],
    *,
    modo: str = "crear",
    max_registros: int = MAX_REGISTROS_IMPORTACION,
) -> ResultadoImportacion:
    """
    Importa registros desde JSON.

    Parámetros
    ----------
    payload:
        Estructura:

        {
            "version": 1,
            "modelo": "estado",
            "registros": [...]
        }

    modo:
        "crear" o "actualizar".

    crear:
        - ID existente -> se omite.
        - ID inexistente -> se crea.
        - Sin ID -> se crea.

    actualizar:
        - ID existente -> se actualiza.
        - ID inexistente -> se crea.
        - Sin ID -> se crea.

    La operación completa es atómica.
    """

    # --------------------------------------------------------
    # Validación del modo
    # --------------------------------------------------------

    if not isinstance(modo, str):
        raise ValueError(
            "El modo debe ser una cadena."
        )

    if modo != modo.strip():
        raise ValueError(
            "El modo no puede contener espacios al inicio o al final."
        )

    modo = modo.lower()

    if modo not in {
        "crear",
        "actualizar",
    }:
        raise ValueError(
            f"Modo de importación no válido: {modo!r}."
        )

    # --------------------------------------------------------
    # Validación general del payload
    # --------------------------------------------------------

    if not isinstance(payload, dict):
        raise ValidationError(
            "El payload debe ser un objeto JSON."
        )

    version = payload.get("version")

    if version != 1:
        raise ValidationError(
            f"Versión JSON no soportada: {version!r}."
        )

    nombre_modelo = payload.get("modelo")

    if not nombre_modelo:
        raise ValidationError(
            "El payload debe indicar el modelo."
        )

    modelo = _obtener_modelo(
        nombre_modelo
    )

    registros = payload.get(
        "registros"
    )

    if not isinstance(registros, list):
        raise ValidationError(
            "El campo 'registros' debe ser una lista."
        )

    if len(registros) > max_registros:
        raise ValidationError(
            f"La importación contiene "
            f"{len(registros)} registros, "
            f"superando el máximo permitido "
            f"de {max_registros}."
        )

    resultado = ResultadoImportacion(
        total=len(registros)
    )

    try:

        # ----------------------------------------------------
        # Todo dentro de una única transacción.
        # ----------------------------------------------------

        with transaction.atomic():

            for numero, registro in enumerate(
                registros,
                start=1,
            ):

                if not isinstance(registro, dict):
                    raise ValidationError(
                        [
                            f"Registro #{numero}: "
                            "Cada registro debe ser un objeto JSON."
                        ]
                    )

                pk = _obtener_id_registro(
                    registro
                )

                # ------------------------------------------------
                # Normalización antes de modificar la BD.
                # ------------------------------------------------

                datos = _normalizar_registro(
                    modelo,
                    registro,
                )

                # ------------------------------------------------
                # Registro con ID existente
                # ------------------------------------------------

                objeto_existente = None

                if pk is not None:
                    objeto_existente = (
                        modelo.objects.filter(
                            pk=pk
                        ).first()
                    )

                # ------------------------------------------------
                # MODO CREAR
                # ------------------------------------------------

                if modo == "crear":

                    if objeto_existente is not None:
                        resultado.omitidos += 1
                        continue

                    objeto = modelo(
                        **datos
                    )

                    objeto.full_clean()
                    objeto.save()

                    resultado.creados += 1
                    continue

                # ------------------------------------------------
                # MODO ACTUALIZAR
                # ------------------------------------------------

                if objeto_existente is not None:

                    for campo, valor in datos.items():
                        setattr(
                            objeto_existente,
                            campo,
                            valor,
                        )

                    objeto_existente.full_clean()
                    objeto_existente.save()

                    resultado.actualizados += 1

                else:

                    objeto = modelo(
                        **datos
                    )

                    objeto.full_clean()
                    objeto.save()

                    resultado.creados += 1

        # ----------------------------------------------------
        # Auditoría exitosa FUERA de la transacción.
        # ----------------------------------------------------

        registrar_auditoria(
            None,
            "IMPORT",
            modelo=modelo._meta.label_lower,
            descripcion=(
                f"Importación JSON exitosa de "
                f"{resultado.total} registros."
            ),
            datos_nuevos={
                "modelo": modelo._meta.label_lower,
                "total": resultado.total,
                "creados": resultado.creados,
                "actualizados": resultado.actualizados,
                "omitidos": resultado.omitidos,
                "modo": modo,
            },
            resultado="exitoso",
        )

        return resultado

    except Exception as exc:

        logger.exception(
            "Importación JSON fallida"
        )

        # ----------------------------------------------------
        # La transacción ya fue revertida.
        # La auditoría se registra fuera del atomic.
        # ----------------------------------------------------

        registrar_auditoria(
            None,
            "IMPORT",
            modelo=modelo._meta.label_lower,
            descripcion=(
                f"Importación JSON fallida: {exc}"
            ),
            datos_nuevos={
                "modelo": modelo._meta.label_lower,
                "total": len(registros),
                "modo": modo,
            },
            resultado="fallido",
        )

        if isinstance(
            exc,
            (ValidationError, ValueError),
        ):
            raise

        raise ValidationError(
            f"Error durante la importación: {exc}"
        ) from exc


# ============================================================
# SERIALIZACIÓN
# ============================================================

def serializar_objeto(objeto) -> dict[str, Any]:
    """
    Serializa únicamente campos persistidos concretos.

    Las ForeignKey se representan por su ID.
    """

    datos = {}

    for field in objeto._meta.concrete_fields:

        nombre = field.name

        valor = field.value_from_object(
            objeto
        )

        if _es_fk(field):

            datos[nombre] = (
                getattr(objeto, f"{nombre}_id")
            )

        else:

            datos[nombre] = _valor_a_json(
                valor
            )

    return datos


# ============================================================
# EXPORTACIÓN
# ============================================================

def exportar_modelo(
    nombre_modelo: str,
    *,
    limite: int = MAX_REGISTROS_EXPORTACION,
) -> dict[str, Any]:
    """
    Exporta registros de un modelo permitido.
    """

    modelo = _obtener_modelo(
        nombre_modelo
    )

    if limite <= 0:
        raise ValueError(
            "El límite de exportación debe ser mayor que cero."
        )

    registros = list(
        modelo.objects.all()[:limite]
    )

    datos = [
        serializar_objeto(objeto)
        for objeto in registros
    ]

    payload = {
        "version": 1,
        "modelo": modelo._meta.model_name,
        "total": len(datos),
        "registros": datos,
    }

    registrar_auditoria(
        None,
        "EXPORT",
        modelo=modelo._meta.label_lower,
        descripcion=(
            f"Exportación JSON de "
            f"{len(datos)} registros."
        ),
        datos_nuevos=payload,
        resultado="exitoso",
    )

    return payload