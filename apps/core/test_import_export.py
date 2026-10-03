"""
Pruebas completas para importación y exportación JSON.

Cobertura:
- Validación del payload.
- Importación en modo crear.
- Importación en modo actualizar.
- IDs existentes.
- IDs incluidos en exportaciones.
- ForeignKey.
- Atomicidad.
- Límites de seguridad.
- Serialización.
- Exportación.
- Exportación + importación.
- Geometrías GeoJSON.
- Validación del modo.
- Auditoría.
"""

from unittest.mock import patch

from django.core.exceptions import ValidationError
from django.test import TestCase

from django.contrib.gis.geos import GEOSGeometry

from apps.core.models import (
    Estado,
    Parroquia,
    PuntoDemanda,
)

from apps.core.import_export import (
    MAX_REGISTROS_IMPORTACION,
    importar_json,
    exportar_modelo,
    serializar_objeto,
)


# ============================================================
# BASE
# ============================================================


class ImportExportBaseTestCase(TestCase):
    """
    Clase base para las pruebas de importación/exportación.
    """

    def crear_estado(
        self,
        nombre="Estado de prueba",
        codigo_ine="TEST-001",
        **kwargs,
    ):
        """
        Crea un Estado utilizando únicamente valores compatibles
        con el modelo.

        codigo_ine tiene máximo 10 caracteres según el modelo.
        """
        return Estado.objects.create(
            nombre=nombre,
            codigo_ine=codigo_ine,
            **kwargs,
        )

    def crear_parroquia(
        self,
        estado,
        nombre="Parroquia de prueba",
        codigo_ine="PAR-001",
        **kwargs,
    ):
        """
        Crea una Parroquia asociada a un Estado.
        """
        return Parroquia.objects.create(
            nombre=nombre,
            estado=estado,
            codigo_ine=codigo_ine,
            **kwargs,
        )


# ============================================================
# VALIDACIÓN BÁSICA DEL PAYLOAD
# ============================================================


class ValidacionPayloadTests(ImportExportBaseTestCase):
    """
    Pruebas de validación de la estructura principal del JSON.
    """

    def test_registros_no_es_lista_falla(self):
        payload = {
            "version": 1,
            "modelo": "estado",
            "registros": {},
        }

        with self.assertRaises(ValidationError):
            importar_json(payload)

    def test_registros_es_none_falla(self):
        payload = {
            "version": 1,
            "modelo": "estado",
            "registros": None,
        }

        with self.assertRaises(ValidationError):
            importar_json(payload)

    def test_registros_no_es_diccionario_falla(self):
        payload = {
            "version": 1,
            "modelo": "estado",
            "registros": [
                "registro inválido",
            ],
        }

        with self.assertRaises(ValidationError):
            importar_json(payload)

    def test_registro_no_es_diccionario_falla(self):
        payload = {
            "version": 1,
            "modelo": "estado",
            "registros": [
                "registro inválido",
            ],
        }

        with self.assertRaises(ValidationError):
            importar_json(payload)

    def test_registro_none_falla(self):
        payload = {
            "version": 1,
            "modelo": "estado",
            "registros": [
                None,
            ],
        }

        with self.assertRaises(ValidationError):
            importar_json(payload)

    def test_registros_vacios_es_valido(self):
        payload = {
            "version": 1,
            "modelo": "estado",
            "registros": [],
        }

        resultado = importar_json(payload)

        self.assertEqual(resultado.total, 0)
        self.assertEqual(resultado.creados, 0)
        self.assertEqual(resultado.actualizados, 0)
        self.assertEqual(resultado.omitidos, 0)


# ============================================================
# MODO CREAR
# ============================================================


