"""
Generador de reportes estadísticos para CobijoVzla.

Este módulo genera reportes en formato Excel y PDF usando pandas.
"""

import os
import logging
from datetime import datetime
from typing import Dict, List, Optional

import pandas as pd
from django.db.models import Count, Sum, Avg, Q
from django.utils import timezone

from apps.core.models import (
    Estado,
    Parroquia,
    PuntoDemanda,
    SitioCandidato,
    RefugioExistente,
    ZonaAfectada,
    ResultadoOptimizacion,
)
from apps.emergencias.models import Evento, Reporte

# Configurar logger
logger = logging.getLogger(__name__)

# Directorio para guardar reportes
REPORTES_DIR = os.path.join('media', 'reportes')


def asegurar_directorio():
    """Crea el directorio de reportes si no existe."""
    os.makedirs(REPORTES_DIR, exist_ok=True)


# ============================================================
# FUNCIONES DE DATOS
# ============================================================

def obtener_datos_zonas_afectadas() -> pd.DataFrame:
    """
    Obtiene datos de zonas afectadas como DataFrame.
    """
    zonas = ZonaAfectada.objects.select_related('evento').all()
    
    data = []
    for z in zonas:
        data.append({
            'ID': z.id,
            'Nombre': z.nombre,
            'Evento': z.evento.nombre if z.evento else 'Sin evento',
            'Tipo Evento': z.evento.tipo if z.evento else '',
            'Nivel Alerta': z.nivel_alerta.upper(),
            'Descripción': z.descripcion or '',
            'Heridos': z.heridos or 0,
            'Fallecidos': z.fallecidos or 0,
            'Damnificados': z.damnificados or 0,
            'Fecha Inicio': z.fecha_inicio.strftime('%Y-%m-%d %H:%M') if z.fecha_inicio else '',
            'Fecha Fin': z.fecha_fin.strftime('%Y-%m-%d %H:%M') if z.fecha_fin else 'Activa',
        })
    
    return pd.DataFrame(data)


def obtener_datos_por_estado() -> pd.DataFrame:
    """
    Obtiene datos agregados por estado.
    """
    estados = Estado.objects.all()
    
    data = []
    for estado in estados:
        parroquias = Parroquia.objects.filter(estado=estado)
        zonas = ZonaAfectada.objects.filter(geom__within=estado.geom) if estado.geom else []
        
        data.append({
            'Estado': estado.nombre,
            'Total Parroquias': parroquias.count(),
            'Población Total': parroquias.aggregate(Sum('poblacion'))['poblacion__sum'] or 0,
            'Total Zonas Afectadas': len(zonas),
            'Heridos': sum(z.heridos for z in zonas if z.heridos),
            'Fallecidos': sum(z.fallecidos for z in zonas if z.fallecidos),
            'Damnificados': sum(z.damnificados for z in zonas if z.damnificados),
            'Vulnerabilidad Promedio': parroquias.aggregate(Avg('indice_vulnerabilidad'))['indice_vulnerabilidad__avg'] or 0,
        })
    
    return pd.DataFrame(data)


def obtener_datos_refugios() -> pd.DataFrame:
    """
    Obtiene datos de refugios como DataFrame.
    """
    refugios = RefugioExistente.objects.all()
    
    data = []
    for r in refugios:
        data.append({
            'ID': r.id,
            'Nombre': r.nombre,
            'Dirección': r.direccion,
            'Capacidad Total': r.capacidad_total,
            'Capacidad Disponible': r.capacidad_disponible,
            'Ocupación': f"{((r.capacidad_total - r.capacidad_disponible) / r.capacidad_total * 100) if r.capacidad_total > 0 else 0:.1f}%",
            'Servicios': ', '.join(r.servicios) if isinstance(r.servicios, list) else '',
            'Operativo': 'Sí' if r.operativo else 'No',
            'Teléfono': r.telefono or '',
        })
    
    return pd.DataFrame(data)


def obtener_datos_demandas() -> pd.DataFrame:
    """
    Obtiene datos de puntos de demanda.
    """
    demandas = PuntoDemanda.objects.select_related('parroquia__estado').all()
    
    data = []
    for d in demandas:
        data.append({
            'ID': d.id,
            'Nombre': d.nombre,
            'Parroquia': d.parroquia.nombre if d.parroquia else '',
            'Estado': d.parroquia.estado.nombre if d.parroquia and d.parroquia.estado else '',
            'Población': d.poblacion,
            'Vulnerabilidad': d.vulnerabilidad,
        })
    
    return pd.DataFrame(data)


def obtener_datos_eventos() -> pd.DataFrame:
    """
    Obtiene datos de eventos.
    """
    eventos = Evento.objects.all()
    
    data = []
    for e in eventos:
        data.append({
            'ID': e.id,
            'Nombre': e.nombre,
            'Tipo': e.tipo,
            'Fecha': e.fecha.strftime('%Y-%m-%d %H:%M'),
            'Magnitud': e.magnitud or 0,
            'Descripción': e.descripcion or '',
            'Activo': 'Sí' if e.activo else 'No',
        })
    
    return pd.DataFrame(data)


