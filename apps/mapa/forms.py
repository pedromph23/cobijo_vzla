"""
Formularios del panel administrativo.

La interfaz oculta la representación técnica de las coordenadas y ofrece
controles sencillos para los datos operativos. La conversión final sigue
centralizada en el formulario Django.
"""
from django import forms
from django.contrib.gis.geos import Point, GEOSGeometry

from apps.core.models import (
    Estado,
    Parroquia,
    PuntoDemanda,
    SitioCandidato,
    RefugioExistente,
    ZonaAfectada,
    ParametrosModelo,
)
from apps.emergencias.models import Evento, Reporte
from apps.core.validators import (
    validar_nombre_operativo,
    validar_telefono,
    validar_texto_sin_numeros_ni_especiales,
    validar_texto_operativo,
)


SERVICIOS_REFUGIO = (
    ('agua', 'Agua'),
    ('alimentacion', 'Alimentación'),
    ('medicina', 'Medicina'),
    ('primeros_auxilios', 'Primeros auxilios'),
    ('higiene', 'Higiene'),
    ('atencion_medica', 'Atención médica'),
    ('electricidad', 'Electricidad'),
    ('internet', 'Internet'),
)

TIPOS_TERRENO_SITIO = (
    ('terreno', 'Terreno'),
    ('edificio', 'Edificio'),
    ('cancha', 'Cancha deportiva'),
    ('escuela', 'Escuela'),
    ('iglesia', 'Iglesia'),
    ('otro', 'Otro'),
)


def _parsear_punto(valor) -> Point:
    """Convierte el valor simple del mapa (lng,lat) en Point WGS84."""
    if isinstance(valor, Point):
        return valor
    if not isinstance(valor, str):
        raise forms.ValidationError("Selecciona una ubicación en el mapa.")
    partes = valor.replace(',', ' ').split()
    if len(partes) < 2:
        raise forms.ValidationError("Selecciona una ubicación en el mapa.")
    try:
        lng, lat = float(partes[0]), float(partes[1])
    except ValueError:
        raise forms.ValidationError("La ubicación seleccionada no es válida.")
    if not (-180 <= lng <= 180) or not (-90 <= lat <= 90):
        raise forms.ValidationError("La ubicación está fuera del rango permitido.")
    if not (0.60 <= lat <= 12.25) or not (-73.50 <= lng <= -58.05):
        raise forms.ValidationError("La ubicación debe estar dentro del territorio de Venezuela.")
    return Point(lng, lat, srid=4326)


class UbicacionInputField(forms.CharField):
    """Campo de transporte para coordenadas seleccionadas en el mapa.

    El navegador envía ``lng,lat``. No usamos el GeometryField de Django para
    el valor oculto porque este campo recibe deliberadamente una representación
    de interfaz y la conversión a Point se hace una sola vez en ``clean_ubicacion``.
    """

    def __init__(self, *args, **kwargs):
        kwargs.setdefault('required', True)
        kwargs.setdefault('widget', forms.HiddenInput())
        kwargs.setdefault('label', 'Ubicación')
        super().__init__(*args, **kwargs)

    def prepare_value(self, value):
        if isinstance(value, Point):
            return f'{value.x:.6f},{value.y:.6f}'
        if value is not None and hasattr(value, 'x') and hasattr(value, 'y'):
            return f'{value.x:.6f},{value.y:.6f}'
        return value


class PuntoDemandaForm(forms.ModelForm):
    ubicacion = UbicacionInputField()

    class Meta:
        model = PuntoDemanda
        fields = ['nombre', 'ubicacion', 'poblacion', 'vulnerabilidad', 'descripcion']
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'form-control', 'maxlength': 200}),
            'poblacion': forms.NumberInput(attrs={'class': 'form-control', 'min': 0, 'step': 1, 'inputmode': 'numeric'}),
            'vulnerabilidad': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.1', 'min': 0, 'max': 1, 'inputmode': 'decimal'}),
            'descripcion': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'maxlength': 2000}),
        }

    def clean_ubicacion(self):
        return _parsear_punto(self.cleaned_data.get('ubicacion'))

    def clean_nombre(self):
        return validar_nombre_operativo(self.cleaned_data.get('nombre'))

    def clean_poblacion(self):
        valor = self.cleaned_data.get('poblacion')
        if valor is None or valor < 0:
            raise forms.ValidationError('La población no puede ser negativa.')
        if valor > 100000000:
            raise forms.ValidationError('La población no debe superar 100.000.000.')
        return valor

    def clean_vulnerabilidad(self):
        valor = self.cleaned_data.get('vulnerabilidad')
        if valor is None or valor < 0 or valor > 1:
            raise forms.ValidationError('La vulnerabilidad debe estar entre 0 y 1.')
        return valor

    def clean_descripcion(self):
        texto = (self.cleaned_data.get('descripcion') or '').strip()
        if len(texto) > 2000:
            raise forms.ValidationError('La descripción no puede superar los 2000 caracteres.')
        return texto


