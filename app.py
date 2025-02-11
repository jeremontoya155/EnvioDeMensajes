from flask import Flask, render_template, request, redirect, url_for, session, flash
from instagrapi import Client
import schedule
import time
import threading
import openai
import os
import random
import json

app = Flask(__name__)
app.secret_key = os.getenv("API_KEY")  # Necesaria para manejar sesiones

# Configuración del proxy SOCKS5
# PROXY = "os.getenv("PROXY")"
PROXY=""
# Variables globales
cliente = None
usuarios = []
usuarios_enviados = set()  # Conjunto para almacenar IDs de usuarios a los que se les ha enviado mensajes
MENSAJES_POR_RONDA = 20  # Mensajes por ronda
DURACION_HORAS = 6
TIEMPO_ENTRE_MENSAJES = random.randint(200, 600)  # Entre 5 y 10 minutos entre mensajes
TIEMPO_ENTRE_RONDAS = 3600  # 1 hora entre rondas de mensajes

# Archivos de mensajes y base de conocimiento
MENSAJES_FILE = "mensajes.txt"
BASE_CONOCIMIENTO_FILE = "base_conocimiento.txt"
DATA_FILE = "data.json"
SESSION_FILE = "session.json"  # Archivo para guardar la sesión

# Configuración de OpenAI
openai.api_key = os.getenv("OPENAI_API_KEY")  # Clave desde .env

# Ruta principal: formulario para ingresar credenciales
@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        # Obtener credenciales
        session["username"] = request.form["username"]
        session["password"] = request.form["password"]

        # Manejar la carga de archivos
        if "mensajes_file" in request.files:
            mensajes_file = request.files["mensajes_file"]
            if mensajes_file.filename != "":
                try:
                    mensajes_file.save(MENSAJES_FILE)
                    flash("Archivo de mensajes cargado correctamente.", "success")
                except Exception as e:
                    flash(f"Error al cargar el archivo de mensajes: {e}", "danger")

        if "data_file" in request.files:
            data_file = request.files["data_file"]
            if data_file.filename != "":
                try:
                    data_file.save(DATA_FILE)
                    flash("Archivo de datos cargado correctamente.", "success")
                except Exception as e:
                    flash(f"Error al cargar el archivo de datos: {e}", "danger")

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
            return "Error al verificar el código de 2FA. Intenta nuevamente."

    return render_template("verificacion_2fa.html")

# Ruta para inicio de sesión exitoso
@app.route("/inicio_exitoso")
def inicio_exitoso():
    global cliente, usuarios

    if not cliente:
        return "Error: No hay sesión activa en Instagram."

    # Cargar usuarios desde data.json
    usuarios = cargar_usuarios_desde_json(DATA_FILE)

    if not usuarios:
        return "No se pudieron cargar los usuarios desde data.json."

    print(f"Se cargaron {len(usuarios)} usuarios desde data.json.")

    # Iniciar el programador de tareas en un hilo separado
    threading.Thread(target=programar_tareas, daemon=True).start()

    return "Inicio de sesión exitoso. El script está en ejecución y enviando mensajes."

# Función para cargar usuarios desde data.json
def cargar_usuarios_desde_json(data_file):
    try:
        with open(data_file, "r", encoding="utf-8") as f:
            usuarios = [json.loads(line) for line in f if line.strip()]
        return usuarios
    except Exception as e:
        print(f"⚠️ Error al cargar usuarios desde {data_file}: {e}")
        return []

# Función para iniciar sesión en Instagram
def iniciar_sesion(username, password, codigo_2fa=None):
    cl = Client()
    cl.set_proxy(PROXY)

    # Cargar la sesión si existe
    if os.path.exists(SESSION_FILE):
        try:
            cl.load_settings(SESSION_FILE)
            print("🔄 Sesión cargada desde session.json")
        except Exception as e:
            print(f"⚠️ Error al cargar la sesión: {e}")

    try:
        if codigo_2fa:
            cl.login(username, password, verification_code=codigo_2fa)
        else:
            cl.login(username, password)

        # Guardar la sesión después de un inicio de sesión exitoso
        cl.dump_settings(SESSION_FILE)
        print("✅ Sesión guardada en session.json")
        return cl
    except Exception as e:
        if "Two-factor authentication required" in str(e):
            return None  # Indicar que se requiere 2FA
        else:
            print(f"Error al iniciar sesión: {e}")
            return None

