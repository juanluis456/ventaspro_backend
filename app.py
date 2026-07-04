from flask import Flask, request, jsonify
from flask_cors import CORS
from pymongo import MongoClient
from datetime import datetime, time
from bson import ObjectId

app = Flask(__name__)
CORS(app)

# ☁️ 1. CONEXIÓN A LA NUBE 
URI_ATLAS = "mongodb+srv://admin_tiendas:Admin12345@cluster0.lqodd.mongodb.net/?appName=Cluster0"
cliente = MongoClient(URI_ATLAS)

# 🔐 EL GUARDIA DE SEGURIDAD (AHORA LEE MÓDULOS VIP)
@app.route('/api/login', methods=['POST'])
def login():
    datos = request.json
    usuario_recibido = datos.get('usuario')
    password_recibida = datos.get('password')

    db_central = cliente['punto_de_venta_cloud']
    coleccion_usuarios = db_central['usuarios']

    usuario_db = coleccion_usuarios.find_one({"usuario": usuario_recibido, "password": password_recibida})

    if usuario_db:
        # 🔥 AQUÍ ESTÁ LA MAGIA: Si no tiene la lista de módulos en Mongo, le mandamos una lista vacía []
        modulos_vip = usuario_db.get("modulos_extra", [])

        return jsonify({
            "exito": True, 
            "id_tienda": usuario_db.get("id_tienda"),
            "nombre": usuario_db.get("nombre_tienda"),
            "modulos": modulos_vip  # <-- Mandamos los permisos a React
        }), 200
    else:
        return jsonify({"exito": False, "mensaje": "Usuario o contraseña incorrectos."}), 401

def obtener_colecciones_privadas():
    tienda_id = request.headers.get('Tienda-ID')
    if not tienda_id:
        return None, None, None
    db_privada = cliente[tienda_id]
    return tienda_id, db_privada['productos'], db_privada['ventas']

@app.route('/api/productos', methods=['GET'])
def obtener_todos_los_productos():
    tienda_id, coleccion_productos, _ = obtener_colecciones_privadas()
    if not tienda_id: return jsonify({"error": "Falta el ID de la tienda"}), 400
    productos = list(coleccion_productos.find({"id_tienda": tienda_id}, {"_id": 0}))
    return jsonify(productos), 200

@app.route('/api/productos/<codigo>', methods=['GET'])
def buscar_producto(codigo):
    tienda_id, coleccion_productos, _ = obtener_colecciones_privadas()
    if not tienda_id: return jsonify({"error": "Falta el ID de la tienda"}), 400
    producto = coleccion_productos.find_one({"codigo": codigo, "id_tienda": tienda_id}, {"_id": 0})
    if producto: return jsonify(producto), 200
    else: return jsonify({"error": "Producto no encontrado"}), 404

@app.route('/api/productos', methods=['POST'])
def agregar_producto():
    tienda_id, coleccion_productos, _ = obtener_colecciones_privadas()
    if not tienda_id: return jsonify({"error": "Falta el ID de la tienda"}), 400
    datos = request.json
    existe = coleccion_productos.find_one({"codigo": datos['codigo'], "id_tienda": tienda_id})
    if existe: return jsonify({"error": "Este código ya está registrado en tu tienda."}), 400
    nuevo_producto = {
        "id_tienda": tienda_id, "codigo": datos['codigo'], "nombre": datos['nombre'],
        "precio": float(datos['precio']), "precio_compra": float(datos.get('precio_compra', 0)),
        "stock": float(datos['stock']), "tipo_unidad": datos.get('tipo_unidad', 'pza'),
        "contenido": datos.get('contenido', '')
    }
    coleccion_productos.insert_one(nuevo_producto)
    return jsonify({"mensaje": "Producto guardado con éxito"}), 201