class SitioCandidatoForm(forms.ModelForm):
    """Formulario operativo para registrar un sitio candidato sin coordenadas técnicas."""

    ubicacion = UbicacionInputField(
        help_text='Selecciona el lugar en el mapa. La parroquia se determina automáticamente a partir de la geometría territorial.',
    )

    class Meta:
        model = SitioCandidato
        fields = ['nombre', 'ubicacion', 'capacidad_maxima', 'costo_apertura', 'costo_operacion', 'tipo_terreno', 'disponible']
        widgets = {
            'nombre': forms.TextInput(attrs={
                'class': 'form-control',
                'maxlength': 200,
                'autocomplete': 'organization',
                'placeholder': 'Ej.: Escuela Bolivariana de La Pastora',
            }),
            'capacidad_maxima': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 1,
                'step': 1,
                'inputmode': 'numeric',
                'placeholder': 'Ej.: 250',
            }),
            'costo_apertura': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 0,
                'step': '0.01',
                'inputmode': 'decimal',
                'placeholder': '0.00',
            }),
            'costo_operacion': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 0,
                'step': '0.01',
                'inputmode': 'decimal',
                'placeholder': '0.00',
            }),
            'tipo_terreno': forms.Select(
                choices=TIPOS_TERRENO_SITIO,
                attrs={'class': 'form-select'},
            ),
            'disponible': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
        labels = {
            'capacidad_maxima': 'Capacidad máxima',
            'costo_apertura': 'Costo de apertura',
            'costo_operacion': 'Costo de operación',
            'tipo_terreno': 'Tipo de sitio',
            'disponible': 'Disponible para selección',
        }
        help_texts = {
            'capacidad_maxima': 'Cantidad máxima de personas que podría albergar.',
            'costo_apertura': 'Costo estimado para habilitar el sitio.',
            'costo_operacion': 'Costo estimado de operación del sitio.',
            'tipo_terreno': 'Ayuda a identificar rápidamente qué tipo de espacio es.',
            'disponible': 'Si está activo, el modelo de optimización puede considerarlo como alternativa.',
        }

    def clean_ubicacion(self):
        return _parsear_punto(self.cleaned_data.get('ubicacion'))

    def clean_nombre(self):
        return validar_nombre_operativo(self.cleaned_data.get('nombre'))

    def clean_capacidad_maxima(self):
        valor = self.cleaned_data.get('capacidad_maxima')
        if valor is None or valor < 1:
            raise forms.ValidationError('La capacidad máxima debe ser al menos 1.')
        if valor > 1000000:
            raise forms.ValidationError('La capacidad máxima no debe superar 1.000.000.')
        return valor

    def clean_costo_apertura(self):
        valor = self.cleaned_data.get('costo_apertura')
        if valor is not None and valor < 0:
            raise forms.ValidationError('El costo de apertura no puede ser negativo.')
        return valor

    def clean_costo_operacion(self):
        valor = self.cleaned_data.get('costo_operacion')
        if valor is not None and valor < 0:
            raise forms.ValidationError('El costo de operación no puede ser negativo.')
        return valor


