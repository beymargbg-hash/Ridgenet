import os
import sqlite3
from flask import Flask, request, jsonify, render_template  # Agregamos render_template
import routeros_api

app = Flask(__name__)

# --- RUTA PARA EL VOLUMEN PERSISTENTE EN RENDER ---
# Esto asegura que la base de datos viva en el disco que no se borra
DB_PATH = '/app/data/elohim_system.db' if os.path.exists('/app/data') else 'elohim_system.db'

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
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

# --- RUTA PRINCIPAL (INDISPENSABLE PARA RENDER) ---
@app.route('/')
def home():
    # Esto mostrará tu index.html de la carpeta templates
    return render_template('index.html')

def get_mt_connection(host, user, password):
    try:
        connection = routeros_api.RouterOsApiPool(host, username=user, password=password, plaintext_login=True)
        return connection.get_api()
    except Exception as e:
        print(f"Error de conexión: {e}")
        return None

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

    conn = get_db_connection()
    cursor = conn.cursor()
    for c in clientes_encontrados:
        cursor.execute('INSERT OR IGNORE INTO abonados (nombre, ip_mikrotik) VALUES (?, ?)', 
                       (c['nombre'], c.get('user_mt')))
    conn.commit()
    conn.close()
    return jsonify({"status": "Sincronización completada", "total": len(clientes_encontrados)})

@app.route('/api/login_cliente', methods=['POST'])
def login_cliente():
    data = request.json
    dni = data.get('dni')
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM abonados WHERE dni = ?', (dni,))
    user = cursor.fetchone()
    conn.close()
    if user:
        return jsonify({"status": "success", "user": {"nombre": user['nombre'], "estado": user['estado']}})
    return jsonify({"status": "error", "message": "DNI no registrado"}), 404

@app.route('/api/control', methods=['POST'])
def control_servicio():
    return jsonify({"status": "Comando enviado"})

# --- INICIO DEL SERVIDOR (AJUSTADO PARA RENDER) ---
if __name__ == '__main__':
    init_db()
    # Capturamos el puerto de Render o usamos 5000 por defecto localmente
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
    