@app.route('/api/productos/surtir_masivo', methods=['PUT'])
def surtir_producto_masivo():
    tienda_id, coleccion_productos, _ = obtener_colecciones_privadas()
    if not tienda_id: return jsonify({"error": "Falta el ID de la tienda"}), 400
    datos = request.json
    productos_actualizados = 0
    for prod in datos['productos']:
        codigo = prod.get('codigo'); cantidad = float(prod.get('cantidad', 0))
        if codigo and cantidad > 0:
            resultado = coleccion_productos.update_one({"codigo": codigo, "id_tienda": tienda_id}, {"$inc": {"stock": cantidad}})
            if resultado.matched_count > 0: productos_actualizados += 1
    return jsonify({"mensaje": f"¡Cargamento aplicado! Se reabastecieron {productos_actualizados} productos."}), 200
    
@app.route('/api/productos/<codigo>', methods=['PUT'])
def editar_producto(codigo):
    tienda_id, coleccion_productos, _ = obtener_colecciones_privadas()
    if not tienda_id: return jsonify({"error": "Falta el ID de la tienda"}), 400
    datos = request.json
    actualizacion = {}
    if 'nombre' in datos: actualizacion['nombre'] = datos['nombre']
    if 'precio' in datos: actualizacion['precio'] = float(datos['precio'])
    if 'precio_compra' in datos: actualizacion['precio_compra'] = float(datos['precio_compra'])
    if 'stock' in datos: actualizacion['stock'] = float(datos['stock'])
    if 'tipo_unidad' in datos: actualizacion['tipo_unidad'] = datos['tipo_unidad']
    if 'contenido' in datos: actualizacion['contenido'] = datos['contenido']
    resultado = coleccion_productos.update_one({"codigo": codigo, "id_tienda": tienda_id}, {"$set": actualizacion})
    if resultado.matched_count > 0: return jsonify({"mensaje": "¡Producto actualizado!"}), 200
    else: return jsonify({"error": "Producto no encontrado"}), 404

@app.route('/api/productos/<codigo>', methods=['DELETE'])
def borrar_producto(codigo):
    tienda_id, coleccion_productos, _ = obtener_colecciones_privadas()
    if not tienda_id: return jsonify({"error": "Falta el ID de la tienda"}), 400
    resultado = coleccion_productos.delete_one({"codigo": codigo, "id_tienda": tienda_id})
    if resultado.deleted_count > 0: return jsonify({"mensaje": "Producto eliminado"}), 200
    else: return jsonify({"error": "Producto no encontrado"}), 404

@app.route('/api/ventas', methods=['POST'])
def registrar_venta():
    tienda_id, coleccion_productos, coleccion_ventas = obtener_colecciones_privadas()
    if not tienda_id: return jsonify({"error": "Falta el ID de la tienda"}), 400
    datos = request.json
    for articulo in datos['carrito']:
        coleccion_productos.update_one({"codigo": articulo['codigo'], "id_tienda": tienda_id}, {"$inc": {"stock": -float(articulo['cantidad'])}})
    nueva_venta = {
        "id_tienda": tienda_id, "fecha": datetime.now(), "articulos": datos['carrito'],
        "total": float(datos['total']), "pago_con": float(datos.get('pago_con', datos['total'])),
        "cambio": float(datos.get('cambio', 0))
    }
    coleccion_ventas.insert_one(nueva_venta)
    return jsonify({"mensaje": "¡Venta guardada en la nube y stock actualizado!"}), 201

@app.route('/api/ventas', methods=['GET'])
def historial_ventas():
    tienda_id, _, coleccion_ventas = obtener_colecciones_privadas()
    if not tienda_id: return jsonify({"error": "Falta el ID de la tienda"}), 400
    hoy_inicio = datetime.combine(datetime.now().date(), time.min)
    hoy_fin = datetime.combine(datetime.now().date(), time.max)
    ventas = list(coleccion_ventas.find({"id_tienda": tienda_id, "fecha": {"$gte": hoy_inicio, "$lte": hoy_fin}}).sort("fecha", -1))
    for venta in ventas:
        venta['_id'] = str(venta['_id']) 
        if isinstance(venta.get('fecha'), datetime): venta['fecha'] = venta['fecha'].isoformat()
    return jsonify(ventas), 200

