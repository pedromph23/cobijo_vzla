from django.db import migrations, models

class Migration(migrations.Migration):
    dependencies = [('reportes', '0001_initial')]
    operations = [
        migrations.AddField(
            model_name='registroreporte',
            name='modo',
            field=models.CharField(default='actual', max_length=20),
        ),
        migrations.AddField(
            model_name='registroreporte',
            name='fecha_referencia',
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
