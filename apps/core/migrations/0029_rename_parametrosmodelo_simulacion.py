"""
Renombra ParametrosModelo -> Simulacion y su FK en ResultadoOptimizacion.

Cambios:
- Modelo: ParametrosModelo -> Simulacion.
- Tabla: core_parametrosmodelo -> core_simulacion.
- Campo FK: ResultadoOptimizacion.parametros -> escenario.
- Columna: parametros_id -> escenario_id.

Motivación:
"Parámetros del modelo" era un nombre confuso para lo que en realidad
es una plantilla de simulación de optimización.

Reversible con los RenameModel/RenameField inversos.
"""
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0028_quitar_constraints_redundantes_zonaafectada'),
    ]

    operations = [
        migrations.RenameModel(
            old_name='ParametrosModelo',
            new_name='Simulacion',
        ),
        migrations.RenameField(
            model_name='resultadooptimizacion',
            old_name='parametros',
            new_name='escenario',
        ),
    ]