class ImportarModoCrearTests(ImportExportBaseTestCase):
    """
    En modo crear:

    - registros nuevos se crean;
    - registros cuyo ID ya existe se omiten;
    - el registro existente no se modifica.
    """

    def test_id_existente_se_omite_en_modo_crear(self):
        estado = self.crear_estado(
            nombre="Estado original",
            codigo_ine="CREAR001",
        )

        payload = {
            "version": 1,
            "modelo": "estado",
            "registros": [
                {
                    "id": estado.pk,
                    "nombre": "Estado modificado",
                    "codigo_ine": "CREAR002",
                }
            ],
        }

        resultado = importar_json(
            payload,
            modo="crear",
        )

        self.assertEqual(resultado.total, 1)
        self.assertEqual(resultado.creados, 0)
        self.assertEqual(resultado.actualizados, 0)
        self.assertEqual(resultado.omitidos, 1)

        estado.refresh_from_db()

        self.assertEqual(
            estado.nombre,
            "Estado original",
        )

        self.assertEqual(
            estado.codigo_ine,
            "CREAR001",
        )

    def test_registro_sin_id_se_crea_en_modo_crear(self):
        payload = {
            "version": 1,
            "modelo": "estado",
            "registros": [
                {
                    "nombre": "Nuevo sin ID",
                    "codigo_ine": "CREAR003",
                }
            ],
        }

        resultado = importar_json(
            payload,
            modo="crear",
        )

        self.assertEqual(resultado.total, 1)
        self.assertEqual(resultado.creados, 1)
        self.assertEqual(resultado.actualizados, 0)
        self.assertEqual(resultado.omitidos, 0)

        self.assertTrue(
            Estado.objects.filter(
                codigo_ine="CREAR003",
            ).exists()
        )

    def test_varios_registros_se_crean(self):
        payload = {
            "version": 1,
            "modelo": "estado",
            "registros": [
                {
                    "nombre": "Estado crear 1",
                    "codigo_ine": "CR001",
                },
                {
                    "nombre": "Estado crear 2",
                    "codigo_ine": "CR002",
                },
                {
                    "nombre": "Estado crear 3",
                    "codigo_ine": "CR003",
                },
            ],
        }

        resultado = importar_json(
            payload,
            modo="crear",
        )

        self.assertEqual(resultado.total, 3)
        self.assertEqual(resultado.creados, 3)
        self.assertEqual(resultado.actualizados, 0)
        self.assertEqual(resultado.omitidos, 0)

        self.assertEqual(
            Estado.objects.filter(
                codigo_ine__in=[
                    "CR001",
                    "CR002",
                    "CR003",
                ]
            ).count(),
            3,
        )


# ============================================================
# MODO ACTUALIZAR
# ============================================================


class ImportarModoActualizarTests(ImportExportBaseTestCase):
    """
    En modo actualizar:

    - registros sin ID se crean;
    - registros con ID existente se actualizan;
    """

    def test_id_existente_se_actualiza(self):
        estado = self.crear_estado(
            nombre="Nombre original",
            codigo_ine="ACT001",
        )

        payload = {
            "version": 1,
            "modelo": "estado",
            "registros": [
                {
                    "id": estado.pk,
                    "nombre": "Nombre actualizado",
                    "codigo_ine": "ACT002",
                }
            ],
        }

        resultado = importar_json(
            payload,
            modo="actualizar",
        )

        self.assertEqual(resultado.total, 1)
        self.assertEqual(resultado.creados, 0)
        self.assertEqual(resultado.actualizados, 1)
        self.assertEqual(resultado.omitidos, 0)

        estado.refresh_from_db()

        self.assertEqual(
            estado.nombre,
            "Nombre actualizado",
        )

        self.assertEqual(
            estado.codigo_ine,
            "ACT002",
        )

    def test_registro_sin_id_se_crea_en_modo_actualizar(self):
        payload = {
            "version": 1,
            "modelo": "estado",
            "registros": [
                {
                    "nombre": "Creado en actualizar",
                    "codigo_ine": "ACT003",
                }
            ],
        }

        resultado = importar_json(
            payload,
            modo="actualizar",
        )

        self.assertEqual(resultado.total, 1)
        self.assertEqual(resultado.creados, 1)
        self.assertEqual(resultado.actualizados, 0)

        self.assertTrue(
            Estado.objects.filter(
                codigo_ine="ACT003",
            ).exists()
        )

    def test_id_inexistente_crea_registro_en_actualizar(self):
        payload = {
            "version": 1,
            "modelo": "estado",
            "registros": [
                {
                    "id": 999999,
                    "nombre": "Estado con ID inexistente",
                    "codigo_ine": "ACT004",
                }
            ],
        }

        resultado = importar_json(
            payload,
            modo="actualizar",
        )

        self.assertEqual(resultado.total, 1)
        self.assertEqual(resultado.creados, 1)
        self.assertEqual(resultado.actualizados, 0)

        self.assertTrue(
            Estado.objects.filter(
                nombre="Estado con ID inexistente",
            ).exists()
        )

    def test_modo_invalido_falla(self):
        payload = {
            "version": 1,
            "modelo": "estado",
            "registros": [
                {
                    "nombre": "Estado",
                    "codigo_ine": "ACT005",
                }
            ],
        }

        with self.assertRaises(ValueError):
            importar_json(
                payload,
                modo="modo_inexistente",
            )

    def test_modo_mayusculas_es_valido(self):
        payload = {
            "version": 1,
            "modelo": "estado",
            "registros": [
                {
                    "nombre": "Estado modo",
                    "codigo_ine": "MODO001",
                }
            ],
        }

        resultado = importar_json(
            payload,
            modo="CREAR",
        )

        self.assertEqual(
            resultado.creados,
            1,
        )

    def test_modo_con_espacios_no_valido(self):
        payload = {
            "version": 1,
            "modelo": "estado",
            "registros": [
                {
                    "nombre": "Estado modo",
                    "codigo_ine": "MODO002",
                }
            ],
        }

        with self.assertRaises(ValueError):
            importar_json(
                payload,
                modo=" crear ",
            )


