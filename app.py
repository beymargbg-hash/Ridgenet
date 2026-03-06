import os
import sqlite3
from flask import Flask, request, jsonify, render_template
import routeros_api

app = Flask(__name__)

# --- CONFIGURACIÓN DE BASE DE DATOS LOCAL ---
def init_db():
    # Creamos la base de datos si no existe
    conn = sqlite3.connect('elohim_system.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS abonados (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT,
            dni TEXT UNIQUE,
            ip_mikrotik TEXT,
            perfil_mikrotik TEXT,
            estado TEXT DEFAULT 'Activo',
            ultimo_pago TEXT,
            metodo_pago TEXT
        )
    ''')
    conn.commit()
    conn.close()

# --- CONEXIÓN DINÁMICA AL MIKROTIK ---
def get_mt_connection(host, user, password):
    try:
        connection = routeros_api.RouterOsApiPool(host, username=user, password=password, plaintext_login=True)
        return connection.get_api()
    except Exception as e:
        return None

# --- RUTA PRINCIPAL (Para ver tu HTML v2.0) ---
@app.route('/')
def home():
    return render_template('index.html')

# --- LÓGICA DE SINCRONIZACIÓN (Tu código original) ---
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
                "user_mt": s['name']
            })
    except: pass

    conn = sqlite3.connect('elohim_system.db')
    cursor = conn.cursor()
    for c in clientes_encontrados:
        cursor.execute('INSERT OR IGNORE INTO abonados (nombre, ip_mikrotik) VALUES (?, ?)', 
                       (c['nombre'], c.get('user_mt')))
    conn.commit()
    conn.close()
    return jsonify({"status": "Sincronización completada", "total": len(clientes_encontrados)})

# --- LÓGICA DE LOGIN PARA CLIENTES (Tu código original) ---
@app.route('/api/login_cliente', methods=['POST'])
def login_cliente():
    data = request.json
    dni = data.get('dni')
    conn = sqlite3.connect('elohim_system.db')
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM abonados WHERE dni = ?', (dni,))
    user = cursor.fetchone()
    conn.close()
    if user:
        return jsonify({"status": "success", "user": {"nombre": user[1], "estado": user[5]}})
    return jsonify({"status": "error", "message": "DNI no registrado"}), 404

# --- INICIO DEL SERVIDOR (Optimizado para Railway) ---
if __name__ == '__main__':
    init_db()
    # ESTO ES LO QUE HACE QUE NO FALLE:
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
    
