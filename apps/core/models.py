"""
Modelos del módulo Core de CobijoVzla.

Contiene las entidades base del sistema: división territorial, puntos
de demanda, sitios candidatos, refugios y zonas afectadas.

Todas las geometrías usan SRID 4326 (WGS84 / GPS estándar).
"""
from django.contrib.gis.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone


# ============================================================
# DIVISIÓN TERRITORIAL
# ============================================================

class Estado(models.Model):
    """Estado o entidad federal de Venezuela."""
    nombre = models.CharField(max_length=100, unique=True)
    codigo_ine = models.CharField(max_length=10, blank=True, null=True, verbose_name="Código INE")
    geom = models.MultiPolygonField(srid=4326, null=True, blank=True, verbose_name="Geometría")

    class Meta:
        verbose_name = "Estado"
        verbose_name_plural = "Estados"
        ordering = ['nombre']

    def __str__(self):
        return self.nombre

    @property
    def total_parroquias(self) -> int:
        return self.parroquias.count()

    @property
    def centroide(self):
        if not self.geom:
            return None
        c = self.geom.centroid
        return (c.y, c.x)


class Parroquia(models.Model):
    """Parroquia perteneciente a un estado."""
    nombre = models.CharField(max_length=100)
    estado = models.ForeignKey(Estado, on_delete=models.CASCADE, related_name='parroquias')
    codigo_ine = models.CharField(max_length=10, blank=True, null=True, verbose_name="Código INE")
    geom = models.MultiPolygonField(srid=4326, null=True, blank=True, verbose_name="Geometría")
    poblacion = models.IntegerField(default=0, validators=[MinValueValidator(0)])
    densidad_poblacional = models.FloatField(default=0.0, validators=[MinValueValidator(0)], help_text="Habitantes por km²")
    indice_vulnerabilidad = models.FloatField(default=0.5, validators=[MinValueValidator(0), MaxValueValidator(1)], help_text="Índice de 0 (baja) a 1 (alta)")

    class Meta:
        verbose_name = "Parroquia"
        verbose_name_plural = "Parroquias"
        ordering = ['estado__nombre', 'nombre']
        unique_together = ('nombre', 'estado')
        indexes = [models.Index(fields=['estado', 'nombre'])]

    def __str__(self):
        return f"{self.nombre}, {self.estado.nombre}"

    @property
    def centroide(self):
        if not self.geom:
            return None
        c = self.geom.centroid
        return (c.y, c.x)

    @property
    def lat(self):
        c = self.centroide
        return c[0] if c else None

    @property
    def lng(self):
        c = self.centroide
        return c[1] if c else None


class UbicacionParroquiaMixin:
    """Asigna una parroquia a partir de la geometría del punto."""

    def asignar_parroquia(self):
        if not getattr(self, 'ubicacion', None):
            return None
        from apps.core.models import Parroquia
        return (
            Parroquia.objects
            .filter(geom__intersects=self.ubicacion)
            .select_related('estado')
            .first()
        )

    def save(self, *args, **kwargs):
        if hasattr(self, 'parroquia') and self.ubicacion:
            self.parroquia = self.asignar_parroquia()
        super().save(*args, **kwargs)


# ============================================================
# PUNTO DE DEMANDA
# ============================================================