# ============================================================
# VALIDACIÓN DE CAMPOS
# ============================================================


class ValidacionCamposTests(ImportExportBaseTestCase):
    """
    Verifica que no se puedan introducir campos arbitrarios.
    """

    def test_campo_no_permitido_falla(self):
        payload = {
            "version": 1,
            "modelo": "estado",
            "registros": [
                {
                    "nombre": "Estado inválido",
                    "codigo_ine": "CAMPO001",
                    "campo_inventado": "valor",
                }
            ],
        }

        with self.assertRaises(ValidationError):
            importar_json(payload)

    def test_otro_campo_no_permitido_falla(self):
        payload = {
            "version": 1,
            "modelo": "estado",
            "registros": [
                {
                    "nombre": "Estado inválido",
                    "codigo_ine": "CAMPO002",
                    "campo_que_no_existe": "ERROR",
                }
            ],
        }

        with self.assertRaises(ValidationError):
            importar_json(payload)

    def test_id_es_campo_permitido_en_importacion(self):
        """
        Importante:

        Las exportaciones incluyen el ID de la instancia.
        Por lo tanto, importar un JSON exportado debe permitir
        recibir 'id'.

        Este test evita la regresión que produjo:

        Campo no permitido para Estado: id
        """
        estado = self.crear_estado(
            nombre="Estado con ID",
            codigo_ine="ID001",
        )

        payload = {
            "version": 1,
            "modelo": "estado",
            "registros": [
                {
                    "id": estado.pk,
                    "nombre": "Estado con ID",
                    "codigo_ine": "ID001",
                }
            ],
        }

        resultado = importar_json(
            payload,
            modo="crear",
        )

        self.assertEqual(
            resultado.omitidos,
            1,
        )

    def test_modelo_no_permitido_falla(self):
        payload = {
            "version": 1,
            "modelo": "auditlog",
            "registros": [
                {
                    "id": 1,
                }
            ],
        }

        with self.assertRaises(ValueError):
            importar_json(payload)


# ============================================================
# FOREIGN KEY
# ============================================================


