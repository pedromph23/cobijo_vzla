"""
Modelos del módulo Core de CobijoVzla.

Contiene las entidades base del sistema: división territorial, puntos
de demanda, sitios candidatos, refugios y zonas afectadas.

Todas las geometrías usan SRID 4326 (WGS84 / GPS estándar).
"""
from django.conf import settings
from django.contrib.gis.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.core.exceptions import ValidationError
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
        constraints = [
            models.CheckConstraint(
                condition=models.Q(capacidad_total__gte=0),
                name='refugio_capacidad_total_gte_0',
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(capacidad_disponible__gte=0)
                    & models.Q(
                        capacidad_disponible__lte=models.F('capacidad_total')
                    )
                ),
                name='refugio_capacidad_disponible_valida',
            ),
        ]

    def clean(self):
        super().clean()
        errores = {}

        if self.capacidad_total is not None and self.capacidad_total < 0:
            errores['capacidad_total'] = (
                'La capacidad total no puede ser negativa.'
            )

        if (
            self.capacidad_disponible is not None
            and self.capacidad_disponible < 0
        ):
            errores['capacidad_disponible'] = (
                'La capacidad disponible no puede ser negativa.'
            )

        if (
            self.capacidad_total is not None
            and self.capacidad_disponible is not None
            and self.capacidad_disponible > self.capacidad_total
        ):
            errores['capacidad_disponible'] = (
                'La capacidad disponible no puede superar la capacidad total.'
            )

        if errores:
            raise ValidationError(errores)

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
        constraints = [
            models.CheckConstraint(
                condition=(
                    models.Q(fecha_fin__isnull=True)
                    | models.Q(fecha_fin__gte=models.F('fecha_inicio'))
                ),
                name='zona_fecha_fin_valida',
            ),
            models.CheckConstraint(
                condition=models.Q(heridos__gte=0),
                name='zona_heridos_gte_0',
            ),
            models.CheckConstraint(
                condition=models.Q(fallecidos__gte=0),
                name='zona_fallecidos_gte_0',
            ),
            models.CheckConstraint(
                condition=models.Q(damnificados__gte=0),
                name='zona_damnificados_gte_0',
            ),
        ]

    def clean(self):
        super().clean()
        errores = {}

        if (
            self.fecha_fin
            and self.fecha_inicio
            and self.fecha_fin < self.fecha_inicio
        ):
            errores['fecha_fin'] = (
                'La fecha de fin no puede ser anterior a la fecha de inicio.'
            )

        for campo in ('heridos', 'fallecidos', 'damnificados'):
            valor = getattr(self, campo)
            if valor is not None and valor < 0:
                errores[campo] = 'El valor no puede ser negativo.'

        if errores:
            raise ValidationError(errores)

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
        constraints = [
            models.CheckConstraint(
                condition=models.Q(p__gte=1),
                name='parametros_p_gte_1',
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(presupuesto__isnull=True)
                    | models.Q(presupuesto__gte=0)
                ),
                name='parametros_presupuesto_gte_0',
            ),
            models.CheckConstraint(
                condition=models.Q(radio_cobertura__gte=0),
                name='parametros_radio_gte_0',
            ),
        ]

    def clean(self):
        super().clean()
        errores = {}

        if self.p is not None and self.p < 1:
            errores['p'] = 'El número de centros debe ser al menos 1.'

        if self.presupuesto is not None and self.presupuesto < 0:
            errores['presupuesto'] = 'El presupuesto no puede ser negativo.'

        if self.radio_cobertura is not None and self.radio_cobertura < 0:
            errores['radio_cobertura'] = (
                'El radio de cobertura no puede ser negativo.'
            )

        if errores:
            raise ValidationError(errores)

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

# ============================================================
# AUDITORÍA / BITÁCORA
# ============================================================

class AuditLog(models.Model):
    """Registro inmutable de operaciones relevantes del sistema."""

    ACCION_CHOICES = [
        ('LOGIN', 'Inicio de sesión'),
        ('LOGOUT', 'Cierre de sesión'),
        ('LOGIN_FAILED', 'Inicio de sesión fallido'),
        ('CREATE', 'Creación'),
        ('UPDATE', 'Actualización'),
        ('DELETE', 'Eliminación'),
        ('IMPORT', 'Importación'),
        ('EXPORT', 'Exportación'),
        ('OPTIMIZATION', 'Optimización'),
        ('COMMAND', 'Comando'),
        ('REPORT', 'Reporte'),
    ]

    RESULTADO_CHOICES = [
        ('exitoso', 'Exitoso'),
        ('fallido', 'Fallido'),
    ]

    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='registros_auditoria',
    )
    fecha_hora = models.DateTimeField(auto_now_add=True, db_index=True)
    accion = models.CharField(max_length=30, choices=ACCION_CHOICES, db_index=True)
    modelo = models.CharField(max_length=150, blank=True, db_index=True)
    objeto_id = models.CharField(max_length=100, blank=True)
    objeto_repr = models.CharField(max_length=255, blank=True)
    descripcion = models.TextField(blank=True)
    ip = models.GenericIPAddressField(null=True, blank=True)
    metodo_http = models.CharField(max_length=10, blank=True)
    ruta = models.CharField(max_length=500, blank=True)
    user_agent = models.TextField(blank=True)
    datos_anteriores = models.JSONField(null=True, blank=True)
    datos_nuevos = models.JSONField(null=True, blank=True)
    resultado = models.CharField(
        max_length=20,
        choices=RESULTADO_CHOICES,
        default='exitoso',
        db_index=True,
    )

    class Meta:
        verbose_name = 'Registro de auditoría'
        verbose_name_plural = 'Registros de auditoría'
        ordering = ['-fecha_hora']
        indexes = [
            models.Index(fields=['usuario', '-fecha_hora']),
            models.Index(fields=['accion', '-fecha_hora']),
            models.Index(fields=['modelo', 'objeto_id']),
        ]

    def __str__(self):
        usuario = self.usuario.get_username() if self.usuario else 'Sistema'
        return f'{self.fecha_hora:%Y-%m-%d %H:%M:%S} — {usuario} — {self.accion}'