class RefugioExistenteForm(forms.ModelForm):
    ubicacion = UbicacionInputField()
    servicios = forms.MultipleChoiceField(
        choices=SERVICIOS_REFUGIO,
        required=False,
        widget=forms.CheckboxSelectMultiple(attrs={'class': 'refugio-servicios-list'}),
        label='Servicios e insumos disponibles',
        help_text='Marca lo habitual y, si necesitas algo más, escríbelo abajo separado por comas.',
    )
    otros_servicios = forms.CharField(
        required=False,
        label='Otros servicios o insumos',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'maxlength': 500,
            'placeholder': 'Ej.: alimentos secos, colchonetas, pañales, agua potable',
            'autocomplete': 'off',
        }),
        help_text='Opcional. Puedes escribir varios separados por comas.',
    )

    class Meta:
        model = RefugioExistente
        fields = ['nombre', 'direccion', 'ubicacion', 'capacidad_total', 'capacidad_disponible', 'servicios', 'operativo', 'telefono', 'horario']
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'form-control', 'maxlength': 200}),
            'direccion': forms.TextInput(attrs={'class': 'form-control', 'maxlength': 300}),
            'capacidad_total': forms.NumberInput(attrs={'class': 'form-control', 'min': 0, 'step': 1, 'inputmode': 'numeric'}),
            'capacidad_disponible': forms.NumberInput(attrs={'class': 'form-control', 'min': 0, 'step': 1, 'inputmode': 'numeric'}),
            'operativo': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'telefono': forms.TextInput(attrs={'class': 'form-control', 'inputmode': 'tel', 'autocomplete': 'tel'}),
            'horario': forms.TextInput(attrs={'class': 'form-control', 'maxlength': 100, 'placeholder': '24/7, 08:00-18:00, etc.'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            valores = self.instance.servicios if isinstance(self.instance.servicios, list) else []
            conocidos = {valor for valor, _ in SERVICIOS_REFUGIO}
            self.initial['servicios'] = [str(v) for v in valores if str(v) in conocidos]
            self.initial['otros_servicios'] = ', '.join(str(v) for v in valores if str(v) not in conocidos)

    def clean_telefono(self):
        value = self.cleaned_data.get('telefono', '').strip()
        validar_telefono(value)
        return value

    def clean_ubicacion(self):
        return _parsear_punto(self.cleaned_data.get('ubicacion'))

    def clean_nombre(self):
        return validar_nombre_operativo(self.cleaned_data.get('nombre'))

    def clean_direccion(self):
        direccion = (self.cleaned_data.get('direccion') or '').strip()
        if len(direccion) < 5:
            raise forms.ValidationError('La dirección debe tener al menos 5 caracteres.')
        return direccion

    def clean_capacidad_total(self):
        valor = self.cleaned_data.get('capacidad_total')
        if valor is None or valor < 0:
            raise forms.ValidationError('La capacidad total no puede ser negativa.')
        if valor > 1000000:
            raise forms.ValidationError('La capacidad total no debe superar 1.000.000.')
        return valor

    def clean_capacidad_disponible(self):
        valor = self.cleaned_data.get('capacidad_disponible')
        if valor is None or valor < 0:
            raise forms.ValidationError('La capacidad disponible no puede ser negativa.')
        return valor

    def clean_horario(self):
        horario = (self.cleaned_data.get('horario') or '').strip()
        if len(horario) > 100:
            raise forms.ValidationError('El horario no puede superar los 100 caracteres.')
        return horario

    def clean_servicios(self):
        return list(self.cleaned_data.get('servicios') or [])

    def clean(self):
        cleaned = super().clean()
        total = cleaned.get('capacidad_total') or 0
        disponible = cleaned.get('capacidad_disponible') or 0
        if disponible > total:
            self.add_error('capacidad_disponible', f'La capacidad disponible ({disponible}) no puede superar la capacidad total ({total}).')

        otros = cleaned.get('otros_servicios', '') or ''
        otros = otros.replace(';', ',').replace('\n', ',')
        extras = []
        vistos = set(cleaned.get('servicios') or [])
        for item in otros.split(','):
            item = ' '.join(item.split()).strip()
            if not item:
                continue
            clave = item.casefold()
            if clave not in {str(v).casefold() for v in vistos}:
                extras.append(item)
                vistos.add(clave)
        cleaned['servicios'] = list(cleaned.get('servicios') or []) + extras
        return cleaned


class ZonaAfectadaForm(forms.ModelForm):
    class Meta:
        model = ZonaAfectada
        fields = ['evento', 'nombre', 'descripcion', 'geom', 'nivel_alerta', 'fecha_inicio', 'fecha_fin', 'heridos', 'fallecidos', 'damnificados']
        widgets = {
            'evento': forms.Select(attrs={'class': 'form-select'}),
            'nombre': forms.TextInput(attrs={'class': 'form-control', 'maxlength': 200}),
            'descripcion': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'maxlength': 2000}),
            'geom': forms.HiddenInput(),
            'nivel_alerta': forms.Select(attrs={'class': 'form-select'}),
            'fecha_inicio': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
            'fecha_fin': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
            'heridos': forms.NumberInput(attrs={'class': 'form-control', 'min': 0, 'step': 1, 'inputmode': 'numeric'}),
            'fallecidos': forms.NumberInput(attrs={'class': 'form-control', 'min': 0, 'step': 1, 'inputmode': 'numeric'}),
            'damnificados': forms.NumberInput(attrs={'class': 'form-control', 'min': 0, 'step': 1, 'inputmode': 'numeric'}),
        }

    def clean_nombre(self):
        return validar_nombre_operativo(self.cleaned_data.get('nombre'))

    def clean_fecha_inicio(self):
        from django.utils import timezone
        from datetime import timedelta
        fecha = self.cleaned_data.get('fecha_inicio')
        if fecha is None:
            return fecha
        ahora = timezone.now()
        if fecha > ahora + timedelta(minutes=5):
            raise forms.ValidationError('La fecha de inicio no puede estar en el futuro.')
        if fecha.year < 1900:
            raise forms.ValidationError('La fecha de inicio no puede ser anterior a 1900.')
        return fecha

    def clean_heridos(self):
        valor = self.cleaned_data.get('heridos')
        if valor is None or valor < 0:
            raise forms.ValidationError('El número de heridos no puede ser negativo.')
        return valor

    def clean_fallecidos(self):
        valor = self.cleaned_data.get('fallecidos')
        if valor is None or valor < 0:
            raise forms.ValidationError('El número de fallecidos no puede ser negativo.')
        return valor

    def clean_damnificados(self):
        valor = self.cleaned_data.get('damnificados')
        if valor is None or valor < 0:
            raise forms.ValidationError('El número de damnificados no puede ser negativo.')
        return valor

    def clean_geom(self):
        valor = self.cleaned_data.get('geom')
        if isinstance(valor, GEOSGeometry):
            return valor
        if isinstance(valor, str):
            try:
                geometria = GEOSGeometry(valor)
            except Exception:
                raise forms.ValidationError('La zona dibujada no es válida.')
            if geometria.geom_type != 'Polygon':
                raise forms.ValidationError('La zona afectada debe ser un área cerrada.')
            if geometria.srid is None:
                geometria.srid = 4326
            elif geometria.srid != 4326:
                geometria.transform(4326)
            return geometria
        raise forms.ValidationError('Dibuja la zona afectada en el mapa.')

    def clean(self):
        cleaned = super().clean()
        inicio = cleaned.get('fecha_inicio')
        fin = cleaned.get('fecha_fin')
        if inicio and fin and fin < inicio:
            self.add_error('fecha_fin', 'La fecha de finalización no puede ser anterior al inicio.')
        return cleaned


