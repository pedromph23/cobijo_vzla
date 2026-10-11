"""Utilidades de detección de duplicados por similitud.

Usa SequenceMatcher para comparar nombres y geopy para distancia geográfica.
Diseñado para ser conservador: solo advierte si hay alta similitud Y
ubicación cercana.
"""
from __future__ import annotations

from difflib import SequenceMatcher
from typing import Iterable, Optional
from unicodedata import combining, normalize

from geopy.distance import geodesic


UMBRAL_NOMBRE = 0.85
UMBRAL_DISTANCIA_M = 100.0


def _normalizar(s: str) -> str:
    """Normaliza texto: sin acentos, minúsculas, espacios colapsados."""
    s = ''.join(c for c in normalize('NFKD', s or '') if not combining(c))
    return ' '.join(s.lower().split())


def similitud_nombres(a: str, b: str) -> float:
    """Retorna un valor entre 0 y 1 con la similitud de dos nombres.

    Además de SequenceMatcher (que compara strings completos), detecta el
    caso de contención: si un nombre está contenido en el otro, se considera
    altamente similar. Esto evita falsos negativos como:
    "Hospital Central" vs "Hospital Central de Caracas" (ratio=0.74).
    """
    na = _normalizar(a)
    nb = _normalizar(b)
    if not na or not nb:
        return 0.0
    if na == nb:
        return 1.0

    # Contención: uno contiene al otro.
    # Ratio ajustado por la proporción del nombre corto respecto al largo.
    corto, largo = (na, nb) if len(na) <= len(nb) else (nb, na)
    if corto in largo:
        # 0.85 base + 0.15 * proporción.
        # "Hospital Central" en "Hospital Central de Caracas":
        #   0.85 + 0.15 * (16/29) = 0.933
        proporcion = len(corto) / len(largo)
        return 0.85 + 0.15 * proporcion

    return SequenceMatcher(None, na, nb).ratio()


def distancia_metros(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Distancia geodésica en metros entre dos puntos."""
    try:
        return geodesic((lat1, lng1), (lat2, lng2)).meters
    except Exception:
        return float('inf')


def buscar_similar(
    *,
    nombre_nuevo: str,
    lat: Optional[float],
    lng: Optional[float],
    candidatos: Iterable,
    attr_nombre: str = 'nombre',
    attr_lat: str = 'lat',
    attr_lng: str = 'lng',
    umbral_nombre: float = UMBRAL_NOMBRE,
    umbral_distancia_m: float = UMBRAL_DISTANCIA_M,
) -> Optional[dict]:
    """Busca un candidato similar por nombre Y ubicación.

    Args:
        nombre_nuevo: Nombre del registro que se intenta crear.
        lat, lng: Coordenadas del nuevo registro (pueden ser None).
        candidatos: Iterable de objetos existentes.
        attr_nombre: Nombre del atributo de nombre.
        attr_lat, attr_lng: Nombres de los atributos de coordenadas.
        umbral_nombre: Similitud mínima de nombre (0-1).
        umbral_distancia_m: Distancia máxima en metros.

    Returns:
        Dict con {objeto, nombre, similitud, distancia_m, motivo} o None.
    """
    if not nombre_nuevo:
        return None

    nombre_norm = _normalizar(nombre_nuevo)
    mejor = None
    mejor_score = 0.0

    for c in candidatos:
        nombre_c = _normalizar(getattr(c, attr_nombre, '') or '')
        if not nombre_c:
            continue

        sim = similitud_nombres(nombre_nuevo, nombre_c)

        # Match solo por nombre
        if sim < umbral_nombre:
            continue

        # Si tenemos coordenadas, verificar distancia
        dist = None
        if lat is not None and lng is not None:
            c_lat = getattr(c, attr_lat, None)
            c_lng = getattr(c, attr_lng, None)
            if c_lat is not None and c_lng is not None:
                dist = distancia_metros(lat, lng, c_lat, c_lng)
                # Si estamos lejos, no es duplicado
                if dist > umbral_distancia_m:
                    continue

        # Score: similitud ponderada por cercanía
        score = sim + (1.0 if dist is None or dist <= umbral_distancia_m else 0.0)
        if score > mejor_score:
            mejor_score = score
            mejor = {
                'objeto': c,
                'nombre': getattr(c, attr_nombre, ''),
                'similitud': round(sim, 3),
                'distancia_m': round(dist, 1) if dist is not None else None,
            }

    if mejor:
        if mejor['distancia_m'] is not None and mejor['distancia_m'] <= umbral_distancia_m:
            mejor['motivo'] = (
                f'Nombre muy similar ({mejor["similitud"]:.0%}) y ubicación '
                f'a {mejor["distancia_m"]:.0f} m.'
            )
        else:
            mejor['motivo'] = f'Nombre muy similar ({mejor["similitud"]:.0%}).'
    return mejor
