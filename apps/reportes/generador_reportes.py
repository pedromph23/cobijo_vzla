"""
Generador de reportes en Excel y PDF.

Usa `services.py` para obtener los datos y los serializa a archivos.
Los archivos se guardan en `MEDIA_ROOT/reportes/` con nombre único.
"""
from __future__ import annotations

import logging
import os
from datetime import datetime, timedelta
from typing import Optional

import pandas as pd
from django.conf import settings

from . import services


logger = logging.getLogger(__name__)


# ============================================================
# CONFIGURACIÓN
# ============================================================

EXTENSIONES_PERMITIDAS = {'.xlsx', '.pdf'}
DIAS_RETENCION_REPORTES = 7


def _reportes_dir() -> str:
    """Ruta absoluta del directorio de reportes, basada en MEDIA_ROOT."""
    ruta = os.path.join(settings.MEDIA_ROOT, 'reportes')
    os.makedirs(ruta, exist_ok=True)
    return ruta


def _nombre_archivo(prefijo: str, extension: str) -> str:
    """Genera un nombre único con timestamp."""
    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    return f"{prefijo}_{ts}{extension}"


def limpiar_reportes_antiguos(dias: int = DIAS_RETENCION_REPORTES) -> int:
    """
    Elimina reportes con más de `dias` días de antigüedad.

    Returns:
        Cantidad de archivos eliminados.
    """
    try:
        directorio = _reportes_dir()
        limite = datetime.now() - timedelta(days=dias)
        eliminados = 0

        for nombre in os.listdir(directorio):
            ruta = os.path.join(directorio, nombre)
            if not os.path.isfile(ruta):
                continue
            _, ext = os.path.splitext(nombre)
            if ext.lower() not in EXTENSIONES_PERMITIDAS:
                continue
            try:
                if datetime.fromtimestamp(os.path.getmtime(ruta)) < limite:
                    os.remove(ruta)
                    eliminados += 1
            except OSError:
                continue

        if eliminados:
            logger.info(f"Limpiados {eliminados} reportes antiguos (>{dias} días)")
        return eliminados
    except Exception as e:
        logger.warning(f"Error limpiando reportes: {e}")
        return 0


# ============================================================
# EXCEL
# ============================================================

def generar_excel_zonas_afectadas() -> Optional[str]:
    """Genera Excel de zonas afectadas con hojas de resumen."""
    df = services.df_zonas_afectadas()
    if df.empty:
        logger.info("Sin datos de zonas afectadas")
        return None

    ruta = os.path.join(_reportes_dir(), _nombre_archivo('zonas_afectadas', '.xlsx'))

    try:
        with pd.ExcelWriter(ruta, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='Zonas Afectadas', index=False)

            # Resumen por alerta
            resumen_alerta = (
                df.groupby('Nivel Alerta')
                .agg({
                    'Heridos': 'sum',
                    'Fallecidos': 'sum',
                    'Damnificados': 'sum',
                    'ID': 'count',
                })
                .rename(columns={'ID': 'Total Zonas'})
            )
            resumen_alerta.to_excel(writer, sheet_name='Resumen por Alerta')

            # Resumen por evento
            resumen_evento = (
                df.groupby('Tipo Evento')
                .agg({
                    'Heridos': 'sum',
                    'Fallecidos': 'sum',
                    'Damnificados': 'sum',
                    'ID': 'count',
                })
                .rename(columns={'ID': 'Total Zonas'})
            )
            resumen_evento.to_excel(writer, sheet_name='Resumen por Evento')

        logger.info(f"Excel zonas generado: {ruta}")
        return ruta
    except Exception as e:
        logger.error(f"Error generando Excel zonas: {e}", exc_info=True)
        return None


