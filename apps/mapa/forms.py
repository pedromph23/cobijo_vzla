"""
Formularios del panel administrativo.

La interfaz oculta la representación técnica de las coordenadas y ofrece
controles sencillos para los datos operativos. La conversión final sigue
centralizada en el formulario Django.
"""
from django import forms
from django.contrib.gis.geos import Point, GEOSGeometry

from apps.core.models import PuntoDemanda, SitioCandidato, RefugioExistente, ZonaAfectada
from apps.emergencias.models import Evento
from apps.core.validators import validar_telefono


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


def _parsear_punto(valor) -> Point:
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
    return Point(lng, lat, srid=4326)


UBICACION_WIDGET = forms.HiddenInput()


class PuntoDemandaForm(forms.ModelForm):
    class Meta:
        model = PuntoDemanda
        fields = ['nombre', 'ubicacion', 'poblacion', 'vulnerabilidad', 'descripcion']
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'form-control', 'maxlength': 200}),
            'ubicacion': UBICACION_WIDGET,
            'poblacion': forms.NumberInput(attrs={'class': 'form-control', 'min': 0, 'step': 1, 'inputmode': 'numeric'}),
            'vulnerabilidad': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.1', 'min': 0, 'max': 1, 'inputmode': 'decimal'}),
            'descripcion': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'maxlength': 2000}),
        }

    def clean_ubicacion(self):
        return _parsear_punto(self.cleaned_data.get('ubicacion'))


class SitioCandidatoForm(forms.ModelForm):
    class Meta:
        model = SitioCandidato
        fields = ['nombre', 'ubicacion', 'capacidad_maxima', 'costo_apertura', 'costo_operacion', 'tipo_terreno', 'disponible']
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'form-control', 'maxlength': 200}),
            'ubicacion': UBICACION_WIDGET,
            'capacidad_maxima': forms.NumberInput(attrs={'class': 'form-control', 'min': 1, 'step': 1, 'inputmode': 'numeric'}),
            'costo_apertura': forms.NumberInput(attrs={'class': 'form-control', 'min': 0, 'step': '0.01', 'inputmode': 'decimal'}),
            'costo_operacion': forms.NumberInput(attrs={'class': 'form-control', 'min': 0, 'step': '0.01', 'inputmode': 'decimal'}),
            'tipo_terreno': forms.TextInput(attrs={'class': 'form-control', 'maxlength': 50}),
            'disponible': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def clean_ubicacion(self):
        return _parsear_punto(self.cleaned_data.get('ubicacion'))


class RefugioExistenteForm(forms.ModelForm):
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
            'ubicacion': UBICACION_WIDGET,
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
            'geom': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'nivel_alerta': forms.Select(attrs={'class': 'form-select'}),
            'fecha_inicio': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
            'fecha_fin': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
            'heridos': forms.NumberInput(attrs={'class': 'form-control', 'min': 0, 'step': 1, 'inputmode': 'numeric'}),
            'fallecidos': forms.NumberInput(attrs={'class': 'form-control', 'min': 0, 'step': 1, 'inputmode': 'numeric'}),
            'damnificados': forms.NumberInput(attrs={'class': 'form-control', 'min': 0, 'step': 1, 'inputmode': 'numeric'}),
        }

    def clean_geom(self):
        valor = self.cleaned_data.get('geom')
        if isinstance(valor, GEOSGeometry):
            return valor
        if isinstance(valor, str):
            try:
                return GEOSGeometry(valor)
            except Exception:
                raise forms.ValidationError('La geometría proporcionada no es válida.')
        return valor

    def clean(self):
        cleaned = super().clean()
        inicio = cleaned.get('fecha_inicio')
        fin = cleaned.get('fecha_fin')
        if inicio and fin and fin < inicio:
            self.add_error('fecha_fin', 'La fecha de finalización no puede ser anterior al inicio.')
        return cleaned
