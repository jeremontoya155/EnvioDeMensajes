from instagrapi import Client
import schedule
import time
import os
from dotenv import load_dotenv
import random
import openai

# Cargar variables de entorno desde un archivo .env
load_dotenv()

# Configuración de credenciales
INSTAGRAM_USERNAME = os.getenv("INSTAGRAM_USERNAME")  # Tu nombre de usuario de Instagram
INSTAGRAM_PASSWORD = os.getenv("INSTAGRAM_PASSWORD")  # Tu contraseña de Instagram
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")          # Tu clave de API de OpenAI

# Configuración del proxy SOCKS5
PROXY = "64.137.42.112:5157:amexwlwa:22d6c11ojca0"

# Lista de cuentas de competencia
COMPETENCIAS = ["jere.montoya", "sebasilva33"]  # Cuentas de competencia

# Configuración de envío
MENSAJES_POR_HORA = 10  # Mensajes a enviar por hora
TOTAL_MENSAJES = 40     # Total de mensajes a enviar
DURACION_HORAS = 6      # Duración total en horas

# Iniciar sesión en Instagram con proxy
def iniciar_sesion():
    cl = Client()
    cl.set_proxy(PROXY)  # Configurar el proxy SOCKS5
    try:
        cl.login(INSTAGRAM_USERNAME, INSTAGRAM_PASSWORD)
        print(f"Inicio de sesión exitoso usando proxy: {PROXY}")
        return cl
    except Exception as e:
        print(f"Error al iniciar sesión: {e}")
        return None

# Obtener seguidores de una cuenta
def obtener_seguidores(cl, username):
    try:
        user_id = cl.user_id_from_username(username)
        seguidores = cl.user_followers(user_id, amount=100)  # Obtener hasta 100 seguidores
        return list(seguidores.keys())
    except Exception as e:
        print(f"Error al obtener seguidores de {username}: {e}")
        return []

# Obtener la descripción del perfil de un usuario
def obtener_descripcion_perfil(cl, user_id):
    try:
        user_info = cl.user_info(user_id)
        return user_info.biography
    except Exception as e:
        print(f"Error al obtener la descripción del perfil de {user_id}: {e}")
        return ""

# Generar un mensaje personalizado con OpenAI
def generar_mensaje_personalizado(descripcion):
    openai.api_key = OPENAI_API_KEY

    prompt = f"La descripción del perfil de Instagram es: '{descripcion}'. Genera un mensaje personalizado para enviarle a esta persona."
    try:
        response = openai.Completion.create(
            engine="text-davinci-003",  # Usa el modelo más reciente
            prompt=prompt,
            max_tokens=100,  # Limita la longitud del mensaje
            n=1,             # Generar una sola respuesta
            stop=None,       # No detener la generación hasta que se complete
        )
        return response.choices[0].text.strip()
    except Exception as e:
        print(f"Error al generar mensaje con OpenAI: {e}")
        return "Hola, ¿cómo estás?"

# Enviar mensajes a seguidores
def enviar_mensajes(cl, seguidores):
    if not cl:
        print("No se pudo iniciar sesión. Verifica tus credenciales.")
        return

    mensajes_enviados = 0
    for user_id in seguidores:
        if mensajes_enviados >= MENSAJES_POR_HORA:
            break  # Detener si ya se enviaron los mensajes de esta hora

        # Obtener la descripción del perfil del seguidor
        descripcion = obtener_descripcion_perfil(cl, user_id)

        # Generar un mensaje personalizado con OpenAI
        mensaje = generar_mensaje_personalizado(descripcion)

        try:
            cl.direct_send(mensaje, user_ids=[user_id])
            print(f"Mensaje enviado a {user_id}: {mensaje}")
            mensajes_enviados += 1
        except Exception as e:
            print(f"Error al enviar mensaje a {user_id}: {e}")

# Programar tareas
def programar_tareas(cl, seguidores):
    for hora in range(DURACION_HORAS):
        schedule.every(hora).hours.do(enviar_mensajes, cl, seguidores)
        print(f"Tarea programada para la hora {hora}.")

# Ejecutar el script
if __name__ == "__main__":
    # Iniciar sesión
    cliente = iniciar_sesion()

    if cliente:
        # Obtener seguidores de las cuentas de competencia
        seguidores = []
        for competencia in COMPETENCIAS:
            seguidores += obtener_seguidores(cliente, competencia)

        if not seguidores:
            print("No se pudieron obtener seguidores. Verifica las cuentas de competencia.")
        else:
            print(f"Se obtuvieron {len(seguidores)} seguidores.")

            # Programar tareas
            programar_tareas(cliente, seguidores)

            # Mantener el script en ejecución
            print("El script está en ejecución. Presiona Ctrl+C para detenerlo.")
            while True:
                schedule.run_pending()
                time.sleep(1)