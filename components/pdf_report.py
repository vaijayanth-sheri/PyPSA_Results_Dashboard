# components/pdf_report.py

import io
import pypsa
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from .utils import _get_network_kpis

def generate_pdf_report(network: pypsa.Network, title: str = "PyPSA Results Report") -> bytes:
    """
    Generates a basic PDF report using ReportLab.
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    styles = getSampleStyleSheet()
    report_elements = []

    report_elements.append(Paragraph(title, styles['h1']))
    report_elements.append(Spacer(1, 0.2 * inch))

    report_elements.append(Paragraph("<b>Network Overview</b>", styles['h2']))
    kpis = _get_network_kpis(network)
    for key, val in kpis.items():
        report_elements.append(Paragraph(f"{key.replace('_', ' ').title()}: {val:,.0f}" if isinstance(val, (int, float)) else f"{key.replace('_', ' ').title()}: {val}", styles['Normal']))
    
    report_elements.append(Spacer(1, 0.2 * inch))

    if not network.generators.empty and 'p_nom' in network.generators.columns and 'carrier' in network.generators.columns:
        report_elements.append(Paragraph("<b>Top 5 Generators (by p_nom)</b>", styles['h2']))
        gen_data = [['Name', 'Carrier', 'p_nom (MW)']]
        top_gens = network.generators.nlargest(5, 'p_nom')[['carrier', 'p_nom']]
        for idx, row in top_gens.iterrows():
            gen_data.append([idx, row['carrier'], f"{row['p_nom']:.2f}"])
        
        table = Table(gen_data)
        table.setStyle(TableStyle([('BACKGROUND', (0,0), (-1,0), colors.grey), ('TEXTCOLOR',(0,0),(-1,0),colors.whitesmoke)]))
        report_elements.append(table)

    doc.build(report_elements)
    buffer.seek(0)
    return buffer.getvalue()