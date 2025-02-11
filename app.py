from flask import Flask, render_template, request, redirect, url_for, session, flash
from instagrapi import Client
import time
import threading
import openai
import os
import random
import json

app = Flask(__name__)
app.secret_key = os.getenv("API_KEY")  # Clave para sesiones

# Configuración de proxy (Si tienes uno, agrégalo aquí)
PROXY = ""

# Variables globales
cliente = None
usuarios = []
mensajes = []
usuarios_enviados = set()
MENSAJES_POR_RONDA = 10  # Reducido para evitar bloqueos
TIEMPO_ENTRE_MENSAJES = random.randint(300, 600)  # 5 a 10 minutos entre mensajes
TIEMPO_ENTRE_RONDAS = 3600  # 1 hora entre rondas
SESSION_FILE = "session.json"  # Guardado de sesión
MENSAJES_FILE = "mensajes.txt"
DATA_FILE = "data.json"
BASE_CONOCIMIENTO_FILE = "base_conocimiento.txt"

# Configuración de OpenAI
openai.api_key = os.getenv("OPENAI_API_KEY")

# Ruta principal: formulario para ingresar credenciales
@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        session["username"] = request.form["username"]
        session["password"] = request.form["password"]

        # Guardar archivos cargados
        if "mensajes_file" in request.files:
            mensajes_file = request.files["mensajes_file"]
            if mensajes_file.filename:
                mensajes_file.save(MENSAJES_FILE)
                flash("Archivo de mensajes cargado correctamente.", "success")

        if "data_file" in request.files:
            data_file = request.files["data_file"]
            if data_file.filename:
                data_file.save(DATA_FILE)
                flash("Archivo de datos cargado correctamente.", "success")

        # Iniciar sesión en Instagram
        global cliente
        cliente = iniciar_sesion(session["username"], session["password"])

        if cliente:
            return redirect(url_for("inicio_exitoso"))
        else:
            return redirect(url_for("verificacion_2fa"))

    return render_template("index.html")

# Ruta para verificación de 2FA
@app.route("/verificacion_2fa", methods=["GET", "POST"])
def verificacion_2fa():
    if request.method == "POST":
        codigo_2fa = request.form["codigo_2fa"]
        global cliente
        cliente = iniciar_sesion(session["username"], session["password"], codigo_2fa)

        if cliente:
            return redirect(url_for("inicio_exitoso"))
        else:
            return "Error al verificar el código de 2FA."

    return render_template("verificacion_2fa.html")

# Ruta para inicio de sesión exitoso
@app.route("/inicio_exitoso")
def inicio_exitoso():
    global cliente, usuarios, mensajes

    if not cliente:
        return "Error: No hay sesión activa en Instagram."

    # Cargar usuarios y mensajes
    usuarios = cargar_usuarios()
    mensajes = cargar_mensajes()

    if not usuarios or not mensajes:
        return "No se pudieron cargar los usuarios o mensajes."

    print(f"✅ Se cargaron {len(usuarios)} usuarios y {len(mensajes)} mensajes.")

    # Iniciar el programador de tareas en un hilo separado
    threading.Thread(target=programar_tareas, daemon=True).start()

    return "Inicio de sesión exitoso. El script está enviando mensajes."

# Función para iniciar sesión en Instagram
def iniciar_sesion(username, password, codigo_2fa=None):
    cl = Client()

    if PROXY:
        cl.set_proxy(PROXY)  

    # Intentar cargar sesión guardada
    if os.path.exists(SESSION_FILE):
        try:
            cl.load_settings(SESSION_FILE)
            print("🔄 Sesión cargada desde session.json")
            cl.relogin()
            return cl
        except Exception as e:
            print(f"⚠️ Error al cargar sesión: {e}")

    try:
        if codigo_2fa:
            cl.login(username, password, verification_code=codigo_2fa)
        else:
            cl.login(username, password)

        cl.dump_settings(SESSION_FILE)
        print("✅ Sesión guardada en session.json")
        return cl
    except Exception as e:
        print(f"⚠️ Error al iniciar sesión: {e}")
        return None

# Función para cargar usuarios dinámicamente desde `data.json`
def cargar_usuarios():
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return [json.loads(line) for line in f if line.strip()]
    except Exception as e:
        print(f"⚠️ Error al cargar usuarios: {e}")
        return []

# Función para cargar mensajes dinámicamente desde `mensajes.txt`
def cargar_mensajes():
    try:
        with open(MENSAJES_FILE, "r", encoding="utf-8") as f:
            return [line.strip() for line in f if line.strip()]
    except Exception as e:
        print(f"⚠️ Error al cargar mensajes: {e}")
        return ["Hola, ¿cómo estás?"]

# Función para generar mensaje personalizado con OpenAI
def generar_mensaje(nombre):
    mensaje_base = random.choice(mensajes)

    prompt = f"Genera un mensaje para {nombre}: {mensaje_base}"
    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            max_tokens=100
        )
        return response["choices"][0]["message"]["content"].strip()
    except:
        return mensaje_base

# Función para enviar mensajes
def enviar_mensajes():
    global cliente, usuarios, usuarios_enviados

    if not cliente or not usuarios:
        print("⚠️ No hay usuarios disponibles.")
        return

    for usuario in usuarios[:MENSAJES_POR_RONDA]:
        if usuario["id"] in usuarios_enviados:
            print(f"⏭️ Ya se envió mensaje a {usuario['full_name']}. Saltando...")
            continue

        nombre = usuario["full_name"]
        mensaje = generar_mensaje(nombre)

        try:
            cliente.direct_send(mensaje, [usuario["id"]])
            print(f"✅ Mensaje enviado a {nombre}: {mensaje}")
            usuarios_enviados.add(usuario["id"])
        except Exception as e:
            print(f"⚠️ Error al enviar mensaje a {nombre}: {e}")
            time.sleep(300)

        tiempo_espera = random.randint(300, 600)  
        print(f"⏳ Esperando {tiempo_espera // 60} minutos...")
        time.sleep(tiempo_espera)

    usuarios = usuarios[MENSAJES_POR_RONDA:] + usuarios[:MENSAJES_POR_RONDA]
    time.sleep(TIEMPO_ENTRE_RONDAS)

# Función para programar el envío de mensajes
def programar_tareas():
    while True:
        enviar_mensajes()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
