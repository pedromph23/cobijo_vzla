"""
Módulo de optimización para CobijoVzla.

Este módulo contiene la lógica para ejecutar modelos de optimización
de localización de centros de acopio y refugios temporales.
"""

import logging
from typing import Dict, List, Tuple, Optional, Any

import pulp
from django.db.models import Q
from geopy.distance import geodesic

from apps.core.models import (
    PuntoDemanda,
    SitioCandidato,
    ZonaAfectada,
    ParametrosModelo,
)

# Configurar logger
logger = logging.getLogger(__name__)


# ============================================================
# FUNCIONES AUXILIARES
# ============================================================

def calcular_distancia_km(punto1, punto2) -> float:
    """
    Calcula la distancia en kilómetros entre dos puntos geográficos.
    
    Args:
        punto1: Punto geográfico (Point de GeoDjango)
        punto2: Punto geográfico (Point de GeoDjango)
        
    Returns:
        float: Distancia en kilómetros
    """
    try:
        if punto1 is None or punto2 is None:
            return float('inf')
        
        return geodesic(
            (punto1.y, punto1.x),
            (punto2.y, punto2.x)
        ).km
    except Exception as e:
        logger.error(f"Error calculando distancia: {e}")
        return float('inf')


def calcular_matriz_distancias(demandas, candidatos) -> Dict:
    """
    Calcula la matriz de distancias entre demandas y candidatos.
    
    Args:
        demandas: Lista de PuntoDemanda
        candidatos: Lista de SitioCandidato
        
    Returns:
        Dict: Matriz de distancias {(demanda_id, candidato_id): distancia_km}
    """
    matriz = {}
    
    for i in demandas:
        for j in candidatos:
            distancia = calcular_distancia_km(i.ubicacion, j.ubicacion)
            matriz[(i.id, j.id)] = distancia
    
    logger.info(f"Matriz de distancias calculada: {len(demandas)}x{len(candidatos)}")
    return matriz


def calcular_ponderacion_demanda(demanda, parametros) -> float:
    """
    Calcula la ponderación de una demanda según vulnerabilidad y afectación.
    
    Args:
        demanda: PuntoDemanda
        parametros: ParametrosModelo
        
    Returns:
        float: Ponderación de la demanda
    """
    peso = 1.0
    
    # Ponderación por vulnerabilidad
    if demanda.vulnerabilidad:
        peso += parametros.ponderador_vulnerabilidad * demanda.vulnerabilidad
    
    # Ponderación por zonas afectadas
    try:
        zonas = ZonaAfectada.objects.filter(geom__contains=demanda.ubicacion)
        
        for zona in zonas:
            if zona.heridos > 0:
                peso += parametros.ponderador_heridos * zona.heridos / 100
            if zona.fallecidos > 0:
                peso += parametros.ponderador_fallecidos * zona.fallecidos / 10
            if zona.damnificados > 0:
                peso += parametros.ponderador_damnificados * zona.damnificados / 1000
    except Exception as e:
        logger.warning(f"Error calculando ponderación: {e}")
    
    return peso


def obtener_datos_optimizacion(parametros_id: int) -> Tuple:
    """
    Obtiene los datos necesarios para la optimización.
    
    Args:
        parametros_id: ID de los parámetros del modelo
        
    Returns:
        Tuple: (demandas, candidatos, parametros)
    """
    try:
        parametros = ParametrosModelo.objects.get(pk=parametros_id)
    except ParametrosModelo.DoesNotExist:
        logger.error(f"Parámetros no encontrados: {parametros_id}")
        return None, None, None
    
    # Filtrar demandas
    demandas = PuntoDemanda.objects.all()
    candidatos = SitioCandidato.objects.filter(disponible=True)
    
    # Filtrar por estado si se especifica
    if parametros.filtro_estado:
        demandas = demandas.filter(parroquia__estado=parametros.filtro_estado)
        candidatos = candidatos.filter(
            ubicacion__within=parametros.filtro_estado.geom
        )
    
    demandas_list = list(demandas)
    candidatos_list = list(candidatos)
    
    logger.info(f"Demandas: {len(demandas_list)}, Candidatos: {len(candidatos_list)}")
    
    return demandas_list, candidatos_list, parametros


# ============================================================
# MODELOS DE OPTIMIZACIÓN
# ============================================================