# ============================================================
# FORMULARIOS EXPLÍCITOS PARA MODELOS DEL PANEL
# ============================================================
# Reemplazan el fallback modelform_factory(fields='__all__') del CRUD.
# Ver FASE 1 del Plan Maestro v2 (hallazgo C7).
# Los imports se agregan al inicio del módulo.

class EstadoForm(forms.ModelForm):
    """Formulario explícito para Estados.

    La geometría se edita exclusivamente desde el Django admin (GISModelAdmin).
    Este formulario valida nombre y código INE para el CRUD operativo.
    """
    class Meta:
        model = Estado
        fields = ['nombre', 'codigo_ine']
        widgets = {
            'nombre': forms.TextInput(attrs={
                'class': 'form-control', 'maxlength': 100,
                'placeholder': 'Ej.: Miranda',
            }),
            'codigo_ine': forms.TextInput(attrs={
                'class': 'form-control', 'maxlength': 10,
                'placeholder': 'Ej.: 15',
            }),
        }

    def clean_nombre(self):
        return validar_nombre_operativo(self.cleaned_data.get('nombre'))

    def clean_codigo_ine(self):
        codigo = (self.cleaned_data.get('codigo_ine') or '').strip()
        if codigo and not codigo.isdigit():
            raise forms.ValidationError('El código INE debe contener solo dígitos.')
        return codigo


