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
    codigo_ine = models.CharField(
        max_length=10, blank=True, null=True,
        verbose_name="Código INE"
    )
    geom = models.MultiPolygonField(
        srid=4326, null=True, blank=True,
        verbose_name="Geometría"
    )

    class Meta:
        verbose_name = "Estado"
        verbose_name_plural = "Estados"
        ordering = ['nombre']

    def __str__(self):
        return self.nombre

    @property
    def total_parroquias(self) -> int:
        """Cantidad de parroquias registradas en este estado."""
        return self.parroquias.count()

    @property
    def centroide(self):
        """Centroide (lat, lng) del estado o None si no hay geometría."""
        if not self.geom:
            return None
        c = self.geom.centroid
        return (c.y, c.x)


class Parroquia(models.Model):
    """Parroquia perteneciente a un estado."""
    nombre = models.CharField(max_length=100)
    estado = models.ForeignKey(
        Estado,
        on_delete=models.CASCADE,
        related_name='parroquias'
    )
    codigo_ine = models.CharField(
        max_length=10, blank=True, null=True,
        verbose_name="Código INE"
    )
    geom = models.MultiPolygonField(
        srid=4326, null=True, blank=True,
        verbose_name="Geometría"
    )
    poblacion = models.IntegerField(
        default=0,
        validators=[MinValueValidator(0)]
    )
    densidad_poblacional = models.FloatField(
        default=0.0,
        validators=[MinValueValidator(0)],
        help_text="Habitantes por km²"
    )
    indice_vulnerabilidad = models.FloatField(
        default=0.5,
        validators=[MinValueValidator(0), MaxValueValidator(1)],
        help_text="Índice de 0 (baja) a 1 (alta)"
    )

    class Meta:
        verbose_name = "Parroquia"
        verbose_name_plural = "Parroquias"
        ordering = ['estado__nombre', 'nombre']
        unique_together = ('nombre', 'estado')
        indexes = [
            models.Index(fields=['estado', 'nombre']),
        ]

    def __str__(self):
        return f"{self.nombre}, {self.estado.nombre}"

    @property
    def centroide(self):
        """Centroide (lat, lng) de la parroquia o None."""
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


# ============================================================
# PUNTO DE DEMANDA
# ============================================================