def optimizar_p_mediana(demandas, candidatos, parametros, matriz_dist, ponderaciones):
    """
    Modelo P-Mediana: minimizar distancia ponderada.
    
    Args:
        demandas: Lista de PuntoDemanda
        candidatos: Lista de SitioCandidato
        parametros: ParametrosModelo
        matriz_dist: Matriz de distancias
        ponderaciones: Diccionario de ponderaciones
        
    Returns:
        Dict: Resultado de la optimización
    """
    prob = pulp.LpProblem("P-Mediana", pulp.LpMinimize)
    
    # Variables de decisión
    x = pulp.LpVariable.dicts(
        "asignacion",
        [(i.id, j.id) for i in demandas for j in candidatos],
        cat='Binary'
    )
    y = pulp.LpVariable.dicts(
        "apertura",
        [j.id for j in candidatos],
        cat='Binary'
    )
    
    # Función objetivo: minimizar distancia ponderada
    prob += pulp.lpSum(
        ponderaciones[i.id] * matriz_dist[(i.id, j.id)] * x[(i.id, j.id)]
        for i in demandas for j in candidatos
    )
    
    # Restricción: cada demanda asignada a exactamente un centro
    for i in demandas:
        prob += pulp.lpSum(x[(i.id, j.id)] for j in candidatos) == 1
    
    # Restricción: no asignar a centros no abiertos
    for i in demandas:
        for j in candidatos:
            prob += x[(i.id, j.id)] <= y[j.id]
    
    # Restricción: número de centros a abrir
    p = min(parametros.p, len(candidatos))
    prob += pulp.lpSum(y[j.id] for j in candidatos) == p
    
    # Resolver
    prob.solve(pulp.PULP_CBC_CMD(msg=0))
    
    if pulp.LpStatus[prob.status] != 'Optimal':
        return {'error': f'No se encontró solución óptima. Estado: {pulp.LpStatus[prob.status]}'}
    
    # Extraer resultados
    return extraer_resultados(demandas, candidatos, x, y, matriz_dist, parametros)


def optimizar_p_centro(demandas, candidatos, parametros, matriz_dist):
    """
    Modelo P-Centro: minimizar la distancia máxima.
    
    Args:
        demandas: Lista de PuntoDemanda
        candidatos: Lista de SitioCandidato
        parametros: ParametrosModelo
        matriz_dist: Matriz de distancias
        
    Returns:
        Dict: Resultado de la optimización
    """
    prob = pulp.LpProblem("P-Centro", pulp.LpMinimize)
    
    # Variables
    x = pulp.LpVariable.dicts(
        "asignacion",
        [(i.id, j.id) for i in demandas for j in candidatos],
        cat='Binary'
    )
    y = pulp.LpVariable.dicts(
        "apertura",
        [j.id for j in candidatos],
        cat='Binary'
    )
    w = pulp.LpVariable("max_distancia", lowBound=0)
    
    # Función objetivo: minimizar distancia máxima
    prob += w
    
    # Restricciones de asignación
    for i in demandas:
        prob += pulp.lpSum(x[(i.id, j.id)] for j in candidatos) == 1
    
    for i in demandas:
        for j in candidatos:
            prob += x[(i.id, j.id)] <= y[j.id]
    
    p = min(parametros.p, len(candidatos))
    prob += pulp.lpSum(y[j.id] for j in candidatos) == p
    
    # Restricción de distancia máxima
    for i in demandas:
        for j in candidatos:
            prob += w >= matriz_dist[(i.id, j.id)] * x[(i.id, j.id)]
    
    prob.solve(pulp.PULP_CBC_CMD(msg=0))
    
    if pulp.LpStatus[prob.status] != 'Optimal':
        return {'error': f'No se encontró solución óptima. Estado: {pulp.LpStatus[prob.status]}'}
    
    return extraer_resultados(demandas, candidatos, x, y, matriz_dist, parametros)


