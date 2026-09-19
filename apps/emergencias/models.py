"""
Modelos del módulo de Emergencias.

Contiene las entidades relacionadas con eventos de emergencia y los
reportes ciudadanos asociados a zonas afectadas o puntos de demanda.
"""
from django.contrib.gis.db import models
from django.core.validators import MinValueValidator

from apps.core.models import ZonaAfectada, PuntoDemanda


# ============================================================
# EVENTO
# ============================================================

class Evento(models.Model):
    """Evento de desastre o emergencia registrado."""

    TIPO_CHOICES = [
        ('inundacion', 'Inundación'),
        ('terremoto', 'Terremoto'),
        ('deslizamiento', 'Deslizamiento'),
        ('incendio', 'Incendio'),
        ('otro', 'Otro'),
    ]

    # Colores asociados por tipo (útil en templates)
    TIPO_COLORES = {
        'inundacion': '#0066cc',
        'terremoto': '#dc3545',
        'deslizamiento': '#8b4513',
        'incendio': '#ff6600',
        'otro': '#6c757d',
    }

    nombre = models.CharField(max_length=200)
    tipo = models.CharField(max_length=30, choices=TIPO_CHOICES)
    fecha = models.DateTimeField()
    magnitud = models.FloatField(
        null=True, blank=True,
        help_text="Magnitud o intensidad del evento (escala según tipo)"
    )
    descripcion = models.TextField(blank=True)
    activo = models.BooleanField(
        default=True,
        help_text="¿El evento sigue en curso?"
    )

    class Meta:
        verbose_name = "Evento"
        verbose_name_plural = "Eventos"
        ordering = ['-fecha']
        indexes = [
            models.Index(fields=['-fecha']),
            models.Index(fields=['activo']),
            models.Index(fields=['tipo', 'activo']),
        ]

    def __str__(self):
        return f"{self.nombre} ({self.get_tipo_display()}) — {self.fecha.date()}"

    # --- Propiedades ---

    @property
    def total_zonas(self) -> int:
        """Cantidad de zonas afectadas asociadas a este evento."""
        return self.zonas_afectadas.count()

    @property
    def esta_activo(self) -> bool:
        """Alias legible de `activo`."""
        return self.activo

    @property
    def color(self) -> str:
        """Color hex asociado al tipo de evento."""
        return self.TIPO_COLORES.get(self.tipo, '#6c757d')

    @property
    def magnitud_fmt(self) -> str:
        """Magnitud formateada o guion si no aplica."""
        return f"{self.magnitud:.2f}" if self.magnitud is not None else "—"


# ============================================================
# REPORTE CIUDADANO
# ============================================================

class Reporte(models.Model):
    """
    Reporte ciudadano o de campo asociado a una zona afectada o
    punto de demanda.
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
    autor = models.CharField(
        max_length=100, blank=True,
        help_text="Nombre o seudónimo del reportante (opcional)"
    )
    texto = models.TextField()
    fecha = models.DateTimeField(auto_now_add=True)
    imagen = models.ImageField(
        upload_to='reportes/%Y/%m/',
        blank=True, null=True
    )
    verificado = models.BooleanField(
        default=False,
        help_text="¿Ha sido validado por un operador?"
    )

    class Meta:
        verbose_name = "Reporte ciudadano"
        verbose_name_plural = "Reportes ciudadanos"
        ordering = ['-fecha']
        indexes = [
            models.Index(fields=['-fecha']),
            models.Index(fields=['verificado']),
            models.Index(fields=['zona_afectada']),
            models.Index(fields=['punto_demanda']),
        ]

    def __str__(self):
        return f"Reporte #{self.id} — {self.fecha.strftime('%Y-%m-%d %H:%M')}"

    # --- Propiedades ---

    @property
    def autor_display(self) -> str:
        """Autor o etiqueta anónima."""
        return self.autor or "Anónimo"

    @property
    def texto_corto(self) -> str:
        """Texto truncado a 100 caracteres."""
        if not self.texto:
            return ""
        return self.texto[:100] + ('...' if len(self.texto) > 100 else '')

    @property
    def tiene_imagen(self) -> bool:
        """True si el reporte incluye imagen."""
        return bool(self.imagen)

    @property
    def esta_verificado(self) -> bool:
        """Alias legible de `verificado`."""
        return self.verificado

    @property
    def asociado_a(self) -> str:
        """Descripción legible del destino del reporte."""
        if self.zona_afectada:
            return f"Zona: {self.zona_afectada.nombre}"
        if self.punto_demanda:
            return f"Punto: {self.punto_demanda.nombre}"
        return "Sin asociar"

    @property
    def color_estado(self) -> str:
        """Color hex según verificación."""
        return '#28a745' if self.verificado else '#ffc107'