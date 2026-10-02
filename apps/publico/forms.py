"""Formularios del portal público con validación estricta y mensajes humanos."""
from django import forms
from django.core.validators import FileExtensionValidator

from apps.emergencias.models import Reporte
from apps.core.models import ZonaAfectada, PuntoDemanda
from apps.core.validators import validar_texto_sin_numeros_ni_especiales

TAMANO_MAX_IMAGEN_MB = 5
EXTENSIONES_IMAGEN = ['jpg', 'jpeg', 'png', 'gif', 'webp']


class ReporteCiudadanoForm(forms.ModelForm):
    class Meta:
        model = Reporte
        fields = ['autor', 'texto', 'zona_afectada', 'punto_demanda', 'imagen']
        widgets = {
            'autor': forms.TextInput(attrs={
                'placeholder': 'Ej: María Pérez', 'class': 'form-control',
                'autocomplete': 'name', 'maxlength': 100,
                'inputmode': 'text',
            }),
            'texto': forms.Textarea(attrs={
                'rows': 5,
                'placeholder': 'Describa la emergencia, necesidad o situación que desea reportar...',
                'class': 'form-control textarea', 'maxlength': 2000,
            }),
            'zona_afectada': forms.Select(attrs={'class': 'form-control'}),
            'punto_demanda': forms.Select(attrs={'class': 'form-control'}),
            'imagen': forms.FileInput(attrs={'class': 'file-input', 'accept': 'image/*'}),
        }
        labels = {
            'autor': 'Su Nombre', 'texto': 'Describa la Situación',
            'zona_afectada': 'Zona Afectada', 'punto_demanda': 'Comunidad o Sector',
            'imagen': 'Adjuntar Imagen',
        }
        help_texts = {
            'autor': '(opcional)', 'zona_afectada': '(opcional)',
            'punto_demanda': '(opcional)',
            'imagen': f'Formatos: JPG, PNG, GIF, WEBP · Máx {TAMANO_MAX_IMAGEN_MB} MB',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for campo in ('autor', 'zona_afectada', 'punto_demanda', 'imagen'):
            self.fields[campo].required = False
        self.fields['imagen'].validators.append(
            FileExtensionValidator(allowed_extensions=EXTENSIONES_IMAGEN)
        )
        self.fields['zona_afectada'].queryset = ZonaAfectada.objects.filter(
            fecha_fin__isnull=True
        ).order_by('nombre')[:200]
        self.fields['punto_demanda'].queryset = PuntoDemanda.objects.order_by('nombre')[:200]

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

    def clean_imagen(self):
        imagen = self.cleaned_data.get('imagen')
        if imagen and imagen.size > TAMANO_MAX_IMAGEN_MB * 1024 * 1024:
            raise forms.ValidationError(f'La imagen no debe superar los {TAMANO_MAX_IMAGEN_MB} MB.')
        return imagen


class BusquedaForm(forms.Form):
    query = forms.CharField(
        max_length=100, required=False,
        widget=forms.TextInput(attrs={
            'placeholder': 'Buscar estado, parroquia, refugio...',
            'class': 'form-control', 'id': 'buscar', 'autocomplete': 'off',
        }),
    )

    def clean_query(self):
        return (self.cleaned_data.get('query') or '').strip()
