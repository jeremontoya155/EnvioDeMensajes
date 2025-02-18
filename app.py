from flask import Flask, render_template, request, redirect, url_for, session, flash
from instagrapi import Client
import schedule
import time
import threading
import openai
import os
import random
import json
import redis  # Importar Redis
from pymongo import MongoClient  # Importar MongoDB
import requests 
import datetime


app = Flask(__name__)
app.secret_key = os.getenv("API_KEY")  # Necesaria para manejar sesiones

# Configuración de Redis
REDIS_URL = os.getenv("REDIS")
redis_client = redis.from_url(REDIS_URL)  # Conexión a Redis
api_key = os.getenv("API_KEY")  # Clave de la API de Instagram

# Configuración de MongoDB
MONGO_URL = os.getenv("MONGO")  # Reemplaza con tu URL de MongoDB
mongo_client = MongoClient(MONGO_URL)
db = mongo_client["instagram_bot"]  # Nombre de la base de datos
historial_collection = db["historial_acciones"]  # Colección para el historial
historial_mensajes = db["historial_mensajes_dm"]

# Configuración del proxy SOCKS5
# PROXY = " "  # Proxy SOCKS5 para instagrapi

# Variables globales
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
# defino una variable global para almacenar los chats activos
active_chats = {}


# Configuración de OpenAI
openai.api_key = os.getenv("OPENAI_API_KEY")  # Clave desde .env

# Ruta principal: formulario para ingresar credenciales
@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        # Obtener credenciales
        username = request.form["username"]
        password = request.form["password"]

        # Guardar credenciales en la sesión de Flask
        session["username"] = username
        session["password"] = password

        # Manejar la carga de archivos y mensajes directos
        mensajes_directos = request.form.get("mensajes_directos", "").strip()

        if mensajes_directos:
            # Si el usuario escribió mensajes directamente, guardarlos en mensajes.txt
            try:
                with open(MENSAJES_FILE, "w", encoding="utf-8") as f:
                    f.write(mensajes_directos)
                flash("Mensajes guardados correctamente.", "success")
            except Exception as e:
                flash(f"Error al guardar los mensajes: {e}", "danger")
        else:
            # Si no escribió mensajes, usar el archivo mensajes.txt que suba
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
        cliente = iniciar_sesion(username, password)

        if cliente:
            return redirect(url_for("resumen"))  # Redirigir a /resumen
        else:
            return redirect(url_for("verificacion_2fa"))

    return render_template("index.html")
@app.route("/resumen")
def resumen():
    if "username" not in session:
        return redirect(url_for("index"))  # Redirigir si el usuario no ha iniciado sesión

    username = session.get("username")

    # Obtener el historial de acciones desde MongoDB
    acciones = list(historial_collection.find({"username": username}).sort("fecha", -1))  # Ordenar por fecha descendente

    # Calcular métricas
    total_mensajes_enviados = len(acciones)
    ultimos_mensajes = acciones[:10]  # Últimos 10 mensajes enviados

    return render_template("resumen.html", 
                           username=username, 
                           total_mensajes_enviados=total_mensajes_enviados, 
                           ultimos_mensajes=ultimos_mensajes)

# Ruta para verificación de 2FA
@app.route("/verificacion_2fa", methods=["GET", "POST"])
def verificacion_2fa():
    if request.method == "POST":
        codigo_2fa = request.form["codigo_2fa"]
        username = session.get("username")
        password = session.get("password")

        cliente = iniciar_sesion(username, password, codigo_2fa)

        if cliente:
            return redirect(url_for("inicio_exitoso"))
        else:
            return "Error al verificar el código de 2FA. Intenta nuevamente."

    return render_template("verificacion_2fa.html")

# Ruta para inicio de sesión exitoso
@app.route("/inicio_exitoso")
def inicio_exitoso():
    username = session.get("username")

    # Cargar usuarios desde data.json
    global usuarios
    usuarios = cargar_usuarios_desde_json(DATA_FILE)

    if not usuarios:
        return "No se pudieron cargar los usuarios desde data.json."

    print(f"Se cargaron {len(usuarios)} usuarios desde data.json.")

    # Iniciar el programador de tareas en un hilo separado
    threading.Thread(target=programar_tareas, args=(username,), daemon=True).start()

    return redirect(url_for("resumen"))

