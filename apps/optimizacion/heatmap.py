"""
Módulo de mapa de calor para CobijoVzla.

Este módulo contiene la lógica para generar mapas de calor basados en
índices de necesidad calculados a partir de múltiples variables.
"""

import logging
from typing import Dict, List, Optional

from django.db.models import Q
from geopy.distance import geodesic
from django.utils import timezone
from datetime import timedelta

from apps.core.models import Parroquia, RefugioExistente, ZonaAfectada, PuntoDemanda
from apps.emergencias.models import Reporte, Evento

# Configurar logger
logger = logging.getLogger(__name__)


# ============================================================
# CONSTANTES
# ============================================================

# Pesos por defecto para el cálculo del índice
PESOS_DEFECTO = {
    'densidad': 1.0,
    'vulnerabilidad': 1.0,
    'distancia': 1.0,
    'heridos': 1.0,
    'fallecidos': 1.0,
    'damnificados': 1.0,
    'reportes': 1.0,
}

# Valores máximos para normalización
MAX_DENSIDAD = 20000  # hab/km²
MAX_DISTANCIA = 50    # km
MAX_HERIDOS = 500
MAX_FALLECIDOS = 50
MAX_DAMNIFICADOS = 5000
MAX_REPORTES = 100


# ============================================================
# FUNCIONES AUXILIARES
# ============================================================

def normalizar(valor: float, maximo: float) -> float:
    """
    Normaliza un valor entre 0 y 1.
    
    Args:
        valor: Valor a normalizar
        maximo: Valor máximo para la normalización
        
    Returns:
        float: Valor normalizado entre 0 y 1
    """
    if valor <= 0:
        return 0.0
    if maximo <= 0:
        return 1.0
    return min(valor / maximo, 1.0)


def calcular_distancia_promedio_refugios(parroquia) -> float:
    """
    Calcula la distancia promedio desde el centroide de la parroquia
    hasta los refugios operativos.
    
    Args:
        parroquia: Objeto Parroquia
        
    Returns:
        float: Distancia promedio en km
    """
    try:
        refugios = RefugioExistente.objects.filter(operativo=True)
        
        if not refugios.exists():
            return MAX_DISTANCIA  # Sin refugios = máxima necesidad
        
        centroide = parroquia.geom.centroid
        distancias = []
        
        for refugio in refugios:
            if refugio.ubicacion:
                distancia = geodesic(
                    (centroide.y, centroide.x),
                    (refugio.ubicacion.y, refugio.ubicacion.x)
                ).km
                distancias.append(distancia)
        
        if not distancias:
            return MAX_DISTANCIA
        
        return sum(distancias) / len(distancias)
        
    except Exception as e:
        logger.warning(f"Error calculando distancia promedio: {e}")
        return MAX_DISTANCIA


def obtener_datos_zonas_afectadas(parroquia) -> Dict:
    """
    Obtiene los datos de zonas afectadas dentro de una parroquia.
    
    Args:
        parroquia: Objeto Parroquia
        
    Returns:
        Dict: Diccionario con heridos, fallecidos y damnificados
    """
    try:
        zonas = ZonaAfectada.objects.filter(geom__within=parroquia.geom)
        
        return {
            'heridos': sum(z.heridos for z in zonas if z.heridos),
            'fallecidos': sum(z.fallecidos for z in zonas if z.fallecidos),
            'damnificados': sum(z.damnificados for z in zonas if z.damnificados),
        }
    except Exception as e:
        logger.warning(f"Error obteniendo zonas afectadas: {e}")
        return {'heridos': 0, 'fallecidos': 0, 'damnificados': 0}


