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

from django.utils import timezone

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
    # Microsegundos evitan colisiones cuando se generan varios reportes
    # del mismo tipo durante el mismo segundo.
    ts = timezone.localtime().strftime('%Y%m%d_%H%M%S_%f')
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

def generar_excel_zonas_afectadas(desde=None, hasta=None, as_of=None) -> Optional[str]:
    """Genera Excel profesional de zonas afectadas, con filtro temporal."""
    df = services.df_zonas_afectadas(desde=desde, hasta=hasta, as_of=as_of)
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

        _formatear_excel(ruta, 'Reporte de Zonas Afectadas', desde, hasta, as_of)
        logger.info(f"Excel zonas generado: {ruta}")
        return ruta
    except Exception as e:
        logger.error(f"Error generando Excel zonas: {e}", exc_info=True)
        return None


def generar_excel_estadisticas_generales(desde=None, hasta=None, as_of=None) -> Optional[str]:
    """Genera Excel general profesional, con filtro temporal."""
    ruta = os.path.join(_reportes_dir(), _nombre_archivo('estadisticas', '.xlsx'))

    try:
        r = services.resumen_general(desde=desde, hasta=hasta, as_of=as_of)
        if not r or not any(r.values()):
            logger.info("Sin datos para estadísticas generales")
            return None

        with pd.ExcelWriter(ruta, engine='openpyxl') as writer:
            services.df_por_estado(desde=desde, hasta=hasta, as_of=as_of).to_excel(writer, sheet_name='Por Estado', index=False)
            services.df_refugios(as_of=as_of).to_excel(writer, sheet_name='Refugios', index=False)
            services.df_demandas(as_of=as_of).to_excel(writer, sheet_name='Puntos de Demanda', index=False)
            services.df_eventos(desde=desde, hasta=hasta, as_of=as_of).to_excel(writer, sheet_name='Eventos', index=False)

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

        _formatear_excel(ruta, 'Reporte Estadístico General', desde, hasta, as_of)
        logger.info(f"Excel general generado: {ruta}")
        return ruta
    except Exception as e:
        logger.error(f"Error generando Excel general: {e}", exc_info=True)
        return None


# ============================================================
# FORMATO EXCEL
# ============================================================

def _formatear_excel(ruta: str, titulo: str, desde=None, hasta=None, as_of=None) -> None:
    """Aplica formato profesional, impresión y metadatos a todas las hojas."""
    from openpyxl import load_workbook
    from openpyxl.styles import Alignment, Font, PatternFill, Border, Side
    from openpyxl.utils import get_column_letter
    from openpyxl.worksheet.page import PageMargins

    wb = load_workbook(ruta)
    azul = '496A72'
    borde = Side(style='thin', color='D8D1C7')
    rango = ' / '.join(
        x for x in (
            f"Desde {timezone.localtime(desde).strftime('%d/%m/%Y %H:%M')}" if desde else None,
            f"Hasta {timezone.localtime(hasta).strftime('%d/%m/%Y %H:%M')}" if hasta else None,
        ) if x
    ) or 'Sin filtro temporal'
    for ws in wb.worksheets:
        ws.freeze_panes = 'A2'
        ws.auto_filter.ref = ws.dimensions
        ws.sheet_view.showGridLines = False
        ws.oddFooter.center.text = 'CobijoVzla · &P de &N'
        ws.oddFooter.right.text = '&D &T'
        ws.page_setup.orientation = 'landscape'
        ws.page_setup.fitToWidth = 1
        ws.page_setup.fitToHeight = 0
        ws.sheet_properties.pageSetUpPr.fitToPage = True
        ws.page_margins = PageMargins(left=0.3, right=0.3, top=0.6, bottom=0.6, header=0.3, footer=0.3)
        for cell in ws[1]:
            cell.font = Font(bold=True, color='FFFFFF')
            cell.fill = PatternFill('solid', fgColor=azul)
            cell.alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)
            cell.border = Border(bottom=borde)
        for row in ws.iter_rows(min_row=2):
            for cell in row:
                cell.alignment = Alignment(vertical='top', wrap_text=True)
                cell.border = Border(bottom=borde)
        for col in range(1, ws.max_column + 1):
            letter = get_column_letter(col)
            max_len = min(max(len(str(ws.cell(row=r, column=col).value or '')) for r in range(1, min(ws.max_row, 100) + 1)) + 2, 45)
            ws.column_dimensions[letter].width = max(10, max_len)
        ws.row_dimensions[1].height = 28
        ws.print_title_rows = '1:1'
        ws.oddHeader.left.text = f'&B{titulo}&B'
        ws.oddHeader.right.text = rango
    wb.save(ruta)

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
        'azul': colors.HexColor('#496A72'),
        'naranja': colors.HexColor('#B9785C'),
        'verde': colors.HexColor('#6E927A'),
        'gris': colors.grey,
        'beige': colors.beige,
        'blanco': colors.white,
    }