class ParroquiaForm(forms.ModelForm):
    """Formulario explícito para Parroquias.

    La geometría se edita exclusivamente desde el Django admin (GISModelAdmin).
    """
    class Meta:
        model = Parroquia
        fields = [
            'nombre', 'estado', 'codigo_ine',
            'poblacion', 'densidad_poblacional', 'indice_vulnerabilidad',
        ]
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'form-control', 'maxlength': 100}),
            'estado': forms.Select(attrs={'class': 'form-select'}),
            'codigo_ine': forms.TextInput(attrs={'class': 'form-control', 'maxlength': 10}),
            'poblacion': forms.NumberInput(attrs={
                'class': 'form-control', 'min': 0, 'step': 1, 'inputmode': 'numeric',
            }),
            'densidad_poblacional': forms.NumberInput(attrs={
                'class': 'form-control', 'min': 0, 'step': '0.01', 'inputmode': 'decimal',
            }),
            'indice_vulnerabilidad': forms.NumberInput(attrs={
                'class': 'form-control', 'min': 0, 'max': 1, 'step': '0.01', 'inputmode': 'decimal',
            }),
        }
        help_texts = {
            'indice_vulnerabilidad': 'Valor entre 0 (baja) y 1 (alta).',
            'densidad_poblacional': 'Habitantes por km².',
        }

    def clean_nombre(self):
        return validar_nombre_operativo(self.cleaned_data.get('nombre'))

    def clean_codigo_ine(self):
        codigo = (self.cleaned_data.get('codigo_ine') or '').strip()
        if codigo and not codigo.isdigit():
            raise forms.ValidationError('El código INE debe contener solo dígitos.')
        return codigo


class ParametrosModeloForm(forms.ModelForm):
    """Formulario explícito para los parámetros de modelos de optimización."""
    class Meta:
        model = ParametrosModelo
        fields = [
            'nombre_escenario', 'tipo_modelo', 'p', 'presupuesto', 'radio_cobertura',
            'ponderador_vulnerabilidad', 'ponderador_heridos',
            'ponderador_fallecidos', 'ponderador_damnificados',
            'filtro_estado',
        ]
        widgets = {
            'nombre_escenario': forms.TextInput(attrs={'class': 'form-control', 'maxlength': 200}),
            'tipo_modelo': forms.Select(attrs={'class': 'form-select'}),
            'p': forms.NumberInput(attrs={
                'class': 'form-control', 'min': 1, 'step': 1, 'inputmode': 'numeric',
            }),
            'presupuesto': forms.NumberInput(attrs={
                'class': 'form-control', 'min': 0, 'step': '0.01', 'inputmode': 'decimal',
            }),
            'radio_cobertura': forms.NumberInput(attrs={
                'class': 'form-control', 'min': 0, 'step': 100, 'inputmode': 'numeric',
            }),
            'ponderador_vulnerabilidad': forms.NumberInput(attrs={
                'class': 'form-control', 'min': 0, 'step': '0.1', 'inputmode': 'decimal',
            }),
            'ponderador_heridos': forms.NumberInput(attrs={
                'class': 'form-control', 'min': 0, 'step': '0.1', 'inputmode': 'decimal',
            }),
            'ponderador_fallecidos': forms.NumberInput(attrs={
                'class': 'form-control', 'min': 0, 'step': '0.1', 'inputmode': 'decimal',
            }),
            'ponderador_damnificados': forms.NumberInput(attrs={
                'class': 'form-control', 'min': 0, 'step': '0.1', 'inputmode': 'decimal',
            }),
            'filtro_estado': forms.Select(attrs={'class': 'form-select'}),
        }
        help_texts = {'radio_cobertura': 'Metros.'}

    def clean_nombre_escenario(self):
        return validar_nombre_operativo(
            self.cleaned_data.get('nombre_escenario'),
            etiqueta='El nombre del escenario',
        )

    def clean_p(self):
        p = self.cleaned_data.get('p')
        if p is None or p < 1:
            raise forms.ValidationError('El número de centros debe ser al menos 1.')
        if p > 1000:
            raise forms.ValidationError('El número de centros no debe superar 1000.')
        return p

    def clean_presupuesto(self):
        valor = self.cleaned_data.get('presupuesto')
        if valor is not None and valor < 0:
            raise forms.ValidationError('El presupuesto no puede ser negativo.')
        return valor

    def clean_radio_cobertura(self):
        valor = self.cleaned_data.get('radio_cobertura')
        if valor is None or valor < 0:
            raise forms.ValidationError('El radio de cobertura no puede ser negativo.')
        if valor > 500000:
            raise forms.ValidationError('El radio de cobertura no debe superar los 500 km (500000 m).')
        return valor

    def clean(self):
        cleaned = super().clean()
        for campo, etiqueta in (
            ('ponderador_vulnerabilidad', 'vulnerabilidad'),
            ('ponderador_heridos', 'heridos'),
            ('ponderador_fallecidos', 'fallecidos'),
            ('ponderador_damnificados', 'damnificados'),
        ):
            valor = cleaned.get(campo)
            if valor is not None and valor < 0:
                self.add_error(campo, f'El ponderador de {etiqueta} no puede ser negativo.')
        return cleaned


