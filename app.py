import os
import sqlite3
from flask import Flask, request, jsonify, render_template
import routeros_api

app = Flask(__name__)

# --- CONFIGURACIÓN DE RUTA PERSISTENTE ---
# En Render, /app/data es el disco que no se borra.
DB_PATH = '/app/data/elohim_system.db' if os.path.exists('/app/data') else 'elohim_system.db'

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    # Tabla para los abonados
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS abonados (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT,
            dni TEXT UNIQUE,
            ip_mikrotik TEXT,
            perfil_mikrotik TEXT,
            estado TEXT DEFAULT 'Activo'
        )
    ''')
    # Tabla para la Configuración del Admin (API KEYS)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS config_admin (
            id INTEGER PRIMARY KEY,
            host TEXT,
            user TEXT,
            password TEXT
        )
    ''')
    conn.commit()
    conn.close()

@app.route('/')
def home():
    return render_template('index.html')

# --- RUTA PARA GUARDAR LAS API KEYS DEL ADMIN ---
@app.route('/api/config_admin', methods=['POST'])
def guardar_config():
    data = request.json
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT OR REPLACE INTO config_admin (id, host, user, password) 
        VALUES (1, ?, ?, ?)
    ''', (data['host'], data['user'], data['pass']))
    conn.commit()
    conn.close()
    return jsonify({"status": "success", "message": "Configuración guardada"})

# --- RUTA PARA LISTAR CLIENTES EN EL PANEL ADMIN ---
@app.route('/api/clientes', methods=['GET'])
def listar_clientes():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM abonados')
    clientes = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return jsonify(clientes)

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
        return jsonify({"status": "success", "user": dict(user)})
    return jsonify({"status": "error", "message": "No registrado"}), 404

if __name__ == '__main__':
    init_db()
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
    
