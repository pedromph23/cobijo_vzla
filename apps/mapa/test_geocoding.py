from types import SimpleNamespace
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import TestCase
from rest_framework.test import APIClient


class GeocodificacionApiTest(TestCase):
    def setUp(self):
        cache.clear()
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            username="geo-test",
            password="test-pass-123",
        )
        self.client.force_authenticate(user=self.user)

    def test_rechaza_direccion_vacia(self):
        response = self.client.get("/api/geocodificar/")
        self.assertEqual(response.status_code, 400)
        self.assertFalse(response.json()["ok"])

    @patch("apps.mapa.geocoding._GEOCODER.geocode")
    def test_geocodifica_y_devuelve_coordenadas(self, geocode):
        geocode.return_value = SimpleNamespace(
            latitude=10.4806,
            longitude=-66.9036,
            address="Caracas, Venezuela",
        )

        response = self.client.get(
            "/api/geocodificar/",
            {"direccion": "Av. Sucre, Caracas"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["lat"], 10.4806)
        self.assertEqual(response.json()["lng"], -66.9036)
        geocode.assert_called_once()

    @patch("apps.mapa.geocoding._GEOCODER.geocode")
    def test_reutiliza_cache(self, geocode):
        geocode.return_value = SimpleNamespace(
            latitude=10.4806,
            longitude=-66.9036,
            address="Caracas, Venezuela",
        )

        first = self.client.get(
            "/api/geocodificar/",
            {"direccion": "Av. Sucre, Caracas"},
        )
        second = self.client.get(
            "/api/geocodificar/",
            {"direccion": "  Av. Sucre,   Caracas  "},
        )

        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 200)
        geocode.assert_called_once()