class ForeignKeyTests(ImportExportBaseTestCase):
    """
    Pruebas de relaciones ForeignKey utilizando:

        Parroquia -> Estado
    """

    def test_foreign_key_por_id(self):
        estado = self.crear_estado(
            nombre="Estado FK",
            codigo_ine="FK001",
        )

        payload = {
            "version": 1,
            "modelo": "parroquia",
            "registros": [
                {
                    "nombre": "Parroquia FK",
                    "estado": estado.pk,
                }
            ],
        }

        resultado = importar_json(
            payload,
            modo="crear",
        )

        self.assertEqual(
            resultado.creados,
            1,
        )

        parroquia = Parroquia.objects.get(
            nombre="Parroquia FK",
        )

        self.assertEqual(
            parroquia.estado_id,
            estado.pk,
        )

    def test_foreign_key_como_objeto(self):
        estado = self.crear_estado(
            nombre="Estado FK objeto",
            codigo_ine="FK002",
        )

        payload = {
            "version": 1,
            "modelo": "parroquia",
            "registros": [
                {
                    "nombre": "Parroquia FK objeto",
                    "estado": {
                        "id": estado.pk,
                    },
                }
            ],
        }

        resultado = importar_json(
            payload,
            modo="crear",
        )

        self.assertEqual(
            resultado.creados,
            1,
        )

        parroquia = Parroquia.objects.get(
            nombre="Parroquia FK objeto",
        )

        self.assertEqual(
            parroquia.estado_id,
            estado.pk,
        )

    def test_foreign_key_inexistente_falla(self):
        payload = {
            "version": 1,
            "modelo": "parroquia",
            "registros": [
                {
                    "nombre": "Parroquia inválida",
                    "estado": 999999,
                }
            ],
        }

        with self.assertRaises(ValidationError):
            importar_json(payload)

        self.assertFalse(
            Parroquia.objects.filter(
                nombre="Parroquia inválida",
            ).exists()
        )

    def test_foreign_key_objeto_sin_id_falla(self):
        estado = self.crear_estado(
            nombre="Estado FK inválido",
            codigo_ine="FK003",
        )

        payload = {
            "version": 1,
            "modelo": "parroquia",
            "registros": [
                {
                    "nombre": "Parroquia inválida",
                    "estado": {
                        "nombre": estado.nombre,
                    },
                }
            ],
        }

        with self.assertRaises(ValidationError):
            importar_json(payload)

    def test_foreign_key_objeto_id_inexistente_falla(self):
        payload = {
            "version": 1,
            "modelo": "parroquia",
            "registros": [
                {
                    "nombre": "Parroquia FK inexistente",
                    "estado": {
                        "id": 999999,
                    },
                }
            ],
        }

        with self.assertRaises(ValidationError):
            importar_json(payload)

        self.assertFalse(
            Parroquia.objects.filter(
                nombre="Parroquia FK inexistente",
            ).exists()
        )


# ============================================================
# ATOMICIDAD
# ============================================================


class AtomicidadImportacionTests(ImportExportBaseTestCase):
    """
    Verifica que una importación sea completamente atómica.

    Si un registro falla, ninguno de los registros anteriores
    debe permanecer guardado.
    """

    def test_importacion_completa_es_atomica(self):
        payload = {
            "version": 1,
            "modelo": "estado",
            "registros": [
                {
                    "nombre": "Estado atomico 1",
                    "codigo_ine": "ATM001",
                },
                {
                    "nombre": "Estado atomico 2",
                    "codigo_ine": "ATM002",
                },
                {
                    "nombre": "Estado atomico invalido",
                    "codigo_ine": "ATM003",
                    "campo_que_no_existe": "ERROR",
                },
            ],
        }

        with self.assertRaises(ValidationError):
            importar_json(payload)

        self.assertFalse(
            Estado.objects.filter(
                codigo_ine="ATM001",
            ).exists()
        )

        self.assertFalse(
            Estado.objects.filter(
                codigo_ine="ATM002",
            ).exists()
        )

        self.assertFalse(
            Estado.objects.filter(
                codigo_ine="ATM003",
            ).exists()
        )

    def test_error_de_fk_revierte_registros_anteriores(self):
        """
        El codigo_ine debe respetar max_length=10.

        La versión anterior utilizaba:

            ATOM-FK-BASE

        que tiene más de 10 caracteres y provocaba:

            value too long for type character varying(10)

        Por eso aquí se utiliza ATMFK001.
        """
        estado = self.crear_estado(
            nombre="Estado valido",
            codigo_ine="ATMFK001",
        )

        payload = {
            "version": 1,
            "modelo": "parroquia",
            "registros": [
                {
                    "nombre": "Parroquia valida",
                    "estado": estado.pk,
                },
                {
                    "nombre": "Parroquia invalida",
                    "estado": 999999,
                },
            ],
        }

        with self.assertRaises(ValidationError):
            importar_json(payload)

        self.assertFalse(
            Parroquia.objects.filter(
                nombre="Parroquia valida",
            ).exists()
        )

        self.assertFalse(
            Parroquia.objects.filter(
                nombre="Parroquia invalida",
            ).exists()
        )

    def test_error_de_campo_revierte_registros_anteriores(self):
        payload = {
            "version": 1,
            "modelo": "estado",
            "registros": [
                {
                    "nombre": "Estado atomico A",
                    "codigo_ine": "ATMA001",
                },
                {
                    "nombre": "Estado atomico B",
                    "codigo_ine": "ATMB001",
                    "campo_inexistente": "ERROR",
                },
            ],
        }

        with self.assertRaises(ValidationError):
            importar_json(payload)

        self.assertFalse(
            Estado.objects.filter(
                codigo_ine="ATMA001",
            ).exists()
        )


