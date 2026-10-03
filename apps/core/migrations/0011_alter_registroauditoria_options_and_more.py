from django.db import migrations


class Migration(migrations.Migration):
    """Punto de compatibilidad para conservar el grafo histórico de migraciones.

    El esquema de RegistroAuditoria ya quedó creado con la estructura actual
    desde la migración 0004 en esta línea del proyecto. Esta migración debe
    existir porque 0012_integridad_operativa la declara como dependencia.
    No modifica datos ni estructura.
    """

    dependencies = [
        ("core", "0006_registroversion_fecha_default"),
    ]

    operations = []