def optimizar_cobertura_maxima(demandas, candidatos, parametros, matriz_dist):
    """
    Modelo de Cobertura Máxima: maximizar demanda cubierta.
    
    Args:
        demandas: Lista de PuntoDemanda
        candidatos: Lista de SitioCandidato
        parametros: ParametrosModelo
        matriz_dist: Matriz de distancias
        
    Returns:
        Dict: Resultado de la optimización
    """
    prob = pulp.LpProblem("Cobertura_Maxima", pulp.LpMaximize)
    
    radio_km = parametros.radio_cobertura / 1000  # Convertir a km
    
    # Variables
    x = pulp.LpVariable.dicts(
        "demanda_cubierta",
        [i.id for i in demandas],
        cat='Binary'
    )
    y = pulp.LpVariable.dicts(
        "apertura",
        [j.id for j in candidatos],
        cat='Binary'
    )
    
    # Función objetivo: maximizar población cubierta
    prob += pulp.lpSum(
        demanda.poblacion * x[demanda.id]
        for demanda in demandas
    )
    
    # Restricción: número de centros
    p = min(parametros.p, len(candidatos))
    prob += pulp.lpSum(y[j.id] for j in candidatos) == p
    
    # Restricción: demanda cubierta solo si hay centro cercano
    for i in demandas:
        centros_cercanos = [
            j.id for j in candidatos
            if matriz_dist[(i.id, j.id)] <= radio_km
        ]
        if centros_cercanos:
            prob += x[i.id] <= pulp.lpSum(y[j_id] for j_id in centros_cercanos)
        else:
            prob += x[i.id] == 0
    
    prob.solve(pulp.PULP_CBC_CMD(msg=0))
    
    if pulp.LpStatus[prob.status] != 'Optimal':
        return {'error': f'No se encontró solución óptima. Estado: {pulp.LpStatus[prob.status]}'}
    
    # Extraer resultados
    centros_seleccionados = [j for j in candidatos if y[j.id].value() > 0.5]
    asignaciones = {}
    
    for i in demandas:
        for j in candidatos:
            if matriz_dist[(i.id, j.id)] <= radio_km and y[j.id].value() > 0.5:
                asignaciones[i.id] = j.id
                break
    
    return construir_resultado(centros_seleccionados, asignaciones, matriz_dist, parametros, demandas)


def optimizar_capacidades(demandas, candidatos, parametros, matriz_dist, ponderaciones):
    """
    Modelo con Capacidades: minimizar distancia con restricción de capacidad.
    
    Args:
        demandas: Lista de PuntoDemanda
        candidatos: Lista de SitioCandidato
        parametros: ParametrosModelo
        matriz_dist: Matriz de distancias
        ponderaciones: Diccionario de ponderaciones
        
    Returns:
        Dict: Resultado de la optimización
    """
    prob = pulp.LpProblem("Capacidades", pulp.LpMinimize)
    
    x = pulp.LpVariable.dicts(
        "asignacion",
        [(i.id, j.id) for i in demandas for j in candidatos],
        cat='Binary'
    )
    y = pulp.LpVariable.dicts(
        "apertura",
        [j.id for j in candidatos],
        cat='Binary'
    )
    
    # Función objetivo
    prob += pulp.lpSum(
        ponderaciones[i.id] * matriz_dist[(i.id, j.id)] * x[(i.id, j.id)]
        for i in demandas for j in candidatos
    )
    
    # Restricciones de asignación
    for i in demandas:
        prob += pulp.lpSum(x[(i.id, j.id)] for j in candidatos) == 1
    
    for i in demandas:
        for j in candidatos:
            prob += x[(i.id, j.id)] <= y[j.id]
    
    p = min(parametros.p, len(candidatos))
    prob += pulp.lpSum(y[j.id] for j in candidatos) == p
    
    # Restricciones de capacidad
    for j in candidatos:
        prob += pulp.lpSum(
            demanda.poblacion * x[(demanda.id, j.id)]
            for demanda in demandas
        ) <= j.capacidad_maxima
    
    prob.solve(pulp.PULP_CBC_CMD(msg=0))
    
    if pulp.LpStatus[prob.status] != 'Optimal':
        return {'error': f'No se encontró solución óptima. Estado: {pulp.LpStatus[prob.status]}'}
    
    return extraer_resultados(demandas, candidatos, x, y, matriz_dist, parametros)


# ============================================================
# FUNCIONES DE EXTRACCIÓN Y CONSTRUCCIÓN
# ============================================================

def extraer_resultados(demandas, candidatos, x, y, matriz_dist, parametros):
    """
    Extrae resultados de variables de decisión de PuLP.
    """
    centros_seleccionados = [j for j in candidatos if y[j.id].value() > 0.5]
    asignaciones = {}
    
    for i in demandas:
        for j in candidatos:
            if x[(i.id, j.id)].value() > 0.5:
                asignaciones[i.id] = j.id
                break
    
    return construir_resultado(centros_seleccionados, asignaciones, matriz_dist, parametros, demandas)