def generar_excel_estadisticas_generales() -> Optional[str]:
    """Genera Excel con estadísticas generales (multi-hoja)."""
    ruta = os.path.join(_reportes_dir(), _nombre_archivo('estadisticas', '.xlsx'))

    try:
        with pd.ExcelWriter(ruta, engine='openpyxl') as writer:
            services.df_por_estado().to_excel(writer, sheet_name='Por Estado', index=False)
            services.df_refugios().to_excel(writer, sheet_name='Refugios', index=False)
            services.df_demandas().to_excel(writer, sheet_name='Puntos de Demanda', index=False)
            services.df_eventos().to_excel(writer, sheet_name='Eventos', index=False)

            r = services.resumen_general()
            resumen_df = pd.DataFrame({
                'Métrica': [
                    'Total Estados', 'Total Parroquias', 'Total Refugios',
                    'Total Puntos de Demanda', 'Total Zonas Afectadas',
                    'Total Eventos', 'Total Heridos', 'Total Fallecidos',
                    'Total Damnificados',
                ],
                'Valor': [
                    r.get('estados', 0), r.get('parroquias', 0),
                    r.get('refugios', 0), r.get('demandas', 0),
                    r.get('zonas', 0), r.get('eventos', 0),
                    r.get('heridos', 0), r.get('fallecidos', 0),
                    r.get('damnificados', 0),
                ],
            })
            resumen_df.to_excel(writer, sheet_name='Resumen General', index=False)

        logger.info(f"Excel general generado: {ruta}")
        return ruta
    except Exception as e:
        logger.error(f"Error generando Excel general: {e}", exc_info=True)
        return None


# ============================================================
# PDF
# ============================================================

def _estilos_pdf():
    """Retorna estilos reutilizables para PDFs."""
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.enums import TA_CENTER

    styles = getSampleStyleSheet()
    return {
        'titulo': ParagraphStyle(
            'Titulo', parent=styles['Heading1'],
            fontSize=18, alignment=TA_CENTER, spaceAfter=20,
        ),
        'subtitulo': styles['Heading2'],
        'normal': styles['Normal'],
    }


def _colores_pdf():
    from reportlab.lib import colors
    return {
        'azul': colors.HexColor('#0066cc'),
        'naranja': colors.HexColor('#ff6600'),
        'verde': colors.HexColor('#28a745'),
        'gris': colors.grey,
        'beige': colors.beige,
        'blanco': colors.white,
    }


def generar_pdf_zonas_afectadas() -> Optional[str]:
    """Genera PDF de zonas afectadas en formato landscape."""
    from reportlab.lib.pagesizes import letter, landscape
    from reportlab.platypus import (
        SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer,
    )

    df = services.df_zonas_afectadas()
    if df.empty:
        logger.info("Sin datos de zonas afectadas")
        return None

    ruta = os.path.join(_reportes_dir(), _nombre_archivo('zonas_afectadas', '.pdf'))

    try:
        styles = _estilos_pdf()
        c = _colores_pdf()

        doc = SimpleDocTemplate(ruta, pagesize=landscape(letter))
        elementos = [
            Paragraph('Reporte de Zonas Afectadas', styles['titulo']),
            Paragraph(
                f'Generado: {datetime.now().strftime("%Y-%m-%d %H:%M")}',
                styles['normal'],
            ),
            Spacer(1, 20),
        ]

        # Tabla principal
        columnas = ['Nombre', 'Evento', 'Nivel', 'Heridos', 'Fallecidos', 'Damnificados']
        filas = [columnas]
        for _, row in df.iterrows():
            filas.append([
                str(row.get('Nombre', ''))[:40],
                str(row.get('Evento', ''))[:30],
                str(row.get('Nivel Alerta', '')),
                str(row.get('Heridos', 0)),
                str(row.get('Fallecidos', 0)),
                str(row.get('Damnificados', 0)),
            ])

        tabla = Table(filas, repeatRows=1)
        tabla.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), c['azul']),
            ('TEXTCOLOR', (0, 0), (-1, 0), c['blanco']),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BACKGROUND', (0, 1), (-1, -1), c['beige']),
            ('GRID', (0, 0), (-1, -1), 0.5, c['gris']),
            ('FONTSIZE', (0, 1), (-1, -1), 8),
        ]))
        elementos.append(tabla)
        elementos.append(Spacer(1, 30))

        # Resumen por alerta
        elementos.append(Paragraph('Resumen por Nivel de Alerta', styles['subtitulo']))
        resumen = (
            df.groupby('Nivel Alerta')
            .agg({'Heridos': 'sum', 'Fallecidos': 'sum', 'Damnificados': 'sum'})
            .reset_index()
        )
        filas_res = [['Nivel Alerta', 'Heridos', 'Fallecidos', 'Damnificados']]
        for _, row in resumen.iterrows():
            filas_res.append([
                str(row.get('Nivel Alerta', '')),
                str(row.get('Heridos', 0)),
                str(row.get('Fallecidos', 0)),
                str(row.get('Damnificados', 0)),
            ])

        tabla_res = Table(filas_res)
        tabla_res.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), c['naranja']),
            ('TEXTCOLOR', (0, 0), (-1, 0), c['blanco']),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('GRID', (0, 0), (-1, -1), 0.5, c['gris']),
        ]))
        elementos.append(tabla_res)

        doc.build(elementos)
        logger.info(f"PDF zonas generado: {ruta}")
        return ruta
    except Exception as e:
        logger.error(f"Error generando PDF zonas: {e}", exc_info=True)
        return None