class PuntoDemanda(UbicacionParroquiaMixin, models.Model):
    nombre = models.CharField(max_length=200)
    parroquia = models.ForeignKey(Parroquia, on_delete=models.SET_NULL, null=True, blank=True, related_name='puntos_demanda')
    ubicacion = models.PointField(srid=4326, verbose_name="Ubicación")
    poblacion = models.IntegerField(default=0, validators=[MinValueValidator(0)])
    vulnerabilidad = models.FloatField(default=0.5, validators=[MinValueValidator(0), MaxValueValidator(1)], help_text="Índice de 0 (baja) a 1 (alta)")
    descripcion = models.TextField(blank=True)
    creado = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Punto de demanda"
        verbose_name_plural = "Puntos de demanda"
        ordering = ['nombre']
        indexes = [models.Index(fields=['parroquia'])]
        constraints = [
            models.CheckConstraint(condition=models.Q(poblacion__gte=0), name='punto_demanda_poblacion_gte_0'),
            models.CheckConstraint(condition=models.Q(vulnerabilidad__gte=0) & models.Q(vulnerabilidad__lte=1), name='punto_demanda_vulnerabilidad_0_1'),
        ]

    def __str__(self):
        return self.nombre

    @property
    def lat(self):
        return self.ubicacion.y if self.ubicacion else None

    @property
    def lng(self):
        return self.ubicacion.x if self.ubicacion else None

    @property
    def nivel_vulnerabilidad(self) -> str:
        v = self.vulnerabilidad or 0
        if v >= 0.7:
            return 'alta'
        if v >= 0.4:
            return 'media'
        return 'baja'


# ============================================================
# SITIO CANDIDATO
# ============================================================

class SitioCandidato(UbicacionParroquiaMixin, models.Model):
    nombre = models.CharField(max_length=200)
    parroquia = models.ForeignKey(Parroquia, on_delete=models.SET_NULL, null=True, blank=True, related_name='sitios_candidatos')
    ubicacion = models.PointField(srid=4326, verbose_name="Ubicación")
    capacidad_maxima = models.IntegerField(default=100, validators=[MinValueValidator(1)], help_text="Personas que puede albergar")
    costo_apertura = models.DecimalField(max_digits=12, decimal_places=2, default=0, validators=[MinValueValidator(0)], verbose_name="Costo de apertura")
    costo_operacion = models.DecimalField(max_digits=12, decimal_places=2, default=0, validators=[MinValueValidator(0)], verbose_name="Costo de operación")
    tipo_terreno = models.CharField(max_length=50, blank=True)
    disponible = models.BooleanField(default=True, help_text="¿Está disponible para ser seleccionado?")
    creado = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Sitio candidato"
        verbose_name_plural = "Sitios candidatos"
        ordering = ['nombre']
        indexes = [models.Index(fields=['disponible']), models.Index(fields=['parroquia'])]
        constraints = [
            models.CheckConstraint(condition=models.Q(capacidad_maxima__gte=1), name='sitio_candidato_capacidad_gte_1'),
            models.CheckConstraint(condition=models.Q(costo_apertura__gte=0), name='sitio_candidato_costo_apertura_gte_0'),
            models.CheckConstraint(condition=models.Q(costo_operacion__gte=0), name='sitio_candidato_costo_operacion_gte_0'),
        ]

    def __str__(self):
        return self.nombre

    @property
    def lat(self):
        return self.ubicacion.y if self.ubicacion else None

    @property
    def lng(self):
        return self.ubicacion.x if self.ubicacion else None


# ============================================================
# REFUGIO EXISTENTE
# ============================================================

