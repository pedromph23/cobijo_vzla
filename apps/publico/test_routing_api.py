import json
from unittest.mock import patch

from django.test import SimpleTestCase


class RutaPublicaApiTests(SimpleTestCase):
    def _payload(self):
        return {
            "code": "Ok",
            "routes": [{
                "distance": 8500,
                "duration": 1200,
                "geometry": {"coordinates": [[-66.90, 10.50], [-66.89, 10.51], [-66.88, 10.52]]},
                "legs": [{"steps": [
                    {"distance": 150, "duration": 20, "name": "Avenida Sucre", "maneuver": {"type": "depart", "location": [-66.90, 10.50]}},
                    {"distance": 300, "duration": 40, "name": "Avenida Baralt", "maneuver": {"type": "turn", "modifier": "right", "location": [-66.89, 10.51]}},
                    {"distance": 0, "duration": 0, "name": "", "maneuver": {"type": "arrive", "location": [-66.88, 10.52]}},
                ]}],
            }],
        }

    @patch("apps.publico.routing_api.urlopen")
    def test_calcula_ruta_y_devuelve_instrucciones_en_espanol(self, mock_urlopen):
        payload = self._payload()

        class Response:
            def __enter__(self):
                return self

            def __exit__(self, *args):
                return False

            def read(self):
                return json.dumps(payload).encode("utf-8")

        mock_urlopen.return_value = Response()
        response = self.client.get("/api/publico/ruta/?origen_lat=10.50&origen_lng=-66.90&destino_lat=10.52&destino_lng=-66.88")

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["ok"])
        self.assertEqual(data["ruta"]["summary"]["totalDistance"], 8500.0)
        self.assertEqual(data["ruta"]["instructions"][0]["text"], "Continúe por Avenida Sucre")
        self.assertEqual(data["ruta"]["instructions"][1]["text"], "Gire a la derecha hacia Avenida Baralt")
        self.assertEqual(data["ruta"]["instructions"][2]["text"], "Ha llegado a su destino")

    def test_rechaza_origen_fuera_de_venezuela(self):
        response = self.client.get("/api/publico/ruta/?origen_lat=40.70&origen_lng=-74.00&destino_lat=10.52&destino_lng=-66.88")
        self.assertEqual(response.status_code, 400)
        self.assertFalse(response.json().get("ok", True))

    def test_rechaza_destino_fuera_de_venezuela(self):
        response = self.client.get("/api/publico/ruta/?origen_lat=10.50&origen_lng=-66.90&destino_lat=40.70&destino_lng=-74.00")
        self.assertEqual(response.status_code, 400)
        self.assertFalse(response.json().get("ok", True))
