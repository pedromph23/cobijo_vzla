from django.contrib.gis.db import models
from apps.core.models import ZonaAfectada, PuntoDemanda


class Evento(models.Model):
    """
    Evento de desastre o emergencia registrado.
    """
    TIPO_CHOICES = [
        ('inundacion', 'Inundación'),
        ('terremoto', 'Terremoto'),
        ('deslizamiento', 'Deslizamiento'),
        ('incendio', 'Incendio'),
        ('otro', 'Otro'),
    ]

    nombre = models.CharField(max_length=200)
    tipo = models.CharField(max_length=30, choices=TIPO_CHOICES)
    fecha = models.DateTimeField()
    magnitud = models.FloatField(null=True, blank=True, help_text="Magnitud o intensidad del evento")
    descripcion = models.TextField(blank=True)
    activo = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.nombre} ({self.tipo}) - {self.fecha.date()}"


class Reporte(models.Model):
    """
    Reporte ciudadano o de campo asociado a una zona afectada o punto de demanda.
    """
    zona_afectada = models.ForeignKey(
        ZonaAfectada,
        on_delete=models.CASCADE,
        related_name='reportes',
        null=True,
        blank=True
    )
    punto_demanda = models.ForeignKey(
        PuntoDemanda,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    autor = models.CharField(max_length=100, blank=True)
    texto = models.TextField()
    fecha = models.DateTimeField(auto_now_add=True)
    imagen = models.ImageField(upload_to='reportes/', blank=True, null=True)
    verificado = models.BooleanField(default=False)

    def __str__(self):
        return f"Reporte {self.id} - {self.fecha}"