"""
Formularios del panel administrativo.

Incluye métodos clean_* para convertir correctamente los inputs de texto
en geometrías GEOS y otros tipos complejos.
"""
from django import forms
from django.contrib.gis.geos import Point, GEOSGeometry

from apps.core.models import (
    PuntoDemanda,
    SitioCandidato,
    RefugioExistente,
    ZonaAfectada,
)
from apps.emergencias.models import Evento


# ============================================================
# HELPERS
# ============================================================

def _parsear_punto(valor) -> Point:
    """
    Convierte un string 'lng,lat' (o 'lng lat') en un Point GEOS.

    Acepta:
        "-66.9036,10.4806"
        "-66.9036 10.4806"
    """
    if isinstance(valor, Point):
        return valor
    if not isinstance(valor, str):
        raise forms.ValidationError("Formato de coordenadas inválido.")

    partes = valor.replace(',', ' ').split()
    if len(partes) < 2:
        raise forms.ValidationError(
            "Se requieren dos coordenadas. Formato: 'lng,lat' (ej: -66.9036,10.4806)"
        )

    try:
        lng, lat = float(partes[0]), float(partes[1])
    except ValueError:
        raise forms.ValidationError(
            f"Coordenadas no numéricas: '{partes[0]}', '{partes[1]}'"
        )

    if not (-180 <= lng <= 180) or not (-90 <= lat <= 90):
        raise forms.ValidationError(
            f"Coordenadas fuera de rango. lng∈[-180,180], lat∈[-90,90]. "
            f"Recibido: lng={lng}, lat={lat}"
        )

    return Point(lng, lat, srid=4326)


# ============================================================
# PUNTO DE DEMANDA
# ============================================================

class PuntoDemandaForm(forms.ModelForm):
    class Meta:
        model = PuntoDemanda
        fields = ['nombre', 'parroquia', 'ubicacion', 'poblacion',
                  'vulnerabilidad', 'descripcion']
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'form-control'}),
            'parroquia': forms.Select(attrs={'class': 'form-select'}),
            'ubicacion': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Coordenadas (lng, lat). Ej: -66.9036,10.4806',
            }),
            'poblacion': forms.NumberInput(attrs={'class': 'form-control', 'min': 0}),
            'vulnerabilidad': forms.NumberInput(attrs={
                'class': 'form-control', 'step': '0.1', 'min': 0, 'max': 1,
            }),
            'descripcion': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

    def clean_ubicacion(self):
        return _parsear_punto(self.cleaned_data.get('ubicacion'))


# ============================================================
# SITIO CANDIDATO
# ============================================================

class SitioCandidatoForm(forms.ModelForm):
    class Meta:
        model = SitioCandidato
        fields = ['nombre', 'ubicacion', 'capacidad_maxima',
                  'costo_apertura', 'costo_operacion',
                  'tipo_terreno', 'disponible']
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'form-control'}),
            'ubicacion': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Coordenadas (lng, lat). Ej: -66.9036,10.4806',
            }),
            'capacidad_maxima': forms.NumberInput(attrs={'class': 'form-control', 'min': 1}),
            'costo_apertura': forms.NumberInput(attrs={'class': 'form-control', 'min': 0, 'step': '0.01'}),
            'costo_operacion': forms.NumberInput(attrs={'class': 'form-control', 'min': 0, 'step': '0.01'}),
            'tipo_terreno': forms.TextInput(attrs={'class': 'form-control'}),
            'disponible': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def clean_ubicacion(self):
        return _parsear_punto(self.cleaned_data.get('ubicacion'))


# ============================================================
# REFUGIO EXISTENTE
# ============================================================

class RefugioExistenteForm(forms.ModelForm):
    class Meta:
        model = RefugioExistente
        fields = ['nombre', 'direccion', 'ubicacion',
                  'capacidad_total', 'capacidad_disponible',
                  'servicios', 'operativo', 'telefono', 'horario']
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'form-control'}),
            'direccion': forms.TextInput(attrs={'class': 'form-control'}),
            'ubicacion': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Coordenadas (lng, lat). Ej: -66.9036,10.4806',
            }),
            'capacidad_total': forms.NumberInput(attrs={'class': 'form-control', 'min': 0}),
            'capacidad_disponible': forms.NumberInput(attrs={'class': 'form-control', 'min': 0}),
            'servicios': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'agua, comida, medicina',
            }),
            'operativo': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'telefono': forms.TextInput(attrs={'class': 'form-control'}),
            'horario': forms.TextInput(attrs={'class': 'form-control'}),
        }

    def clean_ubicacion(self):
        return _parsear_punto(self.cleaned_data.get('ubicacion'))

    def clean_servicios(self):
        """Convierte 'agua, comida' en ['agua', 'comida']."""
        valor = self.cleaned_data.get('servicios')
        if isinstance(valor, str):
            return [s.strip() for s in valor.split(',') if s.strip()]
        if isinstance(valor, list):
            return [str(s).strip() for s in valor if str(s).strip()]
        return []

    def clean(self):
        """Valida que capacidad_disponible <= capacidad_total."""
        cleaned = super().clean()
        total = cleaned.get('capacidad_total') or 0
        disponible = cleaned.get('capacidad_disponible') or 0
        if disponible > total:
            self.add_error(
                'capacidad_disponible',
                f"La capacidad disponible ({disponible}) no puede superar "
                f"la capacidad total ({total})."
            )
        return cleaned


# ============================================================
# ZONA AFECTADA
# ============================================================

class ZonaAfectadaForm(forms.ModelForm):
    class Meta:
        model = ZonaAfectada
        fields = ['evento', 'nombre', 'descripcion', 'geom',
                  'nivel_alerta', 'fecha_inicio', 'fecha_fin',
                  'heridos', 'fallecidos', 'damnificados']
        widgets = {
            'evento': forms.Select(attrs={'class': 'form-select'}),
            'nombre': forms.TextInput(attrs={'class': 'form-control'}),
            'descripcion': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'geom': forms.Textarea(attrs={
                'class': 'form-control', 'rows': 3,
                'placeholder': 'WKT o GeoJSON. Ej: POINT(-66.9 10.5) o POLYGON((...))',
            }),
            'nivel_alerta': forms.Select(attrs={'class': 'form-select'}),
            'fecha_inicio': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
            'fecha_fin': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
            'heridos': forms.NumberInput(attrs={'class': 'form-control', 'min': 0}),
            'fallecidos': forms.NumberInput(attrs={'class': 'form-control', 'min': 0}),
            'damnificados': forms.NumberInput(attrs={'class': 'form-control', 'min': 0}),
        }

    def clean_geom(self):
        """Convierte WKT/GeoJSON en GEOSGeometry."""
        valor = self.cleaned_data.get('geom')
        if isinstance(valor, GEOSGeometry):
            return valor
        if isinstance(valor, str):
            try:
                return GEOSGeometry(valor)
            except Exception as e:
                raise forms.ValidationError(f"Geometría inválida: {e}")
        return valor