# Función para limpiar el mensaje
def limpiar_mensaje(mensaje):
    """
    Elimina los caracteres no deseados (como comillas dobles y simples) de un mensaje.
    """
    caracteres_no_deseados = ['"', "'"]
    for caracter in caracteres_no_deseados:
        mensaje = mensaje.replace(caracter, "")
    return mensaje.strip()  # Eliminar espacios adicionales al inicio y final

# Función para generar mensaje con OpenAI
def generar_mensaje_personalizado(nombre, descripcion):
    mensajes = cargar_mensajes()
    base_conocimiento = cargar_base_conocimiento()

    mensaje_aleatorio = random.choice(mensajes) if mensajes else "Hola, ¿cómo estás?"

    prompt = f"""
    Contexto:
    {base_conocimiento}

    Perfil de usuario:
    Nombre: {nombre}
    Descripción: {descripcion}

    Mensaje sugerido:
    '{mensaje_aleatorio}'

    Basado en la base de conocimiento y el mensaje sugerido, genera un mensaje personalizado y natural para esta persona.
    """

    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "Eres un asistente que genera mensajes personalizados para redes sociales. No puedes enviar ningún mensaje con comillas bajo absolutamente ningún contexto, y si un nombre parece apodo, no nos sirve; ignora el apodo y empieza con sujeto tácito."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=100
        )
        mensaje_generado = response["choices"][0]["message"]["content"].strip()
        return limpiar_mensaje(mensaje_generado)  # Limpiar el mensaje antes de devolverlo
    except Exception as e:
        print(f"⚠️ Error al generar mensaje: {e}")
        return limpiar_mensaje(mensaje_aleatorio)  # Limpiar el mensaje aleatorio antes de devolverlo

# Función para cargar mensajes desde archivo
def cargar_mensajes():
    try:
        with open(MENSAJES_FILE, "r", encoding="utf-8") as f:
            mensajes = [line.strip() for line in f if line.strip()]
        return mensajes
    except Exception as e:
        print(f"⚠️ Error al cargar mensajes: {e}")
        return []

# Función para cargar base de conocimiento
def cargar_base_conocimiento():
    try:
        with open(BASE_CONOCIMIENTO_FILE, "r", encoding="utf-8") as f:
            return f.read().strip()
    except Exception as e:
        print(f"⚠️ Error al cargar base de conocimiento: {e}")
        return ""

# Función para enviar mensajes
def enviar_mensajes():
    global cliente, usuarios, usuarios_enviados

    if not cliente or not usuarios:
        print("⚠️ No hay usuarios para enviar mensajes.")
        return

    mensajes_enviados = 0
    for usuario in usuarios[:MENSAJES_POR_RONDA]:  # Enviar solo a los primeros 10 usuarios
        if usuario["id"] in usuarios_enviados:
            print(f"⏭️ Mensaje ya enviado a {usuario['full_name']}. Saltando...")
            continue

        nombre = usuario["full_name"]
        descripcion = usuario["bio"]

        mensaje = generar_mensaje_personalizado(nombre, descripcion)

        try:
            cliente.direct_send(mensaje, user_ids=[usuario["id"]])
            print(f"✅ Mensaje enviado a {nombre}: {mensaje}")
            mensajes_enviados += 1
            usuarios_enviados.add(usuario["id"])  # Registrar el usuario como enviado
        except Exception as e:
            print(f"⚠️ Error al enviar mensaje a {nombre}: {e}")
            # Si hay un error, esperar un tiempo antes de reintentar
            time.sleep(300)  # Esperar 5 minutos antes de continuar

        # Esperar un tiempo aleatorio entre mensajes
        tiempo_espera = random.randint(200, 600)  # Entre 5 y 10 minutos
        print(f"⏳ Esperando {tiempo_espera // 60} minutos antes del próximo mensaje...")
        time.sleep(tiempo_espera)

    # Rotar la lista de usuarios para la próxima ronda
    usuarios = usuarios[MENSAJES_POR_RONDA:] + usuarios[:MENSAJES_POR_RONDA]
    print(f"🔄 Lista de usuarios rotada. Próxima ronda comenzará en {TIEMPO_ENTRE_RONDAS // 60} minutos.")

    # Esperar antes de la próxima ronda
    time.sleep(TIEMPO_ENTRE_RONDAS)

# Función para programar tareas
def programar_tareas():
    while True:
        enviar_mensajes()  # Ejecutar una ronda de mensajes

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)