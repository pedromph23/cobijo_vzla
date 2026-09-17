from django.contrib.gis.db import models


class Estado(models.Model):
    nombre = models.CharField(max_length=100, unique=True)
    codigo_ine = models.CharField(max_length=10, blank=True, null=True)
    geom = models.MultiPolygonField(srid=4326, null=True, blank=True)

    class Meta:
        verbose_name = "Estado"
        verbose_name_plural = "Estados"
        ordering = ['nombre']

    def __str__(self):
        return self.nombre


class Parroquia(models.Model):
    nombre = models.CharField(max_length=100)
    estado = models.ForeignKey(Estado, on_delete=models.CASCADE, related_name='parroquias')
    codigo_ine = models.CharField(max_length=10, blank=True, null=True)
    geom = models.MultiPolygonField(srid=4326, null=True, blank=True)
    poblacion = models.IntegerField(default=0)
    densidad_poblacional = models.FloatField(default=0.0)
    indice_vulnerabilidad = models.FloatField(default=0.5)

    class Meta:
        verbose_name = "Parroquia"
        verbose_name_plural = "Parroquias"
        ordering = ['estado__nombre', 'nombre']
        # Evitar duplicados de parroquia dentro de un mismo estado
        unique_together = ('nombre', 'estado')

    def __str__(self):
        return f"{self.nombre}, {self.estado.nombre}"


class PuntoDemanda(models.Model):
    nombre = models.CharField(max_length=200)
    parroquia = models.ForeignKey(
        Parroquia,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='puntos_demanda'
    )
    ubicacion = models.PointField(srid=4326)
    poblacion = models.IntegerField(default=0)
    vulnerabilidad = models.FloatField(default=0.5)
    descripcion = models.TextField(blank=True)

    class Meta:
        verbose_name = "Punto de demanda"
        verbose_name_plural = "Puntos de demanda"
        ordering = ['nombre']

    def __str__(self):
        return self.nombre


class SitioCandidato(models.Model):
    nombre = models.CharField(max_length=200)
    ubicacion = models.PointField(srid=4326)
    capacidad_maxima = models.IntegerField(default=100)
    costo_apertura = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    costo_operacion = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    tipo_terreno = models.CharField(max_length=50, blank=True)
    disponible = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Sitio candidato"
        verbose_name_plural = "Sitios candidatos"
        ordering = ['nombre']

    def __str__(self):
        return self.nombre


class RefugioExistente(models.Model):
    nombre = models.CharField(max_length=200)
    direccion = models.CharField(max_length=300)
    ubicacion = models.PointField(srid=4326)
    capacidad_total = models.IntegerField()
    capacidad_disponible = models.IntegerField()
    servicios = models.JSONField(default=list, blank=True)
    operativo = models.BooleanField(default=True)
    telefono = models.CharField(max_length=20, blank=True)
    horario = models.CharField(max_length=100, blank=True)

    class Meta:
        verbose_name = "Refugio existente"
        verbose_name_plural = "Refugios existentes"
        ordering = ['nombre']

    def __str__(self):
        return self.nombre


class ZonaAfectada(models.Model):
    # Referencia corregida usando la ruta completa de la app
    evento = models.ForeignKey(
        'emergencias.Evento',
        on_delete=models.CASCADE,
        related_name='zonas_afectadas'
    )
    nombre = models.CharField(max_length=200)
    descripcion = models.TextField(blank=True)
    geom = models.GeometryField(srid=4326, help_text="Punto, polígono o multipolígono que delimita la zona")
    nivel_alerta = models.CharField(
        max_length=20,
        choices=[('bajo', 'Bajo'), ('medio', 'Medio'), ('alto', 'Alto')],
        default='medio'
    )
    fecha_inicio = models.DateTimeField()
    fecha_fin = models.DateTimeField(null=True, blank=True)
    heridos = models.IntegerField(default=0)
    fallecidos = models.IntegerField(default=0)
    damnificados = models.IntegerField(default=0)

    class Meta:
        verbose_name = "Zona afectada"
        verbose_name_plural = "Zonas afectadas"
        ordering = ['-fecha_inicio']

    def __str__(self):
        return self.nombre


class ParametrosModelo(models.Model):
    TIPO_MODELO_CHOICES = [
        ('pmediana', 'P-Mediana'),
        ('pcentro', 'P-Centro'),
        ('cobertura', 'Cobertura Máxima'),
        ('capacidades', 'Localización con Capacidades'),
    ]

    nombre_escenario = models.CharField(max_length=200)
    tipo_modelo = models.CharField(max_length=30, choices=TIPO_MODELO_CHOICES)
    p = models.IntegerField(default=3, help_text="Número de centros a abrir")
    presupuesto = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    radio_cobertura = models.FloatField(default=5000, help_text="Radio de cobertura en metros")
    ponderador_vulnerabilidad = models.FloatField(default=1.0)
    ponderador_heridos = models.FloatField(default=1.0)
    ponderador_fallecidos = models.FloatField(default=1.0)
    ponderador_damnificados = models.FloatField(default=1.0)
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


class ResultadoOptimizacion(models.Model):
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
        return f"Resultado {self.id} - {self.fecha_ejecucion}"