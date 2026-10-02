from django.db import migrations, models
from django.utils import timezone

class Migration(migrations.Migration):
    dependencies = [('core', '0005_registroversion')]
    operations = [
        migrations.AlterField(
            model_name='registroversion',
            name='fecha_version',
            field=models.DateTimeField(default=timezone.now, db_index=True),
        ),
    ]
