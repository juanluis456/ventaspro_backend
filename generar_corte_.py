import os
from pymongo import MongoClient
from bson import ObjectId
from datetime import datetime
from fpdf import FPDF

# ☁️ CONEXIÓN A LA NUBE
URI_ATLAS = "mongodb+srv://admin_tiendas:Admin12345@cluster0.lqodd.mongodb.net/?appName=Cluster0"
cliente = MongoClient(URI_ATLAS)

def obtener_coleccion_ventas(tienda_id):
    nombre_db = f"tienda_{tienda_id}"
    return cliente[nombre_db]['ventas']

# 🎨 CLASE DE DISEÑO PROFESIONAL PARA EL PDF
# 🎨 CLASE DE DISEÑO PROFESIONAL PARA EL PDF
class PDFMaestro(FPDF):
    def header(self):
        # Barra superior oscura
        self.set_fill_color(30, 41, 59) # Azul marino elegante
        self.rect(0, 0, 210, 25, 'F')
        self.set_y(8)
        self.set_font("Arial", 'B', 16)
        self.set_text_color(255, 255, 255)
        # 🔥 AQUÍ LE QUITAMOS EL MUEBLEXI PARA QUE QUEDE NEUTRO Y PROFESIONAL
        self.cell(0, 10, "REPORTE AUDITADO DE CAJA", ln=True, align='C')
        self.set_text_color(0, 0, 0) # Regresar a texto negro normal
        self.ln(10)

    def footer(self):
        self.set_y(-15)
        self.set_font("Arial", 'I', 8)
        self.set_text_color(128, 128, 128)
        self.cell(0, 10, f"Generado por Sistema POS | Página {self.page_no()}", align='C')
def generar_pdf_corte(tienda_id, fecha_str):
    coleccion_ventas = obtener_coleccion_ventas(tienda_id)
    try:
        fecha_inicio = datetime.strptime(f"{fecha_str} 00:00:00", "%Y-%m-%d %H:%M:%S")
        fecha_fin = datetime.strptime(f"{fecha_str} 23:59:59", "%Y-%m-%d %H:%M:%S")
    except ValueError:
        print("❌ Error: El formato de fecha debe ser YYYY-MM-DD")
        return

    ventas = list(coleccion_ventas.find({"fecha": {"$gte": fecha_inicio, "$lte": fecha_fin}}))
    if not ventas:
        print(f"⚠️ No hay tickets cobrados en {tienda_id} durante el {fecha_str}")
        return

    total_dinero = sum(v.get('total', 0) for v in ventas)
    
    pdf = PDFMaestro()
    pdf.add_page()
    
    # 📌 CABECERA DE LA TIENDA
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 10, f"Sucursal: {tienda_id}   |   Fecha de Corte: {fecha_str}", ln=True)
    pdf.set_font("Arial", '', 11)
    pdf.cell(0, 8, f"Total de Transacciones: {len(ventas)} tickets generados", ln=True)
    pdf.cell(0, 8, f"Dinero Bruto Entrado en Caja: ${total_dinero:.2f}", ln=True)
    pdf.ln(5)

    # 📌 HISTORIAL DETALLADO TICKET POR TICKET
    pdf.set_font("Arial", 'B', 12)
    pdf.set_fill_color(241, 245, 249) # Fondo gris clarito
    pdf.cell(0, 10, " DESGLOSE DETALLADO DE MOVIMIENTOS", ln=True, fill=True)
    pdf.ln(5)

    for v in ventas:
        hora = v['fecha'].strftime("%H:%M:%S") if isinstance(v['fecha'], datetime) else "N/A"
        
        # Título del Ticket
        pdf.set_font("Arial", 'B', 10)
        pdf.set_text_color(37, 99, 235) # Azul
        pdf.cell(110, 8, f"TICKET ID: {str(v['_id'])}")
        pdf.set_text_color(100, 116, 139) # Gris oscuro
        pdf.cell(80, 8, f"Hora: {hora}", ln=True, align='R')
        pdf.set_text_color(0, 0, 0) # Reset a negro

        # Cabecera de la tabla de productos
        pdf.set_font("Arial", 'B', 9)
        pdf.cell(90, 6, "Producto", border='B')
        pdf.cell(30, 6, "Cant.", border='B', align='C')
        pdf.cell(35, 6, "Precio U.", border='B', align='C')
        pdf.cell(35, 6, "Subtotal", border='B', align='R')
        pdf.ln(6)

        # Imprimir todos los productos del ticket
        pdf.set_font("Arial", '', 9)
        for art in v.get('articulos', []):
            nombre = art.get('nombre', 'Producto')[:35]
            cant = float(art.get('cantidad', 0))
            precio = float(art.get('precio', 0))
            subtotal = cant * precio
            
            pdf.cell(90, 6, nombre)
            pdf.cell(30, 6, f"{cant}", align='C')
            pdf.cell(35, 6, f"${precio:.2f}", align='C')
            pdf.cell(35, 6, f"${subtotal:.2f}", align='R')
            pdf.ln(6)

        # Sacar el pago y el cambio de la base de datos
        pdf.ln(2)
        total = float(v.get('total', 0))
        pago_con = float(v.get('pago_con', total)) # Si es una venta vieja, asume que pagó exacto
        cambio = float(v.get('cambio', 0))

        pdf.set_font("Arial", 'B', 10)
        pdf.cell(155, 6, "TOTAL DEL TICKET:", align='R')
        pdf.cell(35, 6, f"${total:.2f}", align='R', ln=True)
        
        pdf.set_font("Arial", '', 9)
        pdf.set_text_color(22, 163, 74) # Verde para la entrada de dinero
        pdf.cell(155, 6, "Efectivo Recibido (Pago con):", align='R')
        pdf.cell(35, 6, f"${pago_con:.2f}", align='R', ln=True)

        pdf.set_text_color(220, 38, 38) # Rojo para la salida de dinero
        pdf.cell(155, 6, "Cambio Entregado:", align='R')
        pdf.cell(35, 6, f"${cambio:.2f}", align='R', ln=True)

        # Línea separadora
        pdf.set_text_color(0,0,0)
        pdf.ln(4)
        pdf.line(10, pdf.get_y(), 200, pdf.get_y())
        pdf.ln(4)

    nombre_archivo = f"Corte_Detallado_{tienda_id}_{fecha_str}.pdf"
    pdf.output(nombre_archivo)
    print(f"✅ ¡Éxito! Reporte auditado guardado como: {nombre_archivo}")