@app.route('/api/ventas/devolver/<id_venta>', methods=['POST'])
def devolver_venta(id_venta):
    tienda_id, coleccion_productos, coleccion_ventas = obtener_colecciones_privadas()
    if not tienda_id: return jsonify({"error": "Falta el ID de la tienda"}), 400
    datos = request.json; tipo = datos.get('tipo') 
    try: venta = coleccion_ventas.find_one({"_id": ObjectId(id_venta), "id_tienda": tienda_id})
    except: return jsonify({"error": "ID de ticket no válido"}), 400
    if not venta: return jsonify({"error": "Ticket no encontrado en esta tienda"}), 404

    if tipo == 'simple':
        coleccion_ventas.delete_one({"_id": ObjectId(id_venta)})
        return jsonify({"mensaje": "🗑️ Ticket borrado simple."}), 200
    elif tipo == 'completa':
        for art in venta['articulos']:
            coleccion_productos.update_one({"codigo": art['codigo'], "id_tienda": tienda_id}, {"$inc": {"stock": float(art['cantidad'])}})
        coleccion_ventas.delete_one({"_id": ObjectId(id_venta)})
        return jsonify({"mensaje": "📦 Ticket eliminado. TODOS los productos regresaron al almacén."}), 200
    elif tipo == 'parcial':
        for p in datos.get('productos_a_devolver', []):
            if float(p['cantidad_devuelta']) > 0:
                coleccion_productos.update_one({"codigo": p['codigo'], "id_tienda": tienda_id}, {"$inc": {"stock": float(p['cantidad_devuelta'])}})
        if len(datos.get('articulos_restantes', [])) == 0:
            coleccion_ventas.delete_one({"_id": ObjectId(id_venta)})
            return jsonify({"mensaje": "Se devolvieron todos los artículos. Ticket borrado."}), 200
        else:
            coleccion_ventas.update_one({"_id": ObjectId(id_venta)}, {"$set": {"articulos": datos.get('articulos_restantes', []), "total": float(datos.get('nuevo_total', 0))}})
            return jsonify({"mensaje": "🔄 Devolución parcial aplicada."}), 200

@app.route('/api/ventas/reiniciar', methods=['DELETE'])
def borrar_todo_el_historial():
    tienda_id, _, coleccion_ventas = obtener_colecciones_privadas()
    if not tienda_id: return jsonify({"error": "Falta el ID de la tienda"}), 400
    coleccion_ventas.delete_many({"id_tienda": tienda_id}) 
    return jsonify({"mensaje": "El historial de esta tienda ha sido eliminado"}), 200

@app.route('/api/corte', methods=['GET'])
def corte_de_caja():
    tienda_id, _, coleccion_ventas = obtener_colecciones_privadas()
    if not tienda_id: return jsonify({"error": "Falta el ID de la tienda"}), 400
    hoy_inicio = datetime.combine(datetime.now().date(), time.min)
    hoy_fin = datetime.combine(datetime.now().date(), time.max)
    ventas_hoy = list(coleccion_ventas.find({"id_tienda": tienda_id, "fecha": {"$gte": hoy_inicio, "$lte": hoy_fin}}))
    total_dinero = sum(venta.get('total', 0) for venta in ventas_hoy)
    total_ganancia = 0
    for venta in ventas_hoy:
        for art in venta.get('articulos', []):
            total_ganancia += (float(art.get('precio', 0)) - float(art.get('precio_compra', 0))) * float(art.get('cantidad', 0))
    for venta in ventas_hoy:
        venta['_id'] = str(venta['_id'])
        if isinstance(venta.get('fecha'), datetime): venta['fecha'] = venta['fecha'].isoformat()
    return jsonify({ "fecha_reporte": datetime.now().strftime("%Y-%m-%d"), "hora_corte": datetime.now().strftime("%H:%M:%S"), "total_ventas": len(ventas_hoy), "total_dinero": total_dinero, "total_ganancia": total_ganancia, "detalles": ventas_hoy }), 200

if __name__ == '__main__':
    # Render asigna el puerto automáticamente, si no hay, usa el 5000
    puerto = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=puerto)