# ============================================================
# LÍMITES
# ============================================================


class LimitesImportacionTests(ImportExportBaseTestCase):
    """
    Verifica los límites de seguridad de la importación.
    """

    def test_superar_limite_maximo_falla(self):
        registros = [
            {
                "nombre": f"Estado {i}",
                "codigo_ine": f"L{i:09d}"[:10],
            }
            for i in range(
                MAX_REGISTROS_IMPORTACION + 1
            )
        ]

        payload = {
            "version": 1,
            "modelo": "estado",
            "registros": registros,
        }

        with self.assertRaises(ValidationError):
            importar_json(payload)

        self.assertEqual(
            Estado.objects.count(),
            0,
        )

    def test_limite_personalizado(self):
        payload = {
            "version": 1,
            "modelo": "estado",
            "registros": [
                {
                    "nombre": "Estado limite 1",
                    "codigo_ine": "LIM001",
                },
                {
                    "nombre": "Estado limite 2",
                    "codigo_ine": "LIM002",
                },
                {
                    "nombre": "Estado limite 3",
                    "codigo_ine": "LIM003",
                },
            ],
        }

        with self.assertRaises(ValidationError):
            importar_json(
                payload,
                max_registros=2,
            )

        self.assertEqual(
            Estado.objects.count(),
            0,
        )


# ============================================================
# SERIALIZACIÓN
# ============================================================


class SerializacionTests(ImportExportBaseTestCase):
    """
    Pruebas de serialización de instancias.
    """

    def test_serializar_estado(self):
        estado = self.crear_estado(
            nombre="Estado serializado",
            codigo_ine="SER001",
        )

        datos = serializar_objeto(estado)

        self.assertIsInstance(
            datos,
            dict,
        )

        self.assertEqual(
            datos["id"],
            estado.pk,
        )

        self.assertEqual(
            datos["nombre"],
            "Estado serializado",
        )

        self.assertEqual(
            datos["codigo_ine"],
            "SER001",
        )

    def test_serializar_foreign_key(self):
        estado = self.crear_estado(
            nombre="Estado serializado FK",
            codigo_ine="SERFK001",
        )

        parroquia = self.crear_parroquia(
            estado=estado,
            nombre="Parroquia serializada",
            codigo_ine="PARFK001",
        )

        datos = serializar_objeto(
            parroquia,
        )

        self.assertEqual(
            datos["estado"],
            estado.pk,
        )

    def test_serializar_objeto_es_diccionario(self):
        estado = self.crear_estado(
            nombre="Estado diccionario",
            codigo_ine="SER002",
        )

        datos = serializar_objeto(
            estado,
        )

        self.assertIsInstance(
            datos,
            dict,
        )

    def test_serializar_incluye_id(self):
        estado = self.crear_estado(
            nombre="Estado ID",
            codigo_ine="SER003",
        )

        datos = serializar_objeto(
            estado,
        )

        self.assertIn(
            "id",
            datos,
        )

        self.assertEqual(
            datos["id"],
            estado.pk,
        )


# ============================================================
# EXPORTACIÓN
# ============================================================


