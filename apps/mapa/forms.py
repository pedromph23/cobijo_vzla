"""
Formularios del panel administrativo.

Incluye métodos clean_* para convertir correctamente los inputs de texto
en geometrías GEOS y otros tipos complejos.
"""
from django import forms
from django.contrib.gis.geos import Point, GEOSGeometry

from apps.core.models import PuntoDemanda, SitioCandidato, RefugioExistente, ZonaAfectada
from apps.emergencias.models import Evento
from apps.core.validators import validar_texto_sin_numeros_ni_especiales, validar_telefono


# ============================================================
# HELPERS
# ============================================================
def _parsear_punto(valor) -> Point:
    if isinstance(valor, Point):
        return valor
    if not isinstance(valor, str):
        raise forms.ValidationError("Formato de coordenadas inválido.")
    partes = valor.replace(',', ' ').split()
    if len(partes) < 2:
        raise forms.ValidationError("Se requieren dos coordenadas. Formato: 'lng,lat'.")
    try:
        lng, lat = float(partes[0]), float(partes[1])
    except ValueError:
        raise forms.ValidationError("Las coordenadas deben ser numéricas.")
    if not (-180 <= lng <= 180) or not (-90 <= lat <= 90):
        raise forms.ValidationError("Coordenadas fuera de rango.")
    return Point(lng, lat, srid=4326)


class PuntoDemandaForm(forms.ModelForm):
    class Meta:
        model = PuntoDemanda
        fields = ['nombre', 'parroquia', 'ubicacion', 'poblacion', 'vulnerabilidad', 'descripcion']
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'form-control', 'maxlength': 200}),
            'parroquia': forms.Select(attrs={'class': 'form-select'}),
            'ubicacion': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'lng,lat'}),
            'poblacion': forms.NumberInput(attrs={'class': 'form-control', 'min': 0, 'step': 1}),
            'vulnerabilidad': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.1', 'min': 0, 'max': 1}),
            'descripcion': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

    def clean_nombre(self):
        value = self.cleaned_data.get('nombre', '').strip()
        validar_texto_sin_numeros_ni_especiales(value)
        return value

    def clean_ubicacion(self):
        return _parsear_punto(self.cleaned_data.get('ubicacion'))


class SitioCandidatoForm(forms.ModelForm):
    class Meta:
        model = SitioCandidato
        fields = ['nombre', 'ubicacion', 'capacidad_maxima', 'costo_apertura', 'costo_operacion', 'tipo_terreno', 'disponible']
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'form-control', 'maxlength': 200}),
            'ubicacion': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'lng,lat'}),
            'capacidad_maxima': forms.NumberInput(attrs={'class': 'form-control', 'min': 1, 'step': 1}),
            'costo_apertura': forms.NumberInput(attrs={'class': 'form-control', 'min': 0, 'step': '0.01'}),
            'costo_operacion': forms.NumberInput(attrs={'class': 'form-control', 'min': 0, 'step': '0.01'}),
            'tipo_terreno': forms.TextInput(attrs={'class': 'form-control', 'maxlength': 50}),
            'disponible': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def clean_nombre(self):
        value = self.cleaned_data.get('nombre', '').strip()
        validar_texto_sin_numeros_ni_especiales(value)
        return value

    def clean_tipo_terreno(self):
        value = self.cleaned_data.get('tipo_terreno', '').strip()
        if value:
            validar_texto_sin_numeros_ni_especiales(value)
        return value

    def clean_ubicacion(self):
        return _parsear_punto(self.cleaned_data.get('ubicacion'))


class RefugioExistenteForm(forms.ModelForm):
    class Meta:
        model = RefugioExistente
        fields = ['nombre', 'direccion', 'ubicacion', 'capacidad_total', 'capacidad_disponible', 'servicios', 'operativo', 'telefono', 'horario']
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'form-control', 'maxlength': 200}),
            'direccion': forms.TextInput(attrs={'class': 'form-control', 'maxlength': 300}),
            'ubicacion': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'lng,lat'}),
            'capacidad_total': forms.NumberInput(attrs={'class': 'form-control', 'min': 0, 'step': 1}),
            'capacidad_disponible': forms.NumberInput(attrs={'class': 'form-control', 'min': 0, 'step': 1}),
            'servicios': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'agua, comida, medicina'}),
            'operativo': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'telefono': forms.TextInput(attrs={'class': 'form-control', 'inputmode': 'tel', 'autocomplete': 'tel'}),
            'horario': forms.TextInput(attrs={'class': 'form-control', 'maxlength': 100}),
        }

    def clean_nombre(self):
        value = self.cleaned_data.get('nombre', '').strip()
        validar_texto_sin_numeros_ni_especiales(value)
        return value

    def clean_telefono(self):
        value = self.cleaned_data.get('telefono', '').strip()
        validar_telefono(value)
        return value

    def clean_ubicacion(self):
        return _parsear_punto(self.cleaned_data.get('ubicacion'))

    def clean_servicios(self):
        valor = self.cleaned_data.get('servicios')
        if isinstance(valor, str):
            return [s.strip() for s in valor.split(',') if s.strip()]
        if isinstance(valor, list):
            return [str(s).strip() for s in valor if str(s).strip()]
        return []

    def clean(self):
        cleaned = super().clean()
        total = cleaned.get('capacidad_total') or 0
        disponible = cleaned.get('capacidad_disponible') or 0
        if disponible > total:
            self.add_error('capacidad_disponible', f'La capacidad disponible ({disponible}) no puede superar la capacidad total ({total}).')
        return cleaned


class ZonaAfectadaForm(forms.ModelForm):
    class Meta:
        model = ZonaAfectada
        fields = ['evento', 'nombre', 'descripcion', 'geom', 'nivel_alerta', 'fecha_inicio', 'fecha_fin', 'heridos', 'fallecidos', 'damnificados']
        widgets = {
            'evento': forms.Select(attrs={'class': 'form-select'}),
            'nombre': forms.TextInput(attrs={'class': 'form-control', 'maxlength': 200}),
            'descripcion': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'geom': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'nivel_alerta': forms.Select(attrs={'class': 'form-select'}),
            'fecha_inicio': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
            'fecha_fin': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
            'heridos': forms.NumberInput(attrs={'class': 'form-control', 'min': 0, 'step': 1}),
            'fallecidos': forms.NumberInput(attrs={'class': 'form-control', 'min': 0, 'step': 1}),
            'damnificados': forms.NumberInput(attrs={'class': 'form-control', 'min': 0, 'step': 1}),
        }

    def clean_nombre(self):
        value = self.cleaned_data.get('nombre', '').strip()
        validar_texto_sin_numeros_ni_especiales(value)
        return value

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
