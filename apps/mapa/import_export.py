"""
Servicios centralizados de importación y exportación JSON.

Responsabilidades:
- Validar estructuras JSON.
- Importar datos de forma segura.
- Mantener transacciones atómicas.
- Resolver relaciones ForeignKey.
- Convertir geometrías GeoJSON a objetos GeoDjango.
- Exportar registros a JSON portable.
- Registrar operaciones de importación/exportación mediante auditoría.

IMPORTANTE:
AuditLog nunca forma parte de los modelos importables.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, time
from decimal import Decimal
from typing import Any

from django.contrib.gis.geos import GEOSGeometry
from django.core.exceptions import ValidationError
from django.db import models, transaction

from apps.core.audit import (
    ACCION_EXPORT,
    ACCION_IMPORT,
    registrar_auditoria,
    sanitizar_datos,
)

from apps.core.models import (
    Estado,
    Parroquia,
    PuntoDemanda,
    SitioCandidato,
    RefugioExistente,
    ZonaAfectada,
    ParametrosModelo,
)


# ============================================================
# CONFIGURACIÓN
# ============================================================

MAX_REGISTROS_IMPORTACION = 5000
MAX_REGISTROS_EXPORTACION = 10000


MODELOS_IMPORTABLES = {
    "estado": Estado,
    "parroquia": Parroquia,
    "punto_demanda": PuntoDemanda,
    "sitio_candidato": SitioCandidato,
    "refugio_existente": RefugioExistente,
    "zona_afectada": ZonaAfectada,
    "parametros_modelo": ParametrosModelo,
}


# ============================================================
# RESULTADO
# ============================================================

@dataclass
class ResultadoImportacion:
    """
    Resultado estructurado de una importación.
    """

    modelo: str = ""
    total: int = 0
    creados: int = 0
    actualizados: int = 0
    omitidos: int = 0
    errores: int = 0

    detalles: list[dict[str, Any]] = field(default_factory=list)

    @property
    def exitoso(self) -> bool:
        return self.errores == 0

    @property
    def total_procesados(self) -> int:
        return (
            self.creados
            + self.actualizados
            + self.omitidos
        )

    def agregar_error(
        self,
        indice: int,
        mensaje: str,
    ) -> None:
        """
        Registra un error asociado a un registro.
        """

        self.errores += 1

        self.detalles.append(
            {
                "registro": indice,
                "resultado": "error",
                "mensaje": str(mensaje),
            }
        )

    def agregar_resultado(
        self,
        indice: int,
        resultado: str,
        objeto=None,
    ) -> None:
        """
        Registra el resultado de procesamiento de un registro.
        """

        detalle = {
            "registro": indice,
            "resultado": resultado,
        }

        if objeto is not None:
            detalle.update(
                {
                    "id": objeto.pk,
                    "representacion": str(objeto),
                }
            )

        self.detalles.append(detalle)


# ============================================================
# VALIDACIÓN DEL MODELO
# ============================================================

def obtener_modelo_importable(nombre: str):
    """
    Devuelve el modelo correspondiente a una clave permitida.

    Nunca permite importar modelos arbitrarios.
    """

    clave = str(nombre or "").strip().lower()

    modelo = MODELOS_IMPORTABLES.get(clave)

    if modelo is None:
        raise ValueError(
            f"Modelo no permitido para importación: {nombre}"
        )

    return modelo


# ============================================================
# CONVERSIÓN DE VALORES
# ============================================================

def _convertir_valor(field, valor):
    """
    Convierte valores JSON al tipo esperado por Django.
    """

    if valor is None:
        return None

    # --------------------------------------------------------
    # ForeignKey
    # --------------------------------------------------------

    if isinstance(field, models.ForeignKey):
        return _resolver_foreign_key(field, valor)

    # --------------------------------------------------------
    # Geometrías GeoDjango
    # --------------------------------------------------------

    if isinstance(field, models.GeometryField):
        return _convertir_geometria(valor)

    # --------------------------------------------------------
    # DateTime
    # --------------------------------------------------------

    if isinstance(field, models.DateTimeField):
        if isinstance(valor, datetime):
            return valor

        return datetime.fromisoformat(
            str(valor).replace("Z", "+00:00")
        )

    # --------------------------------------------------------
    # Date
    # --------------------------------------------------------

    if isinstance(field, models.DateField):
        if isinstance(valor, date):
            return valor

        return date.fromisoformat(str(valor))

    # --------------------------------------------------------
    # Time
    # --------------------------------------------------------

    if isinstance(field, models.TimeField):
        if isinstance(valor, time):
            return valor

        return time.fromisoformat(str(valor))

    # --------------------------------------------------------
    # Decimal
    # --------------------------------------------------------

    if isinstance(field, models.DecimalField):
        return Decimal(str(valor))

    return valor


def _convertir_geometria(valor):
    """
    Convierte una geometría GeoJSON a GEOSGeometry.

    Acepta:

    1. Diccionario GeoJSON:

        {
            "type": "Point",
            "coordinates": [-66.90, 10.48]
        }

    2. Cadena JSON con GeoJSON.

    La geometría resultante se normaliza a SRID 4326.
    """

    if isinstance(valor, dict):
        import json

        valor = json.dumps(
            valor,
            ensure_ascii=False,
        )

    if not isinstance(valor, str):
        raise ValueError(
            "La geometría debe ser un objeto GeoJSON "
            "o una cadena JSON."
        )

    try:
        geometria = GEOSGeometry(valor)
    except Exception as exc:
        raise ValueError(
            f"GeoJSON inválido: {exc}"
        ) from exc

    if geometria.srid is None:
        geometria.srid = 4326

    elif geometria.srid != 4326:
        try:
            geometria.transform(4326)
        except Exception as exc:
            raise ValueError(
                f"No se pudo transformar la geometría "
                f"a SRID 4326: {exc}"
            ) from exc

    return geometria


# ============================================================
# RELACIONES
# ============================================================

def _resolver_foreign_key(field, valor):
    """
    Resuelve una relación ForeignKey.

    Por defecto acepta el PK:

        "estado": 1

    También acepta:

        "estado": {
            "id": 1
        }
    """

    modelo_relacionado = field.remote_field.model

    if isinstance(valor, dict):

        if "id" not in valor:
            raise ValueError(
                f"La relación '{field.name}' "
                f"debe contener 'id'."
            )

        valor = valor["id"]

    if valor in (None, ""):
        if field.null:
            return None

        raise ValueError(
            f"La relación '{field.name}' "
            f"no puede ser nula."
        )

    try:
        return modelo_relacionado.objects.get(
            pk=valor
        )

    except modelo_relacionado.DoesNotExist as exc:
        raise ValueError(
            f"No existe {modelo_relacionado.__name__} "
            f"con id={valor}."
        ) from exc

    except (TypeError, ValueError) as exc:
        raise ValueError(
            f"ID inválido para la relación "
            f"'{field.name}': {valor}"
        ) from exc


# ============================================================
# CAMPOS IMPORTABLES
# ============================================================

def _obtener_campos_importables(Model):
    """
    Devuelve únicamente campos concretos persistibles.

    Excluye:
    - campos automáticos;
    - auto_now;
    - auto_now_add;
    - relaciones reversas;
    - propiedades;
    - campos no concretos.
    """

    campos = {}

    for field in Model._meta.concrete_fields:

        if field.auto_created:
            continue

        if getattr(field, "auto_now", False):
            continue

        if getattr(field, "auto_now_add", False):
            continue

        campos[field.name] = field

    return campos


# ============================================================
# NORMALIZACIÓN DEL REGISTRO
# ============================================================

def _normalizar_registro(Model, datos):
    """
    Valida y convierte un registro individual.
    """

    if not isinstance(datos, dict):
        raise ValidationError(
            "Cada registro debe ser un objeto JSON."
        )

    campos = _obtener_campos_importables(Model)

    datos_modelo = {}

    for nombre, valor in datos.items():

        if nombre not in campos:
            raise ValidationError(
                f"Campo no permitido para "
                f"{Model.__name__}: {nombre}"
            )

        field = campos[nombre]

        try:
            datos_modelo[nombre] = _convertir_valor(
                field,
                valor,
            )

        except Exception as exc:
            raise ValidationError(
                f"Error procesando el campo "
                f"'{nombre}': {exc}"
            ) from exc

    return datos_modelo


# ============================================================
# IDENTIFICACIÓN DEL REGISTRO
# ============================================================

def _obtener_instancia_existente(Model, datos):
    """
    Busca una instancia existente utilizando el PK.

    Si el JSON no contiene PK, se considera
    un registro nuevo.
    """

    pk_field = Model._meta.pk
    pk_name = pk_field.name

    pk = datos.get(pk_name)

    if pk in (None, ""):
        return None

    try:
        return Model.objects.filter(
            pk=pk
        ).first()

    except (TypeError, ValueError) as exc:
        raise ValidationError(
            f"ID inválido: {pk}"
        ) from exc


# ============================================================
# IMPORTACIÓN
# ============================================================

def importar_json(
    payload: Any,
    *,
    request=None,
    modo: str = "crear",
    usuario=None,
    max_registros: int = MAX_REGISTROS_IMPORTACION,
) -> ResultadoImportacion:
    """
    Importa datos desde una estructura JSON.

    Formato esperado:

    {
        "modelo": "estado",
        "version": 1,
        "registros": [
            {
                "nombre": "Miranda",
                "codigo_ine": "15"
            }
        ]
    }

    Modos:

    crear:
        Solo crea registros nuevos.

    actualizar:
        Crea registros nuevos y actualiza aquellos
        que tengan un PK existente.

    La operación completa es atómica.
    """

    # --------------------------------------------------------
    # VALIDACIÓN DEL PAYLOAD
    # --------------------------------------------------------

    if not isinstance(payload, dict):
        raise ValidationError(
            "El archivo JSON debe contener un objeto."
        )

    modelo_nombre = str(
        payload.get("modelo") or ""
    ).strip().lower()

    if not modelo_nombre:
        raise ValidationError(
            "El campo 'modelo' es obligatorio."
        )

    Model = obtener_modelo_importable(
        modelo_nombre
    )

    registros = payload.get("registros")

    if not isinstance(registros, list):
        raise ValidationError(
            "El campo 'registros' debe ser una lista."
        )

    if not registros:
        raise ValidationError(
            "El archivo no contiene registros."
        )

    if max_registros <= 0:
        raise ValidationError(
            "El límite de registros debe ser mayor que cero."
        )

    if len(registros) > max_registros:
        raise ValidationError(
            f"La importación supera el límite de "
            f"{max_registros} registros."
        )

    modo = str(
        modo or "crear"
    ).strip().lower()

    if modo not in {
        "crear",
        "actualizar",
    }:
        raise ValueError(
            "El modo debe ser "
            "'crear' o 'actualizar'."
        )

    resultado = ResultadoImportacion(
        modelo=modelo_nombre,
        total=len(registros),
    )

    # --------------------------------------------------------
    # IMPORTACIÓN ATÓMICA
    # --------------------------------------------------------

    try:

        with transaction.atomic():

            for indice, registro in enumerate(
                registros,
                start=1,
            ):

                try:
                    datos = _normalizar_registro(
                        Model,
                        registro,
                    )

                    instancia = _obtener_instancia_existente(
                        Model,
                        datos,
                    )

                    # --------------------------------------------
                    # CREACIÓN
                    # --------------------------------------------

                    if instancia is None:

                        datos = dict(datos)

                        # Nunca forzamos manualmente el PK
                        # cuando el registro no existe.
                        pk_name = Model._meta.pk.name
                        datos.pop(pk_name, None)

                        objeto = Model(**datos)

                        objeto.full_clean()
                        objeto.save()

                        resultado.creados += 1

                        resultado.agregar_resultado(
                            indice,
                            "creado",
                            objeto,
                        )

                        continue

                    # --------------------------------------------
                    # EXISTENTE + MODO CREAR
                    # --------------------------------------------

                    if modo == "crear":

                        resultado.omitidos += 1

                        resultado.agregar_resultado(
                            indice,
                            "omitido",
                            instancia,
                        )

                        continue

                    # --------------------------------------------
                    # ACTUALIZACIÓN
                    # --------------------------------------------

                    pk_name = Model._meta.pk.name

                    instancia_datos = {
                        key: value
                        for key, value in datos.items()
                        if key != pk_name
                    }

                    for nombre, valor in instancia_datos.items():
                        setattr(
                            instancia,
                            nombre,
                            valor,
                        )

                    instancia.full_clean()
                    instancia.save()

                    resultado.actualizados += 1

                    resultado.agregar_resultado(
                        indice,
                        "actualizado",
                        instancia,
                    )

                except Exception as exc:

                    # La importación es atómica.
                    # Por tanto, cualquier error aborta
                    # toda la operación.

                    resultado.agregar_error(
                        indice,
                        str(exc),
                    )

                    raise

        # --------------------------------------------------------
        # AUDITORÍA EXITOSA
        # --------------------------------------------------------

        registrar_auditoria(
            request=request,
            usuario=usuario,
            accion=ACCION_IMPORT,
            modelo=Model._meta.label_lower,
            descripcion=(
                f"Importación JSON de "
                f"{Model._meta.verbose_name_plural}"
            ),
            datos_nuevos={
                "modelo": modelo_nombre,
                "modo": modo,
                "total": resultado.total,
                "creados": resultado.creados,
                "actualizados": resultado.actualizados,
                "omitidos": resultado.omitidos,
                "errores": resultado.errores,
            },
            resultado="exitoso",
        )

        return resultado

    except Exception as exc:

        # --------------------------------------------------------
        # AUDITORÍA FALLIDA
        # --------------------------------------------------------

        registrar_auditoria(
            request=request,
            usuario=usuario,
            accion=ACCION_IMPORT,
            modelo=Model._meta.label_lower,
            descripcion=(
                f"Importación JSON fallida de "
                f"{Model._meta.verbose_name_plural}"
            ),
            datos_nuevos={
                "modelo": modelo_nombre,
                "modo": modo,
                "total": resultado.total,
                "creados": resultado.creados,
                "actualizados": resultado.actualizados,
                "omitidos": resultado.omitidos,
                "errores": resultado.errores,
                "error": str(exc),
            },
            resultado="fallido",
        )

        raise


# ============================================================
# SERIALIZACIÓN
# ============================================================

def _serializar_valor(field, valor):
    """
    Convierte valores Django a formatos JSON.
    """

    if valor is None:
        return None

    if isinstance(field, models.GeometryField):
        return valor.geojson

    if isinstance(valor, Decimal):
        return str(valor)

    if isinstance(valor, datetime):
        return valor.isoformat()

    if isinstance(valor, date):
        return valor.isoformat()

    if isinstance(valor, time):
        return valor.isoformat()

    return valor


def serializar_objeto(
    objeto,
) -> dict[str, Any]:
    """
    Serializa una instancia Django a un
    diccionario JSON seguro.
    """

    datos = {}

    for field in objeto._meta.concrete_fields:

        nombre = field.name
        valor = field.value_from_object(objeto)

        # --------------------------------------------------------
        # ForeignKey
        # --------------------------------------------------------

        if isinstance(field, models.ForeignKey):

            datos[nombre] = (
                getattr(
                    objeto,
                    field.name,
                ).pk
                if valor is not None
                else None
            )

            continue

        # --------------------------------------------------------
        # Otros campos
        # --------------------------------------------------------

        datos[nombre] = sanitizar_datos(
            _serializar_valor(
                field,
                valor,
            )
        )

    return datos


# ============================================================
# EXPORTACIÓN
# ============================================================

def exportar_modelo(
    modelo_nombre: str,
    *,
    queryset=None,
    request=None,
    usuario=None,
    limite: int | None = None,
) -> dict[str, Any]:
    """
    Exporta registros de un modelo permitido.

    Devuelve una estructura JSON serializable.
    """

    Model = obtener_modelo_importable(
        modelo_nombre
    )

    # --------------------------------------------------------
    # Queryset
    # --------------------------------------------------------

    if queryset is None:
        queryset = Model.objects.all()

    # --------------------------------------------------------
    # Límite de seguridad
    # --------------------------------------------------------

    if limite is None:
        limite = MAX_REGISTROS_EXPORTACION

    if limite <= 0:
        raise ValueError(
            "El límite de exportación debe ser "
            "mayor que cero."
        )

    queryset = queryset[:limite]

    # --------------------------------------------------------
    # Serialización
    # --------------------------------------------------------

    registros = [
        serializar_objeto(objeto)
        for objeto in queryset
    ]

    payload = {
        "version": 1,
        "modelo": modelo_nombre,
        "total": len(registros),
        "registros": registros,
    }

    # --------------------------------------------------------
    # Auditoría
    # --------------------------------------------------------

    registrar_auditoria(
        request=request,
        usuario=usuario,
        accion=ACCION_EXPORT,
        modelo=Model._meta.label_lower,
        descripcion=(
            f"Exportación JSON de "
            f"{Model._meta.verbose_name_plural}"
        ),
        datos_nuevos={
            "modelo": modelo_nombre,
            "total": len(registros),
        },
        resultado="exitoso",
    )

    return payload