def generar_pdf_estadisticas_generales() -> Optional[str]:
    """Genera PDF con estadísticas generales."""
    from reportlab.lib.pagesizes import letter
    from reportlab.platypus import (
        SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer,
    )

    ruta = os.path.join(_reportes_dir(), _nombre_archivo('estadisticas', '.pdf'))

    try:
        styles = _estilos_pdf()
        c = _colores_pdf()

        doc = SimpleDocTemplate(ruta, pagesize=letter)
        elementos = [
            Paragraph('Reporte Estadístico General', styles['titulo']),
            Paragraph(
                f'Generado: {datetime.now().strftime("%Y-%m-%d %H:%M")}',
                styles['normal'],
            ),
            Spacer(1, 20),
        ]

        r = services.resumen_general()
        resumen = [
            ['Métrica', 'Valor'],
            ['Total Estados', str(r.get('estados', 0))],
            ['Total Parroquias', str(r.get('parroquias', 0))],
            ['Total Refugios', str(r.get('refugios', 0))],
            ['Total Puntos de Demanda', str(r.get('demandas', 0))],
            ['Total Zonas Afectadas', str(r.get('zonas', 0))],
            ['Total Eventos', str(r.get('eventos', 0))],
            ['Total Heridos', str(r.get('heridos', 0))],
            ['Total Fallecidos', str(r.get('fallecidos', 0))],
            ['Total Damnificados', str(r.get('damnificados', 0))],
        ]

        tabla = Table(resumen, colWidths=[300, 150])
        tabla.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), c['azul']),
            ('TEXTCOLOR', (0, 0), (-1, 0), c['blanco']),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('GRID', (0, 0), (-1, -1), 0.5, c['gris']),
            ('PADDING', (0, 0), (-1, -1), 8),
        ]))
        elementos.append(tabla)
        elementos.append(Spacer(1, 30))

        # Tabla por estado
        elementos.append(Paragraph('Datos por Estado', styles['subtitulo']))
        df_estados = services.df_por_estado()

        filas = [['Estado', 'Parroquias', 'Población', 'Heridos', 'Fallecidos', 'Damnificados']]
        for _, row in df_estados.iterrows():
            filas.append([
                str(row.get('Estado', ''))[:25],
                str(row.get('Total Parroquias', 0)),
                f"{row.get('Población Total', 0):,}".replace(',', '.'),
                str(row.get('Heridos', 0)),
                str(row.get('Fallecidos', 0)),
                str(row.get('Damnificados', 0)),
            ])

        tabla_est = Table(filas, repeatRows=1)
        tabla_est.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), c['verde']),
            ('TEXTCOLOR', (0, 0), (-1, 0), c['blanco']),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('GRID', (0, 0), (-1, -1), 0.5, c['gris']),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
        ]))
        elementos.append(tabla_est)

        doc.build(elementos)
        logger.info(f"PDF general generado: {ruta}")
        return ruta
    except Exception as e:
        logger.error(f"Error generando PDF general: {e}", exc_info=True)
        return None