# ============================================================
# FUNCIONES DE EXPORTACIÓN EXCEL
# ============================================================

def generar_excel_zonas_afectadas() -> str:
    """
    Genera reporte Excel de zonas afectadas.
    
    Returns:
        str: Ruta del archivo generado
    """
    asegurar_directorio()
    
    df = obtener_datos_zonas_afectadas()
    
    if df.empty:
        return None
    
    nombre_archivo = f"reporte_zonas_afectadas_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    ruta = os.path.join(REPORTES_DIR, nombre_archivo)
    
    with pd.ExcelWriter(ruta, engine='openpyxl') as writer:
        # Hoja principal
        df.to_excel(writer, sheet_name='Zonas Afectadas', index=False)
        
        # Hoja resumen por nivel de alerta
        resumen_alerta = df.groupby('Nivel Alerta').agg({
            'Heridos': 'sum',
            'Fallecidos': 'sum',
            'Damnificados': 'sum',
            'ID': 'count'
        }).rename(columns={'ID': 'Total Zonas'})
        resumen_alerta.to_excel(writer, sheet_name='Resumen por Alerta')
        
        # Hoja resumen por tipo de evento
        resumen_evento = df.groupby('Tipo Evento').agg({
            'Heridos': 'sum',
            'Fallecidos': 'sum',
            'Damnificados': 'sum',
            'ID': 'count'
        }).rename(columns={'ID': 'Total Zonas'})
        resumen_evento.to_excel(writer, sheet_name='Resumen por Evento')
    
    logger.info(f"Reporte Excel generado: {ruta}")
    return ruta


def generar_excel_estadisticas_generales() -> str:
    """
    Genera reporte Excel con estadísticas generales.
    
    Returns:
        str: Ruta del archivo generado
    """
    asegurar_directorio()
    
    nombre_archivo = f"reporte_estadisticas_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    ruta = os.path.join(REPORTES_DIR, nombre_archivo)
    
    with pd.ExcelWriter(ruta, engine='openpyxl') as writer:
        # Estados
        df_estados = obtener_datos_por_estado()
        df_estados.to_excel(writer, sheet_name='Por Estado', index=False)
        
        # Refugios
        df_refugios = obtener_datos_refugios()
        df_refugios.to_excel(writer, sheet_name='Refugios', index=False)
        
        # Demandas
        df_demandas = obtener_datos_demandas()
        df_demandas.to_excel(writer, sheet_name='Puntos de Demanda', index=False)
        
        # Eventos
        df_eventos = obtener_datos_eventos()
        df_eventos.to_excel(writer, sheet_name='Eventos', index=False)
        
        # Resumen general
        resumen = pd.DataFrame({
            'Métrica': [
                'Total Estados',
                'Total Parroquias',
                'Total Refugios',
                'Total Puntos de Demanda',
                'Total Zonas Afectadas',
                'Total Eventos',
                'Total Heridos',
                'Total Fallecidos',
                'Total Damnificados',
            ],
            'Valor': [
                Estado.objects.count(),
                Parroquia.objects.count(),
                RefugioExistente.objects.count(),
                PuntoDemanda.objects.count(),
                ZonaAfectada.objects.count(),
                Evento.objects.count(),
                ZonaAfectada.objects.aggregate(Sum('heridos'))['heridos__sum'] or 0,
                ZonaAfectada.objects.aggregate(Sum('fallecidos'))['fallecidos__sum'] or 0,
                ZonaAfectada.objects.aggregate(Sum('damnificados'))['damnificados__sum'] or 0,
            ]
        })
        resumen.to_excel(writer, sheet_name='Resumen General', index=False)
    
    logger.info(f"Reporte Excel general generado: {ruta}")
    return ruta


# ============================================================
# FUNCIONES DE EXPORTACIÓN PDF
# ============================================================