def generar_pdf_ticket(tienda_id, id_venta):
    coleccion_ventas = obtener_coleccion_ventas(tienda_id)
    try:
        venta = coleccion_ventas.find_one({"_id": ObjectId(id_venta)})
    except:
        print("❌ Error: ID no válido.")
        return

    if not venta:
        print("⚠️ Ticket no encontrado.")
        return

    pdf = PDFMaestro()
    pdf.add_page()
    
    pdf.set_font("Arial", 'B', 14)
    pdf.cell(0, 10, f"REIMPRESION DE TICKET - {tienda_id}", ln=True, align='C')
    
    pdf.set_font("Arial", '', 10)
    fecha_ticket = venta['fecha'].strftime("%Y-%m-%d %H:%M:%S") if isinstance(venta['fecha'], datetime) else "N/A"
    pdf.cell(0, 8, f"Folio (ID): {str(venta['_id'])}", ln=True, align='C')
    pdf.cell(0, 8, f"Fecha de emisión: {fecha_ticket}", ln=True, align='C')
    pdf.ln(5)

    pdf.set_font("Arial", 'B', 10)
    pdf.cell(90, 8, "Producto", border=1)
    pdf.cell(30, 8, "Cant.", border=1, align='C')
    pdf.cell(35, 8, "P. Unit", border=1, align='C')
    pdf.cell(35, 8, "Subtotal", border=1, align='C')
    pdf.ln(8)
    
    pdf.set_font("Arial", '', 10)
    for art in venta.get('articulos', []):
        nombre = art.get('nombre', 'Producto')[:30]
        cant = float(art.get('cantidad', 0))
        precio = float(art.get('precio', 0))
        subtotal = cant * precio
        
        pdf.cell(90, 8, nombre, border=1)
        pdf.cell(30, 8, str(cant), border=1, align='C')
        pdf.cell(35, 8, f"${precio:.2f}", border=1, align='C')
        pdf.cell(35, 8, f"${subtotal:.2f}", border=1, align='C')
        pdf.ln(8)
        
    pdf.ln(5)
    total = float(venta.get('total', 0))
    pago_con = float(venta.get('pago_con', total))
    cambio = float(venta.get('cambio', 0))

    pdf.set_font("Arial", 'B', 12)
    pdf.cell(155, 8, "TOTAL A PAGAR:", align='R')
    pdf.cell(35, 8, f"${total:.2f}", align='R', ln=True)

    pdf.set_font("Arial", '', 11)
    pdf.set_text_color(22, 163, 74)
    pdf.cell(155, 8, "Efectivo (Pago con):", align='R')
    pdf.cell(35, 8, f"${pago_con:.2f}", align='R', ln=True)

    pdf.set_text_color(220, 38, 38)
    pdf.cell(155, 8, "Cambio Entregado:", align='R')
    pdf.cell(35, 8, f"${cambio:.2f}", align='R', ln=True)

    nombre_archivo = f"Reimpresion_Ticket_{id_venta}.pdf"
    pdf.output(nombre_archivo)
    print(f"✅ ¡Éxito! Ticket individual guardado como: {nombre_archivo}")

# --- MENÚ INTERACTIVO ---
if __name__ == '__main__':
    print("========================================")
    print(" 🛠️  PANEL DE ADMINISTRADOR MAESTRO 🛠️")
    print("========================================")
    
    tienda = input("👉 Ingresa el ID de la tienda (Ej. VAZCAM_001): ").strip()
    
    print("\n¿Qué reporte profesional necesitas?")
    print("1. Corte de Caja Detallado (Historial Completo)")
    print("2. Reimpresión de Ticket Individual")
    opcion = input("Elige una opción (1 o 2): ").strip()
    
    if opcion == '1':
        fecha = input("\n👉 Ingresa la fecha del corte (Ej. 2026-06-30): ").strip()
        generar_pdf_corte(tienda, fecha)
    elif opcion == '2':
        id_ticket = input("\n👉 Ingresa el ID largote del Ticket: ").strip()
        generar_pdf_ticket(tienda, id_ticket)
    else:
        print("❌ Opción no válida.")