class ExportacionTests(ImportExportBaseTestCase):
    """
    Pruebas de exportación JSON.
    """

    def test_exportar_modelo(self):
        self.crear_estado(
            nombre="Estado exportado 1",
            codigo_ine="EXP001",
        )

        self.crear_estado(
            nombre="Estado exportado 2",
            codigo_ine="EXP002",
        )

        payload = exportar_modelo(
            "estado",
        )

        self.assertEqual(
            payload["version"],
            1,
        )

        self.assertEqual(
            payload["modelo"],
            "estado",
        )

        self.assertEqual(
            payload["total"],
            2,
        )

        self.assertEqual(
            len(payload["registros"]),
            2,
        )

    def test_exportar_modelo_vacio(self):
        payload = exportar_modelo(
            "estado",
        )

        self.assertEqual(
            payload["modelo"],
            "estado",
        )

        self.assertEqual(
            payload["total"],
            0,
        )

        self.assertEqual(
            payload["registros"],
            [],
        )

    def test_exportar_con_limite(self):
        for i in range(5):
            self.crear_estado(
                nombre=f"Estado export {i}",
                codigo_ine=f"EL{i:03d}",
            )

        payload = exportar_modelo(
            "estado",
            limite=2,
        )

        self.assertEqual(
            payload["total"],
            2,
        )

        self.assertEqual(
            len(payload["registros"]),
            2,
        )

    def test_exportar_modelo_no_permitido(self):
        with self.assertRaises(ValueError):
            exportar_modelo(
                "auditlog",
            )

    def test_exportacion_incluye_ids(self):
        estado = self.crear_estado(
            nombre="Estado export ID",
            codigo_ine="EXPID001",
        )

        payload = exportar_modelo(
            "estado",
        )

        self.assertEqual(
            len(payload["registros"]),
            1,
        )

        registro = payload["registros"][0]

        self.assertIn(
            "id",
            registro,
        )

        self.assertEqual(
            registro["id"],
            estado.pk,
        )


# ============================================================
# EXPORTACIÓN + IMPORTACIÓN
# ============================================================


class ExportacionImportacionTests(ImportExportBaseTestCase):
    """
    Comprueba que un conjunto exportado pueda volver a importarse.
    """

    def test_exportar_y_reimportar(self):
        self.crear_estado(
            nombre="Estado portable",
            codigo_ine="PORT001",
        )

        payload_exportado = exportar_modelo(
            "estado",
        )

        self.assertEqual(
            payload_exportado["total"],
            1,
        )

        Estado.objects.all().delete()

        self.assertEqual(
            Estado.objects.count(),
            0,
        )

        resultado = importar_json(
            payload_exportado,
            modo="crear",
        )

        self.assertEqual(
            resultado.creados,
            1,
        )

        self.assertTrue(
            Estado.objects.filter(
                nombre="Estado portable",
                codigo_ine="PORT001",
            ).exists()
        )

    def test_exportar_y_reimportar_con_modo_actualizar(self):
        estado = self.crear_estado(
            nombre="Estado portable actualizar",
            codigo_ine="PORT002",
        )

        payload_exportado = exportar_modelo(
            "estado",
        )

        estado.nombre = "Nombre diferente"
        estado.codigo_ine = "PORT003"
        estado.save()

        resultado = importar_json(
            payload_exportado,
            modo="actualizar",
        )

        self.assertEqual(
            resultado.actualizados,
            1,
        )

        estado.refresh_from_db()

        self.assertEqual(
            estado.nombre,
            "Estado portable actualizar",
        )

        self.assertEqual(
            estado.codigo_ine,
            "PORT002",
        )


# ============================================================
# GEOMETRÍAS
# ============================================================


class GeometriaTests(ImportExportBaseTestCase):
    """
    Pruebas de conversión de geometrías.

    Las pruebas se adaptan dinámicamente al modelo
    PuntoDemanda.
    """

    def obtener_campo_geometria(self):
        for field in PuntoDemanda._meta.concrete_fields:
            if getattr(field, "geom_type", None):
                return field

            if field.__class__.__name__.lower().endswith(
                "geometryfield"
            ):
                return field

        return None

    def test_punto_demanda_tiene_campo_geometrico(self):
        campo = self.obtener_campo_geometria()

        if campo is None:
            self.skipTest(
                "PuntoDemanda no tiene un campo GeometryField."
            )

        self.assertIsNotNone(
            campo,
        )

    def test_geojson_point_es_convertible(self):
        campo = self.obtener_campo_geometria()

        if campo is None:
            self.skipTest(
                "PuntoDemanda no tiene un campo GeometryField."
            )

        from apps.core import import_export

        geojson = {
            "type": "Point",
            "coordinates": [
                -66.9036,
                10.4806,
            ],
        }

        geometria = import_export._convertir_geometria(
            geojson,
        )

        self.assertIsInstance(
            geometria,
            GEOSGeometry,
        )

        self.assertEqual(
            geometria.geom_type,
            "Point",
        )

        self.assertEqual(
            geometria.srid,
            4326,
        )

        self.assertAlmostEqual(
            geometria.x,
            -66.9036,
            places=4,
        )

        self.assertAlmostEqual(
            geometria.y,
            10.4806,
            places=4,
        )

    def test_geojson_string_es_convertible(self):
        from apps.core import import_export

        geojson = (
            '{"type":"Point",'
            '"coordinates":[-66.9036,10.4806]}'
        )

        geometria = import_export._convertir_geometria(
            geojson,
        )

        self.assertIsInstance(
            geometria,
            GEOSGeometry,
        )

        self.assertEqual(
            geometria.geom_type,
            "Point",
        )

        self.assertEqual(
            geometria.srid,
            4326,
        )

    def test_geometria_invalida_falla(self):
        from apps.core import import_export

        with self.assertRaises(Exception):
            import_export._convertir_geometria(
                "esto no es geojson",
            )

    def test_geometria_tipo_invalido_falla(self):
        from apps.core import import_export

        with self.assertRaises(ValueError):
            import_export._convertir_geometria(
                12345,
            )