def generar_pdf_zonas_afectadas(desde=None, hasta=None, as_of=None) -> Optional[str]:
    """Genera PDF de zonas afectadas en formato landscape."""
    from reportlab.lib.pagesizes import letter, landscape
    from reportlab.platypus import (
        SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer,
    )

    df = services.df_zonas_afectadas(desde=desde, hasta=hasta, as_of=as_of)
    if df.empty:
        logger.info("Sin datos de zonas afectadas")
        return None

    ruta = os.path.join(_reportes_dir(), _nombre_archivo('zonas_afectadas', '.pdf'))

    try:
        styles = _estilos_pdf()
        c = _colores_pdf()

        doc = SimpleDocTemplate(ruta, pagesize=landscape(letter), leftMargin=24, rightMargin=24, topMargin=42, bottomMargin=36)
        elementos = [
            Paragraph('Reporte de Zonas Afectadas', styles['titulo']),
            Paragraph(
                f'Generado: {timezone.localtime().strftime("%d/%m/%Y %H:%M")}',
                styles['normal'],
            ),
            Paragraph(
                'Referencia histórica: ' + timezone.localtime(as_of).strftime('%d/%m/%Y %H:%M') if as_of else\n                'Período: ' + (timezone.localtime(desde).strftime('%d/%m/%Y %H:%M') if desde else 'inicio') +
                ' → ' + (timezone.localtime(hasta).strftime('%d/%m/%Y %H:%M') if hasta else 'actualidad'),
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

        def _pie_pagina(canvas, doc):
            canvas.saveState()
            canvas.setFont('Helvetica', 7)
            canvas.drawString(doc.leftMargin, 18, 'CobijoVzla · Reporte generado por el sistema')
            canvas.drawRightString(doc.pagesize[0] - doc.rightMargin, 18, f'Página {doc.page}')
            canvas.restoreState()

        doc.build(elementos, onFirstPage=_pie_pagina, onLaterPages=_pie_pagina)
        logger.info(f"PDF zonas generado: {ruta}")
        return ruta
    except Exception as e:
        logger.error(f"Error generando PDF zonas: {e}", exc_info=True)
        return None


def generar_pdf_estadisticas_generales(desde=None, hasta=None, as_of=None) -> Optional[str]:
    """Genera PDF con estadísticas generales."""
    from reportlab.lib.pagesizes import letter
    from reportlab.platypus import (
        SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer,
    )

    r = services.resumen_general(desde=desde, hasta=hasta, as_of=as_of)
    if not r or not any(r.values()):
        logger.info("Sin datos para estadísticas generales")
        return None

    ruta = os.path.join(_reportes_dir(), _nombre_archivo('estadisticas', '.pdf'))

    try:
        styles = _estilos_pdf()
        c = _colores_pdf()

        doc = SimpleDocTemplate(ruta, pagesize=letter, leftMargin=36, rightMargin=36, topMargin=42, bottomMargin=36)
        elementos = [
            Paragraph('Reporte Estadístico General', styles['titulo']),
            Paragraph(
                f'Generado: {timezone.localtime().strftime("%d/%m/%Y %H:%M")}',
                styles['normal'],
            ),
            Paragraph(
                'Período: ' + (timezone.localtime(desde).strftime('%d/%m/%Y %H:%M') if desde else 'inicio') +
                ' → ' + (timezone.localtime(hasta).strftime('%d/%m/%Y %H:%M') if hasta else 'actualidad'),
                styles['normal'],
            ),
            Spacer(1, 20),
        ]

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
        df_estados = services.df_por_estado(desde=desde, hasta=hasta)

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

        def _pie_pagina(canvas, doc):
            canvas.saveState()
            canvas.setFont('Helvetica', 7)
            canvas.drawString(doc.leftMargin, 18, 'CobijoVzla · Reporte generado por el sistema')
            canvas.drawRightString(doc.pagesize[0] - doc.rightMargin, 18, f'Página {doc.page}')
            canvas.restoreState()

        doc.build(elementos, onFirstPage=_pie_pagina, onLaterPages=_pie_pagina)
        logger.info(f"PDF general generado: {ruta}")
        return ruta
    except Exception as e:
        logger.error(f"Error generando PDF general: {e}", exc_info=True)
        return None