class RefugioExistente(UbicacionParroquiaMixin, models.Model):
    nombre = models.CharField(max_length=200)
    direccion = models.CharField(max_length=300)
    parroquia = models.ForeignKey(Parroquia, on_delete=models.SET_NULL, null=True, blank=True, related_name='refugios_existentes')
    ubicacion = models.PointField(srid=4326, verbose_name="Ubicación")
    capacidad_total = models.IntegerField(validators=[MinValueValidator(0)], verbose_name="Capacidad total")
    capacidad_disponible = models.IntegerField(validators=[MinValueValidator(0)], verbose_name="Capacidad disponible")
    servicios = models.JSONField(default=list, blank=True, help_text="Lista de servicios disponibles")
    operativo = models.BooleanField(default=True)
    telefono = models.CharField(max_length=20, blank=True)
    horario = models.CharField(max_length=100, blank=True)

    class Meta:
        verbose_name = "Refugio existente"
        verbose_name_plural = "Refugios existentes"
        ordering = ['nombre']
        indexes = [models.Index(fields=['operativo']), models.Index(fields=['parroquia'])]
        constraints = [
            models.CheckConstraint(condition=models.Q(capacidad_total__gte=0), name='refugio_capacidad_total_gte_0'),
            models.CheckConstraint(condition=models.Q(capacidad_disponible__gte=0), name='refugio_capacidad_disponible_gte_0'),
            models.CheckConstraint(condition=models.Q(capacidad_disponible__lte=models.F('capacidad_total')), name='refugio_disponible_lte_total'),
        ]

    def __str__(self):
        return self.nombre

    @property
    def lat(self):
        return self.ubicacion.y if self.ubicacion else None

    @property
    def lng(self):
        return self.ubicacion.x if self.ubicacion else None

    @property
    def porcentaje_ocupacion(self) -> float:
        if not self.capacidad_total:
            return 0.0
        ocupados = self.capacidad_total - self.capacidad_disponible
        return round((ocupados / self.capacidad_total) * 100, 1)

    @property
    def esta_lleno(self) -> bool:
        return self.capacidad_disponible <= 0

    @property
    def servicios_texto(self) -> str:
        if not self.servicios:
            return 'Sin servicios registrados'
        return ', '.join(self.servicios)


# ============================================================
# ZONA AFECTADA
# ============================================================

class ZonaAfectada(models.Model):
    evento = models.ForeignKey('emergencias.Evento', on_delete=models.CASCADE, related_name='zonas_afectadas')
    nombre = models.CharField(max_length=200)
    descripcion = models.TextField(blank=True)
    geom = models.GeometryField(srid=4326, help_text="Punto, polígono o multipolígono que delimita la zona")
    nivel_alerta = models.CharField(max_length=20, choices=[('bajo', 'Bajo'), ('medio', 'Medio'), ('alto', 'Alto')], default='medio')
    fecha_inicio = models.DateTimeField()
    fecha_fin = models.DateTimeField(null=True, blank=True)
    heridos = models.IntegerField(default=0, validators=[MinValueValidator(0)])
    fallecidos = models.IntegerField(default=0, validators=[MinValueValidator(0)])
    damnificados = models.IntegerField(default=0, validators=[MinValueValidator(0)])

    class Meta:
        verbose_name = "Zona afectada"
        verbose_name_plural = "Zonas afectadas"
        ordering = ['-fecha_inicio']
        indexes = [models.Index(fields=['nivel_alerta']), models.Index(fields=['fecha_inicio'])]
        constraints = [
            models.CheckConstraint(condition=models.Q(heridos__gte=0), name='zona_heridos_gte_0'),
            models.CheckConstraint(condition=models.Q(fallecidos__gte=0), name='zona_fallecidos_gte_0'),
            models.CheckConstraint(condition=models.Q(damnificados__gte=0), name='zona_damnificados_gte_0'),
        ]

    def __str__(self):
        return self.nombre

    @property
    def esta_activa(self) -> bool:
        return self.fecha_fin is None

    @property
    def total_afectados(self) -> int:
        return (self.heridos or 0) + (self.fallecidos or 0) + (self.damnificados or 0)

    @property
    def lat(self):
        if not self.geom:
            return None
        return self.geom.centroid.y

    @property
    def lng(self):
        if not self.geom:
            return None
        return self.geom.centroid.x


# ============================================================
# PARÁMETROS DE MODELO
# ============================================================

class ParametrosModelo(models.Model):
    TIPO_MODELO_CHOICES = [
        ('pmediana', 'P-Mediana'),
        ('pcentro', 'P-Centro'),
        ('cobertura', 'Cobertura Máxima'),
        ('capacidades', 'Localización con Capacidades'),
    ]
    nombre_escenario = models.CharField(max_length=200)