class EventoForm(forms.ModelForm):
    """Formulario explícito para eventos de emergencia."""
    class Meta:
        model = Evento
        fields = ['nombre', 'tipo', 'fecha', 'magnitud', 'descripcion', 'activo']
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'form-control', 'maxlength': 200}),
            'tipo': forms.Select(attrs={'class': 'form-select'}),
            'fecha': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
            'magnitud': forms.NumberInput(attrs={
                'class': 'form-control', 'min': 0, 'step': '0.01', 'inputmode': 'decimal',
            }),
            'descripcion': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'maxlength': 2000}),
            'activo': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def clean_nombre(self):
        return validar_nombre_operativo(self.cleaned_data.get('nombre'))

    def clean_magnitud(self):
        valor = self.cleaned_data.get('magnitud')
        if valor is not None and valor < 0:
            raise forms.ValidationError('La magnitud no puede ser negativa.')
        return valor

    def clean_fecha(self):
        from django.utils import timezone
        from datetime import timedelta
        fecha = self.cleaned_data.get('fecha')
        if fecha is None:
            return fecha
        ahora = timezone.now()
        if fecha > ahora + timedelta(minutes=5):
            raise forms.ValidationError('La fecha del evento no puede estar en el futuro. Los eventos son hechos ya ocurridos.')
        if fecha.year < 1900:
            raise forms.ValidationError('La fecha del evento no puede ser anterior a 1900.')
        return fecha


class ReporteForm(forms.ModelForm):
    """Formulario explícito para reportes ciudadanos desde el panel administrativo."""
    class Meta:
        model = Reporte
        fields = ['autor', 'texto', 'zona_afectada', 'punto_demanda', 'imagen', 'verificado']
        widgets = {
            'autor': forms.TextInput(attrs={
                'class': 'form-control', 'maxlength': 100, 'placeholder': 'Ej.: María Pérez',
            }),
            'texto': forms.Textarea(attrs={'class': 'form-control', 'rows': 5, 'maxlength': 2000}),
            'zona_afectada': forms.Select(attrs={'class': 'form-select'}),
            'punto_demanda': forms.Select(attrs={'class': 'form-select'}),
            'imagen': forms.FileInput(attrs={'class': 'form-control', 'accept': 'image/*'}),
            'verificado': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def clean_texto(self):
        texto = (self.cleaned_data.get('texto') or '').strip()
        if len(texto) < 10:
            raise forms.ValidationError('La descripción debe tener al menos 10 caracteres.')
        if len(texto) > 2000:
            raise forms.ValidationError('La descripción no puede superar los 2000 caracteres.')
        return texto

    def clean_autor(self):
        autor = (self.cleaned_data.get('autor') or '').strip()
        if autor:
            validar_texto_sin_numeros_ni_especiales(autor)
        return autor[:100]
