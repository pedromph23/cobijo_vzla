from django.db import migrations, models
from django.db.models import Q, F


# La base de datos de producción puede contener algunas de estas restricciones
# creadas por una migración/versión anterior aunque Django todavía no las tenga
# registradas como aplicadas. PostgreSQL no permite volver a crearlas con el
# mismo nombre, por lo que la parte física se ejecuta de forma idempotente.

def constraint_sql(table, name, condition):
    return f"""
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = '{name}'
          AND conrelid = '{table}'::regclass
    ) THEN
        ALTER TABLE {table}
        ADD CONSTRAINT {name} CHECK ({condition});
    END IF;
END
$$;
"""


def drop_constraint_sql(table, name):
    return f"ALTER TABLE {table} DROP CONSTRAINT IF EXISTS {name};"


CONSTRAINTS = [
    (
        "core_puntodemanda",
        "punto_demanda_poblacion_gte_0",
        "poblacion >= 0",
    ),
    (
        "core_puntodemanda",
        "punto_demanda_vulnerabilidad_0_1",
        "vulnerabilidad >= 0 AND vulnerabilidad <= 1",
    ),
    (
        "core_sitiocandidato",
        "sitio_candidato_capacidad_gte_1",
        "capacidad_maxima >= 1",
    ),
    (
        "core_sitiocandidato",
        "sitio_candidato_costo_apertura_gte_0",
        "costo_apertura >= 0",
    ),
    (
        "core_sitiocandidato",
        "sitio_candidato_costo_operacion_gte_0",
        "costo_operacion >= 0",
    ),
    (
        "core_refugioexistente",
        "refugio_capacidad_total_gte_0",
        "capacidad_total >= 0",
    ),
    (
        "core_refugioexistente",
        "refugio_capacidad_disponible_gte_0",
        "capacidad_disponible >= 0",
    ),
    (
        "core_refugioexistente",
        "refugio_disponible_lte_total",
        "capacidad_disponible <= capacidad_total",
    ),
    (
        "core_zonaafectada",
        "zona_heridos_gte_0",
        "heridos >= 0",
    ),
    (
        "core_zonaafectada",
        "zona_fallecidos_gte_0",
        "fallecidos >= 0",
    ),
    (
        "core_zonaafectada",
        "zona_damnificados_gte_0",
        "damnificados >= 0",
    ),
]


state_operations = [
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


database_operations = [
    migrations.RunSQL(
        sql="\n".join(
            constraint_sql(table, name, condition)
            for table, name, condition in CONSTRAINTS
        ),
        reverse_sql="\n".join(
            drop_constraint_sql(table, name)
            for table, name, _condition in reversed(CONSTRAINTS)
        ),
    )
]


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0011_alter_registroauditoria_options_and_more"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=database_operations,
            state_operations=state_operations,
        ),
    ]
