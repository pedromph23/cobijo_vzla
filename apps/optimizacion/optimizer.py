"""
Módulo de optimización para CobijoVzla.

Resuelve modelos de localización usando programación lineal entera (PuLP).
Incluye timeout, validación previa y mensajes de error en español.

Modelos soportados:
    - pmediana:   minimiza distancia total ponderada
    - pcentro:    minimiza la distancia máxima
    - cobertura:  maximiza población cubierta dentro de un radio
    - capacidades: pmediana con restricción de capacidad
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass, asdict, field
from typing import Dict, List, Optional, Tuple, Any

import pulp
from geopy.distance import geodesic

from apps.core.models import PuntoDemanda, SitioCandidato, ZonaAfectada, ParametrosModelo


logger = logging.getLogger(__name__)


# ============================================================
# CONFIGURACIÓN
# ============================================================

SOLVER_TIMEOUT_SEGUNDOS = 30
MAX_CANDIDATOS_ADVERTENCIA = 500
TIPOS_MODELO_VALIDOS = ('pmediana', 'pcentro', 'cobertura', 'capacidades')


# ============================================================
# EXCEPCIONES
# ============================================================

class OptimizacionError(Exception):
    """Error controlado en el proceso de optimización."""
    pass


# ============================================================
# DATACLASSES
# ============================================================

@dataclass
class ResultadoOptimizacion:
    """Resultado de un modelo de optimización."""
    centros: List[Dict] = field(default_factory=list)
    asignaciones: Dict[str, int] = field(default_factory=dict)
    distancia_total_km: float = 0.0
    distancia_promedio_km: float = 0.0
    distancia_maxima_km: float = 0.0
    poblacion_atendida: int = 0
    porcentaje_cubierto: float = 0.0
    costo_total: float = 0.0
    total_demandas: int = 0
    total_centros: int = 0
    tiempo_ejecucion_seg: float = 0.0
    mensaje: str = ""

    def to_dict(self) -> Dict:
        return asdict(self)


# ============================================================
# UTILIDADES
# ============================================================

def _distancia_km(p1, p2) -> float:
    """Distancia geodésica en km entre dos Points."""
    if p1 is None or p2 is None:
        return float('inf')
    try:
        return geodesic((p1.y, p1.x), (p2.y, p2.x)).km
    except Exception:
        return float('inf')


def _matriz_distancias(demandas, candidatos) -> Dict[Tuple[int, int], float]:
    """Matriz {(demanda_id, candidato_id): km}."""
    matriz = {}
    for d in demandas:
        for c in candidatos:
            matriz[(d.id, c.id)] = _distancia_km(d.ubicacion, c.ubicacion)
    logger.info(f"Matriz {len(demandas)}x{len(candidatos)} calculada")
    return matriz


def _ponderacion_demanda(demanda, parametros) -> float:
    """Ponderación por vulnerabilidad y afectación."""
    peso = 1.0
    try:
        if demanda.vulnerabilidad:
            peso += parametros.ponderador_vulnerabilidad * demanda.vulnerabilidad

        zonas = ZonaAfectada.objects.filter(geom__contains=demanda.ubicacion)
        for z in zonas:
            if z.heridos:
                peso += parametros.ponderador_heridos * z.heridos / 100
            if z.fallecidos:
                peso += parametros.ponderador_fallecidos * z.fallecidos / 10
            if z.damnificados:
                peso += parametros.ponderador_damnificados * z.damnificados / 1000
    except Exception as e:
        logger.warning(f"Ponderación demanda {demanda.id}: {e}")
    return peso


def _validar_entrada(demandas, candidatos, parametros):
    """Valida entradas antes de ejecutar el solver."""
    if not demandas:
        raise OptimizacionError(
            "No hay puntos de demanda disponibles. "
            "Cargue datos primero desde el panel de gestión."
        )
    if not candidatos:
        raise OptimizacionError(
            "No hay sitios candidatos disponibles. "
            "Registre sitios candidatos desde el panel de administración."
        )
    if parametros.tipo_modelo not in TIPOS_MODELO_VALIDOS:
        raise OptimizacionError(
            f"Tipo de modelo '{parametros.tipo_modelo}' no soportado. "
            f"Use uno de: {', '.join(TIPOS_MODELO_VALIDOS)}."
        )
    if len(candidatos) > MAX_CANDIDATOS_ADVERTENCIA:
        logger.warning(
            f"Optimización con {len(candidatos)} candidatos puede ser lenta. "
            f"Considere filtrar por estado."
        )


# ============================================================
# SOLVER CON TIMEOUT
# ============================================================

def _resolver(prob: pulp.LpProblem, timeout: int = SOLVER_TIMEOUT_SEGUNDOS) -> str:
    """Resuelve el problema con timeout. Retorna el status."""
    try:
        solver = pulp.PULP_CBC_CMD(msg=0, timeLimit=timeout)
        prob.solve(solver)
        return pulp.LpStatus[prob.status]
    except Exception as e:
        logger.error(f"Error en solver: {e}")
        return 'Not Solved'


def _verificar_optimo(status: str):
    """Verifica el status y lanza excepción clara si falló."""
    if status == 'Optimal':
        return
    if status == 'Infeasible':
        raise OptimizacionError(
            "No existe solución factible con las restricciones actuales. "
            "Pruebe: aumentar el número de centros (p), reducir el radio de "
            "cobertura, o ampliar los sitios candidatos."
        )
    if status == 'Unbounded':
        raise OptimizacionError("El modelo no tiene solución acotada. Revise los parámetros.")
    if status == 'Not Solved' or 'Time' in status:
        raise OptimizacionError(
            f"El solver no terminó en {SOLVER_TIMEOUT_SEGUNDOS}s. "
            f"Reduzca el tamaño del problema (menos demandas o candidatos)."
        )
    raise OptimizacionError(f"El solver devolvió status inesperado: {status}")


# ============================================================
# MODELOS
# ============================================================

def _pmediana(demandas, candidatos, parametros, matriz, ponderaciones):
    prob = pulp.LpProblem("P-Mediana", pulp.LpMinimize)
    x = pulp.LpVariable.dicts("x", [(i.id, j.id) for i in demandas for j in candidatos], cat='Binary')
    y = pulp.LpVariable.dicts("y", [j.id for j in candidatos], cat='Binary')

    prob += pulp.lpSum(
        ponderaciones[i.id] * matriz[(i.id, j.id)] * x[(i.id, j.id)]
        for i in demandas for j in candidatos
    )
    for i in demandas:
        prob += pulp.lpSum(x[(i.id, j.id)] for j in candidatos) == 1
        for j in candidatos:
            prob += x[(i.id, j.id)] <= y[j.id]

    p = min(parametros.p, len(candidatos))
    prob += pulp.lpSum(y[j.id] for j in candidatos) == p

    _verificar_optimo(_resolver(prob))
    return _extraer(demandas, candidatos, x, y, matriz, parametros)


def _pcentro(demandas, candidatos, parametros, matriz):
    prob = pulp.LpProblem("P-Centro", pulp.LpMinimize)
    x = pulp.LpVariable.dicts("x", [(i.id, j.id) for i in demandas for j in candidatos], cat='Binary')
    y = pulp.LpVariable.dicts("y", [j.id for j in candidatos], cat='Binary')
    w = pulp.LpVariable("w", lowBound=0)

    prob += w
    for i in demandas:
        prob += pulp.lpSum(x[(i.id, j.id)] for j in candidatos) == 1
        for j in candidatos:
            prob += x[(i.id, j.id)] <= y[j.id]
            prob += w >= matriz[(i.id, j.id)] * x[(i.id, j.id)]

    p = min(parametros.p, len(candidatos))
    prob += pulp.lpSum(y[j.id] for j in candidatos) == p

    _verificar_optimo(_resolver(prob))
    return _extraer(demandas, candidatos, x, y, matriz, parametros)


def _cobertura(demandas, candidatos, parametros, matriz):
    prob = pulp.LpProblem("Cobertura-Maxima", pulp.LpMaximize)
    radio_km = parametros.radio_cobertura / 1000

    x = pulp.LpVariable.dicts("x", [i.id for i in demandas], cat='Binary')
    y = pulp.LpVariable.dicts("y", [j.id for j in candidatos], cat='Binary')

    prob += pulp.lpSum(d.poblacion * x[d.id] for d in demandas)

    p = min(parametros.p, len(candidatos))
    prob += pulp.lpSum(y[j.id] for j in candidatos) == p

    for i in demandas:
        cercanos = [j.id for j in candidatos if matriz[(i.id, j.id)] <= radio_km]
        if cercanos:
            prob += x[i.id] <= pulp.lpSum(y[j_id] for j_id in cercanos)
        else:
            prob += x[i.id] == 0

    _verificar_optimo(_resolver(prob))

    centros = [j for j in candidatos if y[j.id].value() > 0.5]
    asignaciones = {}
    for i in demandas:
        for j in candidatos:
            if matriz[(i.id, j.id)] <= radio_km and y[j.id].value() > 0.5:
                asignaciones[i.id] = j.id
                break

    return _construir(centros, asignaciones, matriz, parametros, demandas)


def _capacidades(demandas, candidatos, parametros, matriz, ponderaciones):
    prob = pulp.LpProblem("Capacidades", pulp.LpMinimize)
    x = pulp.LpVariable.dicts("x", [(i.id, j.id) for i in demandas for j in candidatos], cat='Binary')
    y = pulp.LpVariable.dicts("y", [j.id for j in candidatos], cat='Binary')

    prob += pulp.lpSum(
        ponderaciones[i.id] * matriz[(i.id, j.id)] * x[(i.id, j.id)]
        for i in demandas for j in candidatos
    )
    for i in demandas:
        prob += pulp.lpSum(x[(i.id, j.id)] for j in candidatos) == 1
        for j in candidatos:
            prob += x[(i.id, j.id)] <= y[j.id]

    p = min(parametros.p, len(candidatos))
    prob += pulp.lpSum(y[j.id] for j in candidatos) == p

    for j in candidatos:
        prob += pulp.lpSum(d.poblacion * x[(d.id, j.id)] for d in demandas) <= j.capacidad_maxima

    _verificar_optimo(_resolver(prob))
    return _extraer(demandas, candidatos, x, y, matriz, parametros)


# ============================================================
# CONSTRUCCIÓN DE RESULTADOS
# ============================================================

def _extraer(demandas, candidatos, x, y, matriz, parametros):
    centros = [j for j in candidatos if y[j.id].value() > 0.5]
    asignaciones = {}
    for i in demandas:
        for j in candidatos:
            if x[(i.id, j.id)].value() > 0.5:
                asignaciones[i.id] = j.id
                break
    return _construir(centros, asignaciones, matriz, parametros, demandas)


def _construir(centros_sel, asignaciones, matriz, parametros, demandas) -> Dict:
    """Construye el dict de resultado con métricas completas."""
    distancias = [
        matriz[(d_id, c_id)]
        for d_id, c_id in asignaciones.items()
        if (d_id, c_id) in matriz
    ]
    dist_total = sum(distancias)
    dist_prom = dist_total / len(distancias) if distancias else 0
    dist_max = max(distancias) if distancias else 0

    poblacion = sum(d.poblacion for d in demandas if d.id in asignaciones)

    radio_km = parametros.radio_cobertura / 1000
    cubiertos = sum(
        1 for d_id, c_id in asignaciones.items()
        if (d_id, c_id) in matriz and matriz[(d_id, c_id)] <= radio_km
    )
    porcentaje = (cubiertos / len(demandas) * 100) if demandas else 0

    demanda_por_centro = {}
    for c_id in asignaciones.values():
        demanda_por_centro[c_id] = demanda_por_centro.get(c_id, 0) + 1

    centros_data = [
        {
            'id': j.id,
            'nombre': j.nombre,
            'lng': j.ubicacion.x if j.ubicacion else None,
            'lat': j.ubicacion.y if j.ubicacion else None,
            'capacidad_maxima': j.capacidad_maxima,
            'costo_apertura': float(j.costo_apertura) if j.costo_apertura else 0.0,
            'demanda_asignada': demanda_por_centro.get(j.id, 0),
        }
        for j in centros_sel
    ]

    resultado = ResultadoOptimizacion(
        centros=centros_data,
        asignaciones={str(k): v for k, v in asignaciones.items()},
        distancia_total_km=round(dist_total, 2),
        distancia_promedio_km=round(dist_prom, 2),
        distancia_maxima_km=round(dist_max, 2),
        poblacion_atendida=poblacion,
        porcentaje_cubierto=round(porcentaje, 2),
        costo_total=sum(c['costo_apertura'] for c in centros_data),
        total_demandas=len(demandas),
        total_centros=len(centros_sel),
        mensaje=(
            f"{len(centros_sel)} centros atienden a {poblacion:,} personas "
            f"({porcentaje:.1f}% cobertura)."
        ).replace(',', '.'),
    )

    logger.info(f"Optimización OK: {len(centros_sel)} centros, {porcentaje:.2f}% cubierto")
    return resultado.to_dict()


# ============================================================
# FUNCIÓN PRINCIPAL
# ============================================================

def ejecutar_optimizacion(parametros_id: int) -> Dict[str, Any]:
    """
    Ejecuta un modelo de optimización.

    Args:
        parametros_id: ID del escenario (ParametrosModelo).

    Returns:
        Dict con resultado o {'error': 'mensaje claro'}.
    """
    inicio = time.time()
    logger.info(f"Iniciando optimización — parámetros ID: {parametros_id}")

    try:
        # 1. Parámetros
        try:
            parametros = ParametrosModelo.objects.get(pk=parametros_id)
        except ParametrosModelo.DoesNotExist:
            raise OptimizacionError(
                f"El escenario #{parametros_id} no existe. "
                "Verifique el ID o cree un nuevo escenario."
            )

        # 2. Datos
        demandas = list(PuntoDemanda.objects.select_related('parroquia'))
        candidatos = list(SitioCandidato.objects.filter(disponible=True))

        if parametros.filtro_estado:
            demandas = [
                d for d in demandas
                if d.parroquia and d.parroquia.estado_id == parametros.filtro_estado_id
            ]
            candidatos = [
                c for c in candidatos
                if c.ubicacion and c.ubicacion.within(parametros.filtro_estado.geom)
            ]

        _validar_entrada(demandas, candidatos, parametros)

        # 3. Preparar
        matriz = _matriz_distancias(demandas, candidatos)
        ponderaciones = {d.id: _ponderacion_demanda(d, parametros) for d in demandas}

        # 4. Ejecutar
        tipo = parametros.tipo_modelo
        if tipo == 'pmediana':
            resultado = _pmediana(demandas, candidatos, parametros, matriz, ponderaciones)
        elif tipo == 'pcentro':
            resultado = _pcentro(demandas, candidatos, parametros, matriz)
        elif tipo == 'cobertura':
            resultado = _cobertura(demandas, candidatos, parametros, matriz)
        elif tipo == 'capacidades':
            resultado = _capacidades(demandas, candidatos, parametros, matriz, ponderaciones)
        else:
            raise OptimizacionError(f"Modelo '{tipo}' no implementado")

        # 5. Enriquecer
        resultado['tiempo_ejecucion_seg'] = round(time.time() - inicio, 2)
        resultado['escenario'] = parametros.nombre_escenario
        resultado['tipo_modelo'] = tipo

        return resultado

    except OptimizacionError as e:
        logger.warning(f"Optimización rechazada: {e}")
        return {'error': str(e), 'tipo_error': 'validacion'}

    except Exception as e:
        logger.error(f"Error inesperado: {e}", exc_info=True)
        return {
            'error': f"Error inesperado: {str(e)}. Revise los logs del servidor.",
            'tipo_error': 'interno',
        }