def contar_reportes_recientes(parroquia, dias: int = 7) -> int:
    """
    Cuenta los reportes recientes en una parroquia.
    
    Args:
        parroquia: Objeto Parroquia
        dias: Número de días hacia atrás (default: 7)
        
    Returns:
        int: Número de reportes recientes
    """
    try:
        fecha_limite = timezone.now() - timedelta(days=dias)
        
        reportes = Reporte.objects.filter(
            Q(zona_afectada__geom__within=parroquia.geom) |
            Q(punto_demanda__parroquia=parroquia),
            fecha__gte=fecha_limite
        ).count()
        
        return reportes
    except Exception as e:
        logger.warning(f"Error contando reportes: {e}")
        return 0


def contar_puntos_demanda(parroquia) -> int:
    """
    Cuenta los puntos de demanda en una parroquia.
    
    Args:
        parroquia: Objeto Parroquia
        
    Returns:
        int: Número de puntos de demanda
    """
    try:
        return PuntoDemanda.objects.filter(parroquia=parroquia).count()
    except Exception as e:
        logger.warning(f"Error contando puntos de demanda: {e}")
        return 0


# ============================================================
# CÁLCULO DE ÍNDICE DE NECESIDAD
# ============================================================

def calcular_indice_necesidad(parroquia, pesos: Dict = None) -> float:
    """
    Calcula el índice de necesidad para una parroquia.
    
    El índice combina múltiples variables ponderadas:
    - Densidad poblacional
    - Vulnerabilidad
    - Distancia a refugios
    - Heridos en zonas afectadas
    - Fallecidos en zonas afectadas
    - Damnificados en zonas afectadas
    - Reportes recientes
    
    Args:
        parroquia: Objeto Parroquia
        pesos: Diccionario con pesos para cada variable
        
    Returns:
        float: Índice de necesidad entre 0 y 1
    """
    if pesos is None:
        pesos = PESOS_DEFECTO.copy()
    
    try:
        indice = 0.0
        total_peso = 0.0
        
        # 1. Densidad poblacional
        peso = pesos.get('densidad', 0)
        if peso > 0:
            valor = normalizar(parroquia.densidad_poblacional, MAX_DENSIDAD)
            indice += peso * valor
            total_peso += peso
        
        # 2. Vulnerabilidad
        peso = pesos.get('vulnerabilidad', 0)
        if peso > 0:
            valor = normalizar(parroquia.indice_vulnerabilidad, 1.0)
            indice += peso * valor
            total_peso += peso
        
        # 3. Distancia a refugios
        peso = pesos.get('distancia', 0)
        if peso > 0:
            distancia_prom = calcular_distancia_promedio_refugios(parroquia)
            valor = normalizar(distancia_prom, MAX_DISTANCIA)
            indice += peso * valor
            total_peso += peso
        
        # 4. Datos de zonas afectadas
        datos_zonas = obtener_datos_zonas_afectadas(parroquia)
        
        peso = pesos.get('heridos', 0)
        if peso > 0:
            valor = normalizar(datos_zonas['heridos'], MAX_HERIDOS)
            indice += peso * valor
            total_peso += peso
        
        peso = pesos.get('fallecidos', 0)
        if peso > 0:
            valor = normalizar(datos_zonas['fallecidos'], MAX_FALLECIDOS)
            indice += peso * valor
            total_peso += peso
        
        peso = pesos.get('damnificados', 0)
        if peso > 0:
            valor = normalizar(datos_zonas['damnificados'], MAX_DAMNIFICADOS)
            indice += peso * valor
            total_peso += peso
        
        # 5. Reportes recientes
        peso = pesos.get('reportes', 0)
        if peso > 0:
            num_reportes = contar_reportes_recientes(parroquia)
            valor = normalizar(num_reportes, MAX_REPORTES)
            indice += peso * valor
            total_peso += peso
        
        # Normalizar por el total de pesos
        if total_peso > 0:
            indice = indice / total_peso
        
        return round(min(indice, 1.0), 4)
        
    except Exception as e:
        logger.error(f"Error calculando índice de necesidad: {e}")
        return 0.0


# ============================================================
# GENERACIÓN DE MAPA DE CALOR
# ============================================================