class PuntoDemanda(models.Model):
    """Punto geográfico que representa una necesidad humanitaria."""
    nombre = models.CharField(max_length=200)
    parroquia = models.ForeignKey(
        Parroquia,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='puntos_demanda'
    )
    ubicacion = models.PointField(srid=4326, verbose_name="Ubicación")
    poblacion = models.IntegerField(
        default=0,
        validators=[MinValueValidator(0)]
    )
    vulnerabilidad = models.FloatField(
        default=0.5,
        validators=[MinValueValidator(0), MaxValueValidator(1)],
        help_text="Índice de 0 (baja) a 1 (alta)"
    )
    descripcion = models.TextField(blank=True)
    creado = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Punto de demanda"
        verbose_name_plural = "Puntos de demanda"
        ordering = ['nombre']
        indexes = [
            models.Index(fields=['parroquia']),
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
        """Clasificación legible de la vulnerabilidad."""
        v = self.vulnerabilidad or 0
        if v >= 0.7:
            return 'alta'
        if v >= 0.4:
            return 'media'
        return 'baja'


# ============================================================
# SITIO CANDIDATO
# ============================================================

class SitioCandidato(models.Model):
    """Ubicación posible para abrir un centro de acopio o refugio."""
    nombre = models.CharField(max_length=200)
    ubicacion = models.PointField(srid=4326, verbose_name="Ubicación")
    capacidad_maxima = models.IntegerField(
        default=100,
        validators=[MinValueValidator(1)],
        help_text="Personas que puede albergar"
    )
    costo_apertura = models.DecimalField(
        max_digits=12, decimal_places=2, default=0,
        verbose_name="Costo de apertura"
    )
    costo_operacion = models.DecimalField(
        max_digits=12, decimal_places=2, default=0,
        verbose_name="Costo de operación"
    )
    tipo_terreno = models.CharField(max_length=50, blank=True)
    disponible = models.BooleanField(
        default=True,
        help_text="¿Está disponible para ser seleccionado?"
    )
    creado = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Sitio candidato"
        verbose_name_plural = "Sitios candidatos"
        ordering = ['nombre']
        indexes = [
            models.Index(fields=['disponible']),
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

class RefugioExistente(models.Model):
    """Refugio ya operativo en el territorio."""
    nombre = models.CharField(max_length=200)
    direccion = models.CharField(max_length=300)
    ubicacion = models.PointField(srid=4326, verbose_name="Ubicación")
    capacidad_total = models.IntegerField(
        validators=[MinValueValidator(0)],
        verbose_name="Capacidad total"
    )
    capacidad_disponible = models.IntegerField(
        validators=[MinValueValidator(0)],
        verbose_name="Capacidad disponible"
    )
    servicios = models.JSONField(
        default=list,
        blank=True,
        help_text="Lista de servicios disponibles"
    )
    operativo = models.BooleanField(default=True)
    telefono = models.CharField(max_length=20, blank=True)
    horario = models.CharField(max_length=100, blank=True)

    class Meta:
        verbose_name = "Refugio existente"
        verbose_name_plural = "Refugios existentes"
        ordering = ['nombre']
        indexes = [
            models.Index(fields=['operativo']),
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
        """Ocupación en % (0-100). 0 si no hay capacidad registrada."""
        if not self.capacidad_total:
            return 0.0
        ocupados = self.capacidad_total - self.capacidad_disponible
        return round((ocupados / self.capacidad_total) * 100, 1)

    @property
    def esta_lleno(self) -> bool:
        """True si no hay capacidad disponible."""
        return self.capacidad_disponible <= 0

    @property
    def servicios_texto(self) -> str:
        """Servicios como string legible."""
        if not self.servicios:
            return 'Sin servicios registrados'
        return ', '.join(self.servicios)


# ============================================================
# ZONA AFECTADA
# ============================================================

class ZonaAfectada(models.Model):
    """Zona geográfica afectada por un evento de emergencia."""
    evento = models.ForeignKey(
        'emergencias.Evento',
        on_delete=models.CASCADE,
        related_name='zonas_afectadas'
    )
    nombre = models.CharField(max_length=200)
    descripcion = models.TextField(blank=True)
    geom = models.GeometryField(
        srid=4326,
        help_text="Punto, polígono o multipolígono que delimita la zona"
    )
    nivel_alerta = models.CharField(
        max_length=20,
        choices=[('bajo', 'Bajo'), ('medio', 'Medio'), ('alto', 'Alto')],
        default='medio'
    )
    fecha_inicio = models.DateTimeField()
    fecha_fin = models.DateTimeField(null=True, blank=True)
    heridos = models.IntegerField(default=0, validators=[MinValueValidator(0)])
    fallecidos = models.IntegerField(default=0, validators=[MinValueValidator(0)])
    damnificados = models.IntegerField(default=0, validators=[MinValueValidator(0)])

    class Meta:
        verbose_name = "Zona afectada"
        verbose_name_plural = "Zonas afectadas"
        ordering = ['-fecha_inicio']
        indexes = [
            models.Index(fields=['nivel_alerta']),
            models.Index(fields=['fecha_inicio']),
        ]

    def __str__(self):
        return self.nombre

    @property
    def esta_activa(self) -> bool:
        """True si la zona no tiene fecha de fin."""
        return self.fecha_fin is None

    @property
    def total_afectados(self) -> int:
        """Suma de heridos + fallecidos + damnificados."""
        return (self.heridos or 0) + (self.fallecidos or 0) + (self.damnificados or 0)

    @property
    def lat(self):
        """Centroide lat de la geometría."""
        if not self.geom:
            return None
        return self.geom.centroid.y

    @property
    def lng(self):
        """Centroide lng de la geometría."""
        if not self.geom:
            return None
        return self.geom.centroid.x


# ============================================================
# PARÁMETROS DE MODELO
# ============================================================

class ParametrosModelo(models.Model):
    """Configuración de un escenario de optimización."""
    TIPO_MODELO_CHOICES = [
        ('pmediana', 'P-Mediana'),
        ('pcentro', 'P-Centro'),
        ('cobertura', 'Cobertura Máxima'),
        ('capacidades', 'Localización con Capacidades'),
    ]

    nombre_escenario = models.CharField(max_length=200)
    tipo_modelo = models.CharField(max_length=30, choices=TIPO_MODELO_CHOICES)
    p = models.IntegerField(
        default=3,
        validators=[MinValueValidator(1)],
        help_text="Número de centros a abrir"
    )
    presupuesto = models.DecimalField(
        max_digits=14, decimal_places=2,
        null=True, blank=True
    )
    radio_cobertura = models.FloatField(
        default=5000,
        validators=[MinValueValidator(0)],
        help_text="Radio de cobertura en metros"
    )
    ponderador_vulnerabilidad = models.FloatField(
        default=1.0,
        validators=[MinValueValidator(0)]
    )
    ponderador_heridos = models.FloatField(
        default=1.0,
        validators=[MinValueValidator(0)]
    )
    ponderador_fallecidos = models.FloatField(
        default=1.0,
        validators=[MinValueValidator(0)]
    )
    ponderador_damnificados = models.FloatField(
        default=1.0,
        validators=[MinValueValidator(0)]
    )
    filtro_estado = models.ForeignKey(
        Estado,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Parámetros de modelo"
        verbose_name_plural = "Parámetros de modelo"
        ordering = ['-fecha_creacion']

    def __str__(self):
        return self.nombre_escenario

    @property
    def radio_cobertura_km(self) -> float:
        return round(self.radio_cobertura / 1000, 2)


# ============================================================
# RESULTADO DE OPTIMIZACIÓN
# ============================================================

class ResultadoOptimizacion(models.Model):
    """Resultado guardado de una ejecución de optimización."""
    parametros = models.ForeignKey(
        ParametrosModelo,
        on_delete=models.CASCADE,
        related_name='resultados'
    )
    fecha_ejecucion = models.DateTimeField(auto_now_add=True)
    datos_json = models.JSONField()

    class Meta:
        verbose_name = "Resultado de optimización"
        verbose_name_plural = "Resultados de optimización"
        ordering = ['-fecha_ejecucion']

    def __str__(self):
        return f"Resultado #{self.id} — {self.parametros.nombre_escenario}"

    @property
    def total_centros(self) -> int:
        return len((self.datos_json or {}).get('centros', []))

    @property
    def porcentaje_cubierto(self) -> float:
        return (self.datos_json or {}).get('porcentaje_cubierto', 0.0)

    @property
    def poblacion_atendida(self) -> int:
        return (self.datos_json or {}).get('poblacion_atendida', 0)

    @property
    def resumen(self) -> str:
        """Resumen de una línea para mostrar en tablas."""
        return (
            f"{self.total_centros} centros · "
            f"{self.porcentaje_cubierto}% cobertura · "
            f"{self.poblacion_atendida:,} personas"
        ).replace(',', '.')