# ============================================================
# AUDITORÍA
# ============================================================


class AuditoriaImportExportTests(ImportExportBaseTestCase):
    """
    Verifica que los servicios de importación y exportación
    invoquen registrar_auditoria correctamente.

    Estos tests verifican el contrato real utilizado por
    import_export.py:

    - modelo
    - descripcion
    - datos_nuevos
    - resultado

    No depende de la implementación interna de AuditLog.
    """

    @patch(
        "apps.core.import_export.registrar_auditoria"
    )
    def test_importacion_registra_auditoria(
        self,
        mock_auditoria,
    ):
        payload = {
            "version": 1,
            "modelo": "estado",
            "registros": [
                {
                    "nombre": "Estado auditado",
                    "codigo_ine": "AUD-001",
                }
            ],
        }

        resultado = importar_json(
            payload,
            modo="crear",
        )

        # ----------------------------------------------------
        # Resultado de la importación
        # ----------------------------------------------------

        self.assertEqual(
            resultado.creados,
            1,
        )

        # ----------------------------------------------------
        # Auditoría
        # ----------------------------------------------------

        mock_auditoria.assert_called_once()

        kwargs = mock_auditoria.call_args.kwargs

        self.assertEqual(
            kwargs["modelo"],
            "core.estado",
        )

        self.assertEqual(
            kwargs["resultado"],
            "exitoso",
        )

        self.assertIn(
            "descripcion",
            kwargs,
        )

        self.assertIn(
            "Importación JSON exitosa",
            kwargs["descripcion"],
        )

        self.assertIn(
            "datos_nuevos",
            kwargs,
        )

        datos_nuevos = kwargs["datos_nuevos"]

        self.assertEqual(
            datos_nuevos["modelo"],
            "core.estado",
        )

        self.assertEqual(
            datos_nuevos["total"],
            1,
        )

        self.assertEqual(
            datos_nuevos["creados"],
            1,
        )

        self.assertEqual(
            datos_nuevos["actualizados"],
            0,
        )

        self.assertEqual(
            datos_nuevos["omitidos"],
            0,
        )

        self.assertEqual(
            datos_nuevos["modo"],
            "crear",
        )

    @patch(
        "apps.core.import_export.registrar_auditoria"
    )
    def test_exportacion_registra_auditoria(
        self,
        mock_auditoria,
    ):
        self.crear_estado(
            nombre="Estado export auditado",
            codigo_ine="AUD-002",
        )

        payload = exportar_modelo(
            "estado",
        )

        # ----------------------------------------------------
        # Verificar exportación
        # ----------------------------------------------------

        self.assertEqual(
            payload["modelo"],
            "estado",
        )

        self.assertEqual(
            payload["total"],
            1,
        )

        # ----------------------------------------------------
        # Auditoría
        # ----------------------------------------------------

        mock_auditoria.assert_called_once()

        kwargs = mock_auditoria.call_args.kwargs

        self.assertEqual(
            kwargs["modelo"],
            "core.estado",
        )

        self.assertEqual(
            kwargs["resultado"],
            "exitoso",
        )

        self.assertIn(
            "descripcion",
            kwargs,
        )

        self.assertIn(
            "Exportación JSON",
            kwargs["descripcion"],
        )

        self.assertIn(
            "datos_nuevos",
            kwargs,
        )

        datos_nuevos = kwargs["datos_nuevos"]

        self.assertEqual(
            datos_nuevos["version"],
            1,
        )

        self.assertEqual(
            datos_nuevos["modelo"],
            "estado",
        )

        self.assertEqual(
            datos_nuevos["total"],
            1,
        )

        self.assertIn(
            "registros",
            datos_nuevos,
        )

        self.assertEqual(
            len(datos_nuevos["registros"]),
            1,
        )

    @patch(
        "apps.core.import_export.registrar_auditoria"
    )
    def test_importacion_fallida_registra_auditoria(
        self,
        mock_auditoria,
    ):
        payload = {
            "version": 1,
            "modelo": "estado",
            "registros": [
                {
                    "nombre": "Estado inválido",
                    "codigo_ine": "AUD-003",
                    "campo_inexistente": "ERROR",
                }
            ],
        }

        # ----------------------------------------------------
        # La importación debe fallar
        # ----------------------------------------------------

        with self.assertRaises(ValidationError):
            importar_json(
                payload,
                modo="crear",
            )

        # ----------------------------------------------------
        # La auditoría debe registrarse
        # ----------------------------------------------------

        mock_auditoria.assert_called_once()

        kwargs = mock_auditoria.call_args.kwargs

        self.assertEqual(
            kwargs["modelo"],
            "core.estado",
        )

        self.assertEqual(
            kwargs["resultado"],
            "fallido",
        )

        self.assertIn(
            "descripcion",
            kwargs,
        )

        self.assertIn(
            "datos_nuevos",
            kwargs,
        )


