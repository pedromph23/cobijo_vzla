from django.db import migrations, models
from django.db.models import Q, F


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0011_alter_registroauditoria_options_and_more"),
    ]

    operations = [
        migrations.AddConstraint(
            model_name="puntodemanda",
            constraint=models.CheckConstraint(
                condition=Q(poblacion__gte=0),
                name="punto_demanda_poblacion_gte_0",
            ),
        ),
        migrations.AddConstraint(
            model_name="puntodemanda",
            constraint=models.CheckConstraint(
                condition=Q(vulnerabilidad__gte=0) & Q(vulnerabilidad__lte=1),
                name="punto_demanda_vulnerabilidad_0_1",
            ),
        ),
        migrations.AddConstraint(
            model_name="sitiocandidato",
            constraint=models.CheckConstraint(
                condition=Q(capacidad_maxima__gte=1),
                name="sitio_candidato_capacidad_gte_1",
            ),
        ),
        migrations.AddConstraint(
            model_name="sitiocandidato",
            constraint=models.CheckConstraint(
                condition=Q(costo_apertura__gte=0),
                name="sitio_candidato_costo_apertura_gte_0",
            ),
        ),
        migrations.AddConstraint(
            model_name="sitiocandidato",
            constraint=models.CheckConstraint(
                condition=Q(costo_operacion__gte=0),
                name="sitio_candidato_costo_operacion_gte_0",
            ),
        ),
        migrations.AddConstraint(
            model_name="refugioexistente",
            constraint=models.CheckConstraint(
                condition=Q(capacidad_total__gte=0),
                name="refugio_capacidad_total_gte_0",
            ),
        ),
        migrations.AddConstraint(
            model_name="refugioexistente",
            constraint=models.CheckConstraint(
                condition=Q(capacidad_disponible__gte=0),
                name="refugio_capacidad_disponible_gte_0",
            ),
        ),
        migrations.AddConstraint(
            model_name="refugioexistente",
            constraint=models.CheckConstraint(
                condition=Q(capacidad_disponible__lte=F("capacidad_total")),
                name="refugio_disponible_lte_total",
            ),
        ),
        migrations.AddConstraint(
            model_name="zonaafectada",
            constraint=models.CheckConstraint(
                condition=Q(heridos__gte=0),
                name="zona_heridos_gte_0",
            ),
        ),
        migrations.AddConstraint(
            model_name="zonaafectada",
            constraint=models.CheckConstraint(
                condition=Q(fallecidos__gte=0),
                name="zona_fallecidos_gte_0",
            ),
        ),
        migrations.AddConstraint(
            model_name="zonaafectada",
            constraint=models.CheckConstraint(
                condition=Q(damnificados__gte=0),
                name="zona_damnificados_gte_0",
            ),
        ),
    ]
