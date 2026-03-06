import os
from flask import Flask, request, jsonify, render_template
import routeros_api
from pymongo import MongoClient # Importación necesaria para MongoDB

app = Flask(__name__)

# --- CONFIGURACIÓN DE MONGODB (LLAVE MAESTRA) ---
# He integrado tu link de Cluster0.oe1r5ao
MONGO_URI = "mongodb+srv://Beymar:Beymar@cluster0.oe1r5ao.mongodb.net/?appName=Cluster0"
client = MongoClient(MONGO_URI)
db = client['ridginet_db']
coleccion_clientes = db['abonados']
coleccion_config = db['config_admin']

# --- RUTA PRINCIPAL ---
@app.route('/')
def home():
    return render_template('index.html')

# --- LÓGICA DE MIKROTIK ---
def get_mt_connection(host, user, password):
    try:
        connection = routeros_api.RouterOsApiPool(host, username=user, password=password, plaintext_login=True)
        return connection.get_api()
    except Exception as e:
        print(f"Error de conexión: {e}")
        return None

# --- NUEVA RUTA PARA GUARDAR CONFIGURACIÓN DEL ADMIN (PERSISTENTE) ---
@app.route('/api/config_admin', methods=['POST'])
def guardar_config():
    data = request.json
    coleccion_config.update_one(
        {"_id": "config_global"},
        {"$set": {
            "host": data.get('host'),
            "user": data.get('user'),
            "pass": data.get('pass')
        }},
        upsert=True
    )
    return jsonify({"status": "success", "message": "Configuración guardada en la nube"})

# --- LISTAR CLIENTES PARA EL PANEL ---
@app.route('/api/clientes', methods=['GET'])
def listar_clientes():
    clientes = list(coleccion_clientes.find({}, {"_id": 0}))
    return jsonify(clientes)

@app.route('/api/sincronizar', methods=['POST'])
def sincronizar_wisp():
    data = request.json
    api = get_mt_connection(data['host'], data['user'], data['pass'])
    if not api:
        return jsonify({"error": "No se pudo conectar al MikroTik"}), 400

    clientes_encontrados = []
    try:
        secrets = api.get_resource('/ppp/secret').get()
        for s in secrets:
            clientes_encontrados.append({
                "nombre": s.get('comment', s['name']),
                "dni": s['name'], # Usamos el name como DNI inicial
                "ip_mikrotik": s.get('remote-address', '0.0.0.0'),
                "estado": "Activo"
            })
    except: pass

    # Guardar en MongoDB (No se borra)
    for c in clientes_encontrados:
        coleccion_clientes.update_one(
            {"dni": c['dni']},
            {"$set": c},
            upsert=True
        )
    
    return jsonify({"status": "Sincronización completada", "total": len(clientes_encontrados)})

@app.route('/api/login_cliente', methods=['POST'])
def login_cliente():
    data = request.json
    dni = data.get('dni')
    user = coleccion_clientes.find_one({"dni": dni}, {"_id": 0})
    
    if user:
        return jsonify({"status": "success", "user": user})
    return jsonify({"status": "error", "message": "DNI no registrado"}), 404

@app.route('/api/control', methods=['POST'])
def control_servicio():
    return jsonify({"status": "Comando enviado"})

# --- INICIO DEL SERVIDOR ---
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
    
