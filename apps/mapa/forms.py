from django import forms
from apps.core.models import PuntoDemanda, SitioCandidato, RefugioExistente, ZonaAfectada
from apps.emergencias.models import Evento

class PuntoDemandaForm(forms.ModelForm):
    class Meta:
        model = PuntoDemanda
        fields = ['nombre', 'parroquia', 'ubicacion', 'poblacion', 'vulnerabilidad', 'descripcion']
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'form-control'}),
            'parroquia': forms.Select(attrs={'class': 'form-select'}),
            'ubicacion': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Coordenadas (lng, lat)'}),
            'poblacion': forms.NumberInput(attrs={'class': 'form-control'}),
            'vulnerabilidad': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.1', 'min': '0', 'max': '1'}),
            'descripcion': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

class SitioCandidatoForm(forms.ModelForm):
    class Meta:
        model = SitioCandidato
        fields = ['nombre', 'ubicacion', 'capacidad_maxima', 'costo_apertura', 'costo_operacion', 'tipo_terreno', 'disponible']
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'form-control'}),
            'ubicacion': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Coordenadas (lng, lat)'}),
            'capacidad_maxima': forms.NumberInput(attrs={'class': 'form-control'}),
            'costo_apertura': forms.NumberInput(attrs={'class': 'form-control'}),
            'costo_operacion': forms.NumberInput(attrs={'class': 'form-control'}),
            'tipo_terreno': forms.TextInput(attrs={'class': 'form-control'}),
            'disponible': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

class RefugioExistenteForm(forms.ModelForm):
    class Meta:
        model = RefugioExistente
        fields = ['nombre', 'direccion', 'ubicacion', 'capacidad_total', 'capacidad_disponible', 'servicios', 'operativo', 'telefono', 'horario']
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'form-control'}),
            'direccion': forms.TextInput(attrs={'class': 'form-control'}),
            'ubicacion': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Coordenadas (lng, lat)'}),
            'capacidad_total': forms.NumberInput(attrs={'class': 'form-control'}),
            'capacidad_disponible': forms.NumberInput(attrs={'class': 'form-control'}),
            'servicios': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Lista separada por comas'}),
            'operativo': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'telefono': forms.TextInput(attrs={'class': 'form-control'}),
            'horario': forms.TextInput(attrs={'class': 'form-control'}),
        }

class ZonaAfectadaForm(forms.ModelForm):
    class Meta:
        model = ZonaAfectada
        fields = ['evento', 'nombre', 'descripcion', 'geom', 'nivel_alerta', 'fecha_inicio', 'fecha_fin', 'heridos', 'fallecidos', 'damnificados']
        widgets = {
            'evento': forms.Select(attrs={'class': 'form-select'}),
            'nombre': forms.TextInput(attrs={'class': 'form-control'}),
            'descripcion': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'geom': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Coordenadas (lng, lat) o polígono'}),
            'nivel_alerta': forms.Select(attrs={'class': 'form-select'}),
            'fecha_inicio': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
            'fecha_fin': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
            'heridos': forms.NumberInput(attrs={'class': 'form-control'}),
            'fallecidos': forms.NumberInput(attrs={'class': 'form-control'}),
            'damnificados': forms.NumberInput(attrs={'class': 'form-control'}),
        }