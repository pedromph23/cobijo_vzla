from django.test import TestCase
from django.contrib.gis.geos import Point

from apps.core.models import RefugioExistente
from apps.mapa.forms import RefugioExistenteForm


class RefugioServiciosFormTest(TestCase):
    def datos(self, **extra):
        data = {
            'nombre': 'Refugio de prueba',
            'direccion': 'Av. Sucre, Caracas',
            'ubicacion': '-66.9,10.5',
            'capacidad_total': 100,
            'capacidad_disponible': 80,
            'servicios': ['agua', 'medicina'],
            'otros_servicios': 'Colchonetas, alimentos secos',
            'operativo': True,
            'telefono': '',
            'horario': '',
        }
        data.update(extra)
        return data

    def test_convierte_opciones_y_otros_en_una_lista(self):
        form = RefugioExistenteForm(data=self.datos())
        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(
            form.cleaned_data['servicios'],
            ['agua', 'medicina', 'Colchonetas', 'alimentos secos'],
        )

    def test_edicion_recupera_servicios_personalizados(self):
        refugio = RefugioExistente.objects.create(
            nombre='Refugio existente',
            direccion='Av. Sucre, Caracas',
            ubicacion=Point(-66.9, 10.5),
            capacidad_total=100,
            capacidad_disponible=80,
            servicios=['agua', 'colchonetas', 'alimentos secos'],
        )
        form = RefugioExistenteForm(instance=refugio)
        self.assertEqual(form.initial['servicios'], ['agua'])
        self.assertEqual(form.initial['otros_servicios'], 'colchonetas, alimentos secos')

    def test_elimina_duplicados_personalizados(self):
        form = RefugioExistenteForm(data=self.datos(otros_servicios='Agua, agua, colchonetas, Colchonetas'))
        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.cleaned_data['servicios'], ['agua', 'medicina', 'colchonetas'])
