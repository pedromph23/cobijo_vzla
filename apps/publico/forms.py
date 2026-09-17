"""
Formularios para la aplicación pública de CobijoVzla.
"""

from django import forms
from apps.emergencias.models import Reporte
from apps.core.models import ZonaAfectada, PuntoDemanda


class ReporteCiudadanoForm(forms.ModelForm):
    """
    Formulario para que los ciudadanos envíen reportes de emergencias.
    """
    
    class Meta:
        model = Reporte
        fields = ['autor', 'texto', 'zona_afectada', 'punto_demanda', 'imagen']
        widgets = {
            'autor': forms.TextInput(attrs={
                'placeholder': 'Ej: María Pérez',
                'class': 'form-control',
                'autocomplete': 'name',
            }),
            'texto': forms.Textarea(attrs={
                'rows': 5,
                'placeholder': 'Describa la emergencia, necesidad o situación que desea reportar...',
                'class': 'form-control textarea',
                'maxlength': 500,
            }),
            'zona_afectada': forms.Select(attrs={
                'class': 'form-control',
            }),
            'punto_demanda': forms.Select(attrs={
                'class': 'form-control',
            }),
            'imagen': forms.FileInput(attrs={
                'class': 'file-input',
                'accept': 'image/*',
            }),
        }
        labels = {
            'autor': 'Su Nombre',
            'texto': 'Describa la Situación',
            'zona_afectada': 'Zona Afectada',
            'punto_demanda': 'Comunidad o Sector',
            'imagen': 'Adjuntar Imagen',
        }
        help_texts = {
            'autor': '(opcional)',
            'zona_afectada': '(opcional)',
            'punto_demanda': '(opcional)',
            'imagen': 'Formatos: JPG, PNG, GIF - Máx 5MB',
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Hacer campos opcionales
        self.fields['autor'].required = False
        self.fields['zona_afectada'].required = False
        self.fields['punto_demanda'].required = False
        self.fields['imagen'].required = False
        
        # Filtrar zonas afectadas activas
        self.fields['zona_afectada'].queryset = ZonaAfectada.objects.filter(
            fecha_fin__isnull=True
        ).order_by('nombre')
        
        # Filtrar puntos de demanda (limitar a 100 para no sobrecargar)
        self.fields['punto_demanda'].queryset = PuntoDemanda.objects.all()[:100]
    
    def clean_texto(self):
        """
        Valida que el texto tenga al menos 10 caracteres.
        """
        texto = self.cleaned_data.get('texto', '').strip()
        
        if len(texto) < 10:
            raise forms.ValidationError(
                'La descripción debe tener al menos 10 caracteres.'
            )
        
        return texto
    
    def clean_imagen(self):
        """
        Valida que la imagen no supere 5MB.
        """
        imagen = self.cleaned_data.get('imagen')
        
        if imagen:
            if imagen.size > 5 * 1024 * 1024:
                raise forms.ValidationError(
                    'La imagen no debe superar los 5MB.'
                )
            
            # Validar tipo de archivo
            import os
            extension = os.path.splitext(imagen.name)[1].lower()
            extensiones_permitidas = ['.jpg', '.jpeg', '.png', '.gif']
            
            if extension not in extensiones_permitidas:
                raise forms.ValidationError(
                    'Formato de imagen no permitido. Use JPG, PNG o GIF.'
                )
        
        return imagen


class BusquedaForm(forms.Form):
    """
    Formulario para búsqueda de lugares.
    """
    query = forms.CharField(
        max_length=200,
        required=False,
        widget=forms.TextInput(attrs={
            'placeholder': 'Buscar estado, parroquia, refugio...',
            'class': 'form-control',
            'id': 'buscar',
            'autocomplete': 'off',
        })
    )