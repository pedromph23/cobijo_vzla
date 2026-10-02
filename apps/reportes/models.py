"""
Modelos de trazabilidad del módulo de reportes.
"""
from django.conf import settings
from django.db import models


class RegistroReporte(models.Model):
    """Bitácora persistente de cada intento de generación de reporte."""

    RESULTADOS = [
        ('exitoso', 'Exitoso'),
        ('sin_datos', 'Sin datos'),
        ('error', 'Error'),
        ('rechazado', 'Rechazado'),
    ]

    TIPOS = [
        ('excel', 'Excel'),
        ('pdf', 'PDF'),
    ]

    CONTENIDOS = [
        ('zonas', 'Zonas afectadas'),
        ('general', 'Estadísticas generales'),
    ]

    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='registros_reportes',
    )
    fecha_generacion = models.DateTimeField(auto_now_add=True, db_index=True)
    tipo = models.CharField(max_length=10, choices=TIPOS)
    contenido = models.CharField(max_length=20, choices=CONTENIDOS)
    fecha_desde = models.DateTimeField(null=True, blank=True)
    fecha_hasta = models.DateTimeField(null=True, blank=True)
    archivo = models.CharField(max_length=255, blank=True)
    resultado = models.CharField(max_length=20, choices=RESULTADOS, db_index=True)
    detalle = models.CharField(max_length=500, blank=True)
    ip = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=500, blank=True)

    class Meta:
        verbose_name = 'Registro de reporte'
        verbose_name_plural = 'Bitácora de reportes'
        ordering = ['-fecha_generacion']
        indexes = [
            models.Index(fields=['usuario', '-fecha_generacion']),
            models.Index(fields=['tipo', 'contenido', '-fecha_generacion']),
        ]

    def __str__(self):
        usuario = self.usuario.get_username() if self.usuario else 'Sistema'
        return f'{self.fecha_generacion:%d/%m/%Y %H:%M} · {usuario} · {self.tipo.upper()} · {self.contenido}'