#Ruta para mostrar estadisticas
@app.route("/resumen", methods=["GET"])
def estadisticas():
    # Obtener todos los mensajes enviados desde MongoDB
    mensajes = list(historial_mensajes.find())

    # Calcular estadísticas
    total_mensajes = len(mensajes)
    mensajes_por_usuario = {}
    mensajes_con_respuestas = 0  # Para contar los mensajes con respuestas
    total_likes = 0  # Total de likes acumulados
    mensajes_vistos = 0  # Para contar los mensajes vistos

    for mensaje in mensajes:
        destinatario = mensaje.get("destinatario")
        if destinatario not in mensajes_por_usuario:
            mensajes_por_usuario[destinatario] = 0
        mensajes_por_usuario[destinatario] += 1

        # Contar los mensajes que tienen respuestas
        if mensaje.get("respuesta"):
            mensajes_con_respuestas += 1
        
        # Acumular los likes
        total_likes += mensaje.get("likes", 0)

        # Contar los mensajes vistos
        if mensaje.get("visto"):
            mensajes_vistos += 1

    # Estadísticas de mensajes por fecha
    mensajes_por_fecha = {}
    for mensaje in mensajes:
        fecha = mensaje.get("fecha")
        fecha = datetime.strptime(fecha, "%Y-%m-%d %H:%M:%S").date()
        if fecha not in mensajes_por_fecha:
            mensajes_por_fecha[fecha] = 0
        mensajes_por_fecha[fecha] += 1

    # Renderizar plantilla HTML con las estadísticas
    return render_template("resumen.html", 
                           total_mensajes=total_mensajes, 
                           mensajes_por_usuario=mensajes_por_usuario, 
                           mensajes_por_fecha=mensajes_por_fecha,
                           mensajes_con_respuestas=mensajes_con_respuestas,
                           total_likes=total_likes,
                           mensajes_vistos=mensajes_vistos)



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
    # cl.set_proxy(PROXY)  # Configurar el proxy

    # Clave única para la sesión en Redis
    session_key = f"instagram_session:{username}"

    # Cargar la sesión desde Redis si existe
    session_data = redis_client.get(session_key)
    if (session_data):
        try:
            # Convertir los datos de Redis (bytes) a un diccionario
            session_dict = json.loads(session_data.decode("utf-8"))
            # Guardar la sesión en un archivo temporal
            with open("temp_session.json", "w") as f:
                json.dump(session_dict, f)
            # Cargar la sesión desde el archivo temporal
            cl.load_settings("temp_session.json")
            print(f"🔄 Sesión cargada desde Redis para el usuario {username}")
        except Exception as e:
            print(f"⚠️ Error al cargar la sesión desde Redis: {e}")

    try:
        if codigo_2fa:
            cl.login(username, password, verification_code=codigo_2fa)
        else:
            cl.login(username, password)

        # Guardar la sesión en Redis después de un inicio de sesión exitoso
        session_data = cl.get_settings()  # Esto devuelve un diccionario
        session_data_str = json.dumps(session_data)  # Convertir a JSON
        redis_client.set(session_key, session_data_str)
        print(f"✅ Sesión guardada en Redis para el usuario {username}")
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
def track_and_monitor_message(username, user_id, message_id, delay=120):
    api_url = f"https://graph.facebook.com/v17.0/{message_id}"
    params = {"access_token": api_key}

    try:
        # Espera antes de realizar la consulta (evitar monitorear de forma constante)
        print(f"⏳ Esperando {delay} segundos antes de monitorear el mensaje...")
        time.sleep(delay)

        response = requests.get(api_url, params=params)
        if response.status_code == 200:
            dm_data = response.json()

            # Extraer los datos relevantes del mensaje
            estado = dm_data.get("status", "Desconocido")  # Estado del mensaje (ej. entregado, leído, etc.)
            likes_count = dm_data.get("likes_count", 0)  # Número de "likes"
            respuesta = dm_data.get("text", "")  # Respuesta al mensaje (si existe)
            visto = dm_data.get("is_seen", False)  # Si el mensaje fue visto o no

            # Obtener la fecha de la respuesta (si aplica) o la fecha de la última actualización
            fecha = time.strftime("%Y-%m-%d %H:%M:%S")

            # Estructura para guardar o actualizar la información en MongoDB
            mensaje_guardado = {
                "username": username,
                "message_id": message_id,
                "user_id": user_id,
                "estado": estado,
                "likes_count": likes_count,
                "respuesta": respuesta,
                "visto": visto,
                "fecha": fecha,
                "fecha_respuesta": fecha  # Si no se tiene una fecha de respuesta específica, usar la fecha actual
            }

            # Actualizar el estado y la interacción en MongoDB
            historial_mensajes.update_one(
                {"message_id": message_id},  # Identificar el mensaje original
                {"$set": mensaje_guardado},
                upsert=True  # Si no existe, lo inserta; si ya existe, lo actualiza
            )

            print(f"✅ Mensaje {message_id} con estado, likes, respuesta y visto actualizado para el usuario {user_id} en MongoDB.")
        else:
            print(f"⚠️ Error al obtener el estado del mensaje {message_id}: {response.status_code}")

    except Exception as e:
        print(f"⚠️ Error al conectar con la API para trackear y monitorear el mensaje {message_id}: {e}")