def generar_mapa_calor(pesos: Dict = None, parroquias_ids: List = None) -> List[Dict]:
    """
    Genera los puntos para el mapa de calor.
    
    Args:
        pesos: Diccionario con pesos para cada variable
        parroquias_ids: Lista opcional de IDs de parroquias a incluir
        
    Returns:
        List[Dict]: Lista de puntos con lat, lng e intensidad
    """
    logger.info("Generando mapa de calor...")
    
    try:
        # Obtener parroquias
        if parroquias_ids:
            parroquias = Parroquia.objects.filter(id__in=parroquias_ids)
        else:
            parroquias = Parroquia.objects.all()
        
        puntos_calor = []
        
        for parroquia in parroquias:
            try:
                # Calcular índice de necesidad
                indice = calcular_indice_necesidad(parroquia, pesos)
                
                # Obtener centroide
                if parroquia.geom:
                    centroide = parroquia.geom.centroid
                    puntos_calor.append({
                        'lat': centroide.y,
                        'lng': centroide.x,
                        'intensidad': indice,
                        'parroquia': parroquia.nombre,
                        'estado': parroquia.estado.nombre if parroquia.estado else '',
                    })
            except Exception as e:
                logger.warning(f"Error procesando parroquia {parroquia.id}: {e}")
                continue
        
        logger.info(f"Mapa de calor generado: {len(puntos_calor)} puntos")
        return puntos_calor
        
    except Exception as e:
        logger.error(f"Error generando mapa de calor: {e}")
        return []


# ============================================================
# FUNCIONES ADICIONALES
# ============================================================

def generar_mapa_calor_por_estado(estado_id: int, pesos: Dict = None) -> List[Dict]:
    """
    Genera mapa de calor para un estado específico.
    
    Args:
        estado_id: ID del estado
        pesos: Diccionario con pesos
        
    Returns:
        List[Dict]: Puntos de calor del estado
    """
    try:
        parroquias = Parroquia.objects.filter(estado_id=estado_id)
        parroquias_ids = list(parroquias.values_list('id', flat=True))
        
        return generar_mapa_calor(pesos, parroquias_ids)
        
    except Exception as e:
        logger.error(f"Error generando mapa de calor por estado: {e}")
        return []


def obtener_estadisticas_calor() -> Dict:
    """
    Obtiene estadísticas del mapa de calor.
    
    Returns:
        Dict: Estadísticas generales
    """
    try:
        parroquias = Parroquia.objects.all()
        
        indices = []
        for parroquia in parroquias:
            indice = calcular_indice_necesidad(parroquia)
            indices.append(indice)
        
        if not indices:
            return {
                'total': 0,
                'promedio': 0,
                'maximo': 0,
                'minimo': 0,
                'alto': 0,
                'medio': 0,
                'bajo': 0,
            }
        
        return {
            'total': len(indices),
            'promedio': round(sum(indices) / len(indices), 4),
            'maximo': max(indices),
            'minimo': min(indices),
            'alto': sum(1 for i in indices if i > 0.7),
            'medio': sum(1 for i in indices if 0.3 <= i <= 0.7),
            'bajo': sum(1 for i in indices if i < 0.3),
        }
        
    except Exception as e:
        logger.error(f"Error obteniendo estadísticas: {e}")
        return {}


def get_pesos_desde_request(query_params) -> Dict:
    """
    Obtiene pesos desde parámetros de request.
    
    Args:
        query_params: QueryDict de Django
        
    Returns:
        Dict: Pesos normalizados
    """
    pesos = PESOS_DEFECTO.copy()
    
    for clave in pesos.keys():
        if clave in query_params:
            try:
                valor = float(query_params[clave])
                if valor >= 0:
                    pesos[clave] = valor
            except (ValueError, TypeError):
                logger.warning(f"Valor inválido para peso {clave}: {query_params[clave]}")
    
    return pesos