# ============================================================
# VALIDACIONES ADICIONALES
# ============================================================


class ValidacionesAdicionalesTests(ImportExportBaseTestCase):
    """
    Pruebas adicionales para evitar regresiones.
    """

    def test_estado_se_importa_sin_id(self):
        payload = {
            "version": 1,
            "modelo": "estado",
            "registros": [
                {
                    "nombre": "Estado sin ID",
                    "codigo_ine": "SINID001",
                }
            ],
        }

        resultado = importar_json(
            payload,
            modo="crear",
        )

        self.assertEqual(
            resultado.creados,
            1,
        )

        estado = Estado.objects.get(
            codigo_ine="SINID001",
        )

        self.assertIsNotNone(
            estado.pk,
        )

    def test_estado_se_importa_con_id_en_modo_actualizar(self):
        estado = self.crear_estado(
            nombre="Estado original",
            codigo_ine="CONID001",
        )

        payload = {
            "version": 1,
            "modelo": "estado",
            "registros": [
                {
                    "id": estado.pk,
                    "nombre": "Estado actualizado",
                    "codigo_ine": "CONID002",
                }
            ],
        }

        resultado = importar_json(
            payload,
            modo="actualizar",
        )

        self.assertEqual(
            resultado.actualizados,
            1,
        )

        estado.refresh_from_db()

        self.assertEqual(
            estado.nombre,
            "Estado actualizado",
        )

        self.assertEqual(
            estado.codigo_ine,
            "CONID002",
        )

    def test_fk_de_parroquia_se_conserva_al_serializar(self):
        estado = self.crear_estado(
            nombre="Estado relación",
            codigo_ine="REL001",
        )

        parroquia = self.crear_parroquia(
            estado=estado,
            nombre="Parroquia relación",
            codigo_ine="REL002",
        )

        datos = serializar_objeto(
            parroquia,
        )

        self.assertEqual(
            datos["estado"],
            estado.pk,
        )

    def test_importacion_multiple_de_parroquias(self):
        estado = self.crear_estado(
            nombre="Estado múltiples",
            codigo_ine="MULT001",
        )

        payload = {
            "version": 1,
            "modelo": "parroquia",
            "registros": [
                {
                    "nombre": "Parroquia 1",
                    "estado": estado.pk,
                },
                {
                    "nombre": "Parroquia 2",
                    "estado": estado.pk,
                },
            ],
        }

        resultado = importar_json(
            payload,
            modo="crear",
        )

        self.assertEqual(
            resultado.creados,
            2,
        )

        self.assertEqual(
            Parroquia.objects.filter(
                estado=estado,
            ).count(),
            2,
        )