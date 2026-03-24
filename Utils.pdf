import os
from fpdf import FPDF
from config import LOGO_PATH


def limpiar_texto(texto):
    if not texto:
        return "N/A"
    return str(texto)


def generar_pdf(inc, comentarios):
    pdf = FPDF()
    pdf.add_page()

    if os.path.exists(LOGO_PATH):
        pdf.image(LOGO_PATH, x=10, y=8, w=35)
        pdf.set_xy(50, 15)
    else:
        pdf.set_xy(10, 15)

    pdf.set_font("Helvetica", style="B", size=22)
    pdf.set_text_color(255, 204, 0)
    pdf.cell(0, 15, text="VAPA Service Desk", new_x="LMARGIN", new_y="NEXT", align='L')
    pdf.set_text_color(26, 26, 26)
    pdf.set_y(45)

    pdf.set_font("Helvetica", style="B", size=16)
    pdf.cell(0, 10, text=limpiar_texto(f"Reporte de Incidencia #{inc[0]}"),
             new_x="LMARGIN", new_y="NEXT", align='C')

    prio   = inc[9]  if len(inc) > 9  else 'Media'
    cat    = inc[10] if len(inc) > 10 else 'Otros'
    limite = inc[11] if len(inc) > 11 and inc[11] else 'Sin límite'
    resol  = inc[12] if len(inc) > 12 and inc[12] else 'Pendiente'

    pdf.set_font("Helvetica", size=12)
    pdf.ln(5)
    pdf.cell(0, 10, text=limpiar_texto(f"Titulo: {inc[1]}"),                                    new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 10, text=limpiar_texto(f"Categoria: {cat} | Prioridad: {prio}"),                new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 10, text=limpiar_texto(f"Reportado por: {inc[3]} | Asignado a: {inc[4]}"),     new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 10, text=limpiar_texto(f"Estado: {inc[5]}"),                                    new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 10, text=limpiar_texto(f"Fecha Creacion: {inc[6]}"),                            new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 10, text=limpiar_texto(f"Fecha Limite: {limite} | Fecha Resolucion: {resol}"), new_x="LMARGIN", new_y="NEXT")

    pdf.ln(5)
    pdf.set_font("Helvetica", style="B", size=12)
    pdf.set_fill_color(255, 204, 0)
    pdf.cell(0, 8, text=" Descripcion:", new_x="LMARGIN", new_y="NEXT", fill=True)
    pdf.set_font("Helvetica", size=11)
    pdf.multi_cell(0, 8, text=limpiar_texto(inc[2]))

    if inc[8]:
        pdf.ln(5)
        pdf.set_font("Helvetica", style="B", size=12)
        pdf.cell(0, 8, text=" Informe Tecnico Final:", new_x="LMARGIN", new_y="NEXT", fill=True)
        pdf.set_font("Helvetica", size=11)
        pdf.multi_cell(0, 8, text=limpiar_texto(inc[8]))

    if comentarios:
        pdf.ln(10)
        pdf.set_font("Helvetica", style="B", size=12)
        pdf.cell(0, 8, text=" Historial de Comentarios:", new_x="LMARGIN", new_y="NEXT", fill=True)
        pdf.set_font("Helvetica", size=10)
        for c_autor, c_fecha, c_texto in comentarios:
            pdf.multi_cell(0, 6, text=limpiar_texto(f"[{c_fecha}] {c_autor}: {c_texto}"))

    return bytes(pdf.output())