# Función para enviar los mensajes y realizar el seguimiento
def enviar_mensajes(username):
    global usuarios, usuarios_enviados

    if not usuarios:
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
            # Obtener el cliente de Instagram desde Redis
            session_key = f"instagram_session:{username}"
            session_data = redis_client.get(session_key)
            if session_data:
                cl = Client()
                session_dict = json.loads(session_data.decode("utf-8"))
                
                # Guardar la sesión en un archivo temporal
                with open("temp_session.json", "w") as f:
                    json.dump(session_dict, f)
                
                # Cargar la sesión desde el archivo temporal
                cl.load_settings("temp_session.json")

                # Enviar mensaje y obtener response con message_id
                response = cl.direct_send(mensaje, user_ids=[usuario["id"]])
                
                if response and "message_id" in response:
                    message_id = response["message_id"]
                else:
                    message_id = None  # En caso de que no se devuelva el ID

                print(f"✅ Mensaje enviado a {nombre}: {mensaje} (ID: {message_id})")
                mensajes_enviados += 1
                usuarios_enviados.add(usuario["id"])  # Registrar el usuario como enviado

                # Registrar la acción en MongoDB (historial de mensajes)
                accion = {
                    "username": username,
                    "accion": "mensaje_enviado",
                    "destinatario": nombre,
                    "mensaje": mensaje,
                    "message_id": message_id,
                    "fecha": time.strftime("%Y-%m-%d %H:%M:%S")
                }
                historial_mensajes.insert_one(accion)

                # Si se obtuvo el ID del mensaje, agregarlo al diccionario correspondiente
                if message_id:
                    if usuario["id"] not in active_chats:
                        active_chats[usuario["id"]] = []
                    active_chats[usuario["id"]].append(message_id)  # Agregar el ID a la lista del usuario

                    # Iniciar el monitoreo en un hilo separado
                    threading.Thread(target=track_and_monitor_message, args=(username, usuario["id"], message_id), daemon=True).start()

        except Exception as e:
            print(f"⚠️ Error al enviar mensaje a {nombre}: {e}")
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

# Iniciar el monitoreo en segundo plano
# monitor_thread = threading.Thread(target=track_and_monitor_message, daemon=True)
# monitor_thread.start()

# Función para programar tareas
def programar_tareas(username):
    while True:
        enviar_mensajes(username)  # Ejecutar una ronda de mensajes
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)