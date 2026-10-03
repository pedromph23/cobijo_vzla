from django.db import migrations, models


def copiar_descripcion_a_detalle(apps, schema_editor):
    RegistroAuditoria = apps.get_model("core", "RegistroAuditoria")
    for registro in RegistroAuditoria.objects.exclude(descripcion=""):
        registro.detalle = registro.descripcion
        registro.save(update_fields=["detalle"])


def restaurar_descripcion_desde_detalle(apps, schema_editor):
    RegistroAuditoria = apps.get_model("core", "RegistroAuditoria")
    for registro in RegistroAuditoria.objects.exclude(detalle=""):
        registro.descripcion = registro.detalle
        registro.save(update_fields=["descripcion"])


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0006_registroversion_fecha_default"),
    ]

    operations = [
        migrations.AddField(
            model_name="registroauditoria",
            name="metodo",
            field=models.CharField(default="", max_length=10),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="registroauditoria",
            name="ruta",
            field=models.CharField(default="", max_length=500),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="registroauditoria",
            name="detalle",
            field=models.TextField(blank=True, default=""),
            preserve_default=False,
        ),
        migrations.RunPython(
            copiar_descripcion_a_detalle,
            restaurar_descripcion_desde_detalle,
        ),
        migrations.AlterField(
            model_name="registroauditoria",
            name="modelo",
            field=models.CharField(blank=True, max_length=150),
        ),
        migrations.AlterField(
            model_name="registroauditoria",
            name="user_agent",
            field=models.CharField(blank=True, max_length=500),
        ),
        migrations.RemoveIndex(
            model_name="registroauditoria",
            name="core_registr_modulo_8b1d9b_idx",
        ),
        migrations.RemoveField(
            model_name="registroauditoria",
            name="modulo",
        ),
        migrations.RemoveField(
            model_name="registroauditoria",
            name="objeto",
        ),
        migrations.RemoveField(
            model_name="registroauditoria",
            name="descripcion",
        ),
        migrations.AlterModelOptions(
            name="registroauditoria",
            options={
                "ordering": ["-fecha"],
                "verbose_name": "Registro de auditoría",
                "verbose_name_plural": "Bitácora del sistema",
            },
        ),
    ]