def generar_pdf_zonas_afectadas() -> str:
    """
    Genera reporte PDF de zonas afectadas.
    
    Returns:
        str: Ruta del archivo generado
    """
    from reportlab.lib.pagesizes import letter, landscape
    from reportlab.lib import colors
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    
    asegurar_directorio()
    
    df = obtener_datos_zonas_afectadas()
    
    if df.empty:
        return None
    
    nombre_archivo = f"reporte_zonas_afectadas_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    ruta = os.path.join(REPORTES_DIR, nombre_archivo)
    
    # Crear documento
    doc = SimpleDocTemplate(ruta, pagesize=landscape(letter))
    elementos = []
    
    # Estilos
    styles = getSampleStyleSheet()
    titulo_style = ParagraphStyle(
        'Titulo',
        parent=styles['Heading1'],
        fontSize=18,
        alignment=1,
        spaceAfter=20
    )
    
    # Título
    elementos.append(Paragraph('Reporte de Zonas Afectadas', titulo_style))
    elementos.append(Paragraph(f'Generado: {datetime.now().strftime("%Y-%m-%d %H:%M")}', styles['Normal']))
    elementos.append(Spacer(1, 20))
    
    # Datos para tabla
    columnas = ['Nombre', 'Evento', 'Nivel Alerta', 'Heridos', 'Fallecidos', 'Damnificados']
    filas = [columnas]
    
    for _, row in df.iterrows():
        filas.append([
            row['Nombre'],
            row['Evento'],
            row['Nivel Alerta'],
            str(row['Heridos']),
            str(row['Fallecidos']),
            str(row['Damnificados']),
        ])
    
    # Crear tabla
    tabla = Table(filas)
    tabla.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#0066cc')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.grey),
        ('FONTSIZE', (0, 1), (-1, -1), 9),
    ]))
    
    elementos.append(tabla)
    
    # Resumen
    elementos.append(Spacer(1, 30))
    elementos.append(Paragraph('Resumen por Nivel de Alerta', styles['Heading2']))
    
    resumen = df.groupby('Nivel Alerta').agg({
        'Heridos': 'sum',
        'Fallecidos': 'sum',
        'Damnificados': 'sum'
    }).reset_index()
    
    filas_resumen = [['Nivel Alerta', 'Heridos', 'Fallecidos', 'Damnificados']]
    for _, row in resumen.iterrows():
        filas_resumen.append([
            row['Nivel Alerta'],
            str(row['Heridos']),
            str(row['Fallecidos']),
            str(row['Damnificados']),
        ])
    
    tabla_resumen = Table(filas_resumen)
    tabla_resumen.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#ff6600')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('GRID', (0, 0), (-1, -1), 1, colors.grey),
    ]))
    
    elementos.append(tabla_resumen)
    
    doc.build(elementos)
    
    logger.info(f"Reporte PDF generado: {ruta}")
    return ruta


def generar_pdf_estadisticas_generales() -> str:
    """
    Genera reporte PDF con estadísticas generales.
    """
    from reportlab.lib.pagesizes import letter
    from reportlab.lib import colors
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    
    asegurar_directorio()
    
    nombre_archivo = f"reporte_estadisticas_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    ruta = os.path.join(REPORTES_DIR, nombre_archivo)
    
    doc = SimpleDocTemplate(ruta, pagesize=letter)
    elementos = []
    
    styles = getSampleStyleSheet()
    titulo_style = ParagraphStyle('Titulo', parent=styles['Heading1'], fontSize=18, alignment=1, spaceAfter=20)
    
    elementos.append(Paragraph('Reporte Estadístico General', titulo_style))
    elementos.append(Paragraph(f'Generado: {datetime.now().strftime("%Y-%m-%d %H:%M")}', styles['Normal']))
    elementos.append(Spacer(1, 20))
    
    # Resumen general
    resumen = [
        ['Métrica', 'Valor'],
        ['Total Estados', str(Estado.objects.count())],
        ['Total Parroquias', str(Parroquia.objects.count())],
        ['Total Refugios', str(RefugioExistente.objects.count())],
        ['Total Puntos de Demanda', str(PuntoDemanda.objects.count())],
        ['Total Zonas Afectadas', str(ZonaAfectada.objects.count())],
        ['Total Eventos', str(Evento.objects.count())],
        ['Total Heridos', str(ZonaAfectada.objects.aggregate(Sum('heridos'))['heridos__sum'] or 0)],
        ['Total Fallecidos', str(ZonaAfectada.objects.aggregate(Sum('fallecidos'))['fallecidos__sum'] or 0)],
        ['Total Damnificados', str(ZonaAfectada.objects.aggregate(Sum('damnificados'))['damnificados__sum'] or 0)],
    ]
    
    tabla_resumen = Table(resumen, colWidths=[300, 150])
    tabla_resumen.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#0066cc')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('GRID', (0, 0), (-1, -1), 1, colors.grey),
        ('PADDING', (0, 0), (-1, -1), 8),
    ]))
    
    elementos.append(tabla_resumen)
    elementos.append(Spacer(1, 30))
    
    # Datos por estado
    elementos.append(Paragraph('Datos por Estado', styles['Heading2']))
    df_estados = obtener_datos_por_estado()
    
    filas_estados = [['Estado', 'Parroquias', 'Población', 'Heridos', 'Fallecidos', 'Damnificados']]
    for _, row in df_estados.iterrows():
        filas_estados.append([
            row['Estado'],
            str(row['Total Parroquias']),
            str(row['Población Total']),
            str(row['Heridos']),
            str(row['Fallecidos']),
            str(row['Damnificados']),
        ])
    
    tabla_estados = Table(filas_estados, repeatRows=1)
    tabla_estados.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#28a745')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('GRID', (0, 0), (-1, -1), 1, colors.grey),
        ('FONTSIZE', (0, 0), (-1, -1), 8),
    ]))
    
    elementos.append(tabla_estados)
    
    doc.build(elementos)
    
    logger.info(f"Reporte PDF general generado: {ruta}")
    return ruta