def construir_resultado(centros_seleccionados, asignaciones, matriz_dist, parametros, demandas):
    """
    Construye el diccionario de resultado con métricas.
    """
    # Métricas
    distancia_total = sum(
        matriz_dist[(demanda_id, centro_id)]
        for demanda_id, centro_id in asignaciones.items()
        if (demanda_id, centro_id) in matriz_dist
    )
    
    poblacion_atendida = sum(
        demanda.poblacion
        for demanda in demandas
        if demanda.id in asignaciones
    )
    
    radio_km = parametros.radio_cobertura / 1000
    cubiertos_radio = sum(
        1 for demanda_id, centro_id in asignaciones.items()
        if (demanda_id, centro_id) in matriz_dist
        and matriz_dist[(demanda_id, centro_id)] <= radio_km
    )
    
    porcentaje_cubierto = (cubiertos_radio / len(demandas) * 100) if demandas else 0
    
    resultado = {
        'centros': [
            {
                'id': j.id,
                'nombre': j.nombre,
                'lng': j.ubicacion.x if j.ubicacion else None,
                'lat': j.ubicacion.y if j.ubicacion else None,
                'capacidad_maxima': j.capacidad_maxima,
                'costo_apertura': float(j.costo_apertura) if j.costo_apertura else 0,
            }
            for j in centros_seleccionados
        ],
        'asignaciones': {str(k): v for k, v in asignaciones.items()},
        'distancia_total_km': round(distancia_total, 2),
        'poblacion_atendida': poblacion_atendida,
        'porcentaje_cubierto': round(porcentaje_cubierto, 2),
        'costo_total': sum(
            float(j.costo_apertura) if j.costo_apertura else 0
            for j in centros_seleccionados
        ),
        'total_demandas': len(demandas),
        'total_centros': len(centros_seleccionados),
    }
    
    logger.info(f"Optimización completada: {len(centros_seleccionados)} centros, "
                f"{len(asignaciones)} asignaciones, {porcentaje_cubierto:.2f}% cubierto")
    
    return resultado


# ============================================================
# FUNCIÓN PRINCIPAL
# ============================================================

def ejecutar_optimizacion(parametros_id: int) -> Dict[str, Any]:
    """
    Ejecuta el modelo de optimización según los parámetros especificados.
    
    Args:
        parametros_id: ID de los parámetros del modelo
        
    Returns:
        Dict: Resultado de la optimización o error
    """
    logger.info(f"Iniciando optimización con parámetros ID: {parametros_id}")
    
    try:
        # Obtener datos
        demandas, candidatos, parametros = obtener_datos_optimizacion(parametros_id)
        
        if parametros is None:
            return {'error': 'Parámetros no encontrados'}
        
        if not demandas:
            return {'error': 'No hay puntos de demanda disponibles'}
        
        if not candidatos:
            return {'error': 'No hay sitios candidatos disponibles'}
        
        # Calcular matriz de distancias
        matriz_dist = calcular_matriz_distancias(demandas, candidatos)
        
        # Calcular ponderaciones
        ponderaciones = {
            demanda.id: calcular_ponderacion_demanda(demanda, parametros)
            for demanda in demandas
        }
        
        # Seleccionar modelo según tipo
        tipo_modelo = parametros.tipo_modelo
        
        if tipo_modelo == 'pmediana':
            resultado = optimizar_p_mediana(
                demandas, candidatos, parametros, matriz_dist, ponderaciones
            )
        elif tipo_modelo == 'pcentro':
            resultado = optimizar_p_centro(
                demandas, candidatos, parametros, matriz_dist
            )
        elif tipo_modelo == 'cobertura':
            resultado = optimizar_cobertura_maxima(
                demandas, candidatos, parametros, matriz_dist
            )
        elif tipo_modelo == 'capacidades':
            resultado = optimizar_capacidades(
                demandas, candidatos, parametros, matriz_dist, ponderaciones
            )
        else:
            return {'error': f'Tipo de modelo no válido: {tipo_modelo}'}
        
        return resultado
        
    except Exception as e:
        logger.error(f"Error en optimización: {e}", exc_info=True)
        return {'error': f'Error al ejecutar optimización: {str(e)}'}