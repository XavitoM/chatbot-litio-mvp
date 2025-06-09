from fastapi import FastAPI
from pydantic import BaseModel
from openai import OpenAI
import smtplib
from email.mime.text import MIMEText
from fastapi.middleware.cors import CORSMiddleware
import os
from fastapi.responses import HTMLResponse
import csv
from datetime import datetime
import re

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class Message(BaseModel):
    content: str

pacientes_en_sesion = {}  # rut -> nombre
nombre_pendiente = ""
rut_pendiente = ""
rut_en_conversacion = ""
esperando_respuesta_litio = False
@app.post("/mensaje")
async def recibir_mensaje(message: Message):
    global nombre_pendiente, rut_pendiente, rut_en_conversacion, esperando_respuesta_litio
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    texto = message.content
    prefijo = ""

    nombre = extraer_nombre(texto)
    rut = normalizar_rut(extraer_rut(texto))
    fecha = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    print("DEBUG | Nombre extraído:", nombre, "| RUT normalizado:", rut)

    if esperando_respuesta_litio and rut_en_conversacion:
        esperando_respuesta_litio = False
        if "no" in texto.lower():
            return {"respuesta": "Entiendo, si en algún momento comienzas un tratamiento con litio avísame para acompañarte."}
        return {"respuesta": "Perfecto, seguimos atentos a tus síntomas y dudas."}

    if rut in pacientes_en_sesion:
        nombre = pacientes_en_sesion[rut]
        rut_en_conversacion = rut
    elif nombre and rut:
        pacientes_en_sesion[rut] = nombre
        rut_en_conversacion = rut
        nombre_pendiente = ""
        rut_pendiente = ""
        esperando_respuesta_litio = True
        return {"respuesta": f"Gracias {nombre.split()[0]}, ¿estás tomando litio actualmente?"}
    elif nombre and not rut:
        nombre_pendiente = nombre
        if rut_pendiente:
            pacientes_en_sesion[rut_pendiente] = nombre
            rut_en_conversacion = rut_pendiente
            rut = rut_pendiente
            nombre_pendiente = ""
            rut_pendiente = ""
            esperando_respuesta_litio = True
            return {"respuesta": f"Gracias {nombre.split()[0]}, ¿estás tomando litio actualmente?"}
        else:
            registrar_rut_fallido(texto, nombre, rut)
            return {"respuesta": f"Gracias {nombre.split()[0]}, ¿podrías indicarme tu RUT?"}
    elif rut and not nombre:
        rut_pendiente = rut
        if nombre_pendiente:
            pacientes_en_sesion[rut] = nombre_pendiente
            rut_en_conversacion = rut
            nombre = nombre_pendiente
            nombre_pendiente = ""
            rut_pendiente = ""
            esperando_respuesta_litio = True
            return {"respuesta": f"Gracias {nombre.split()[0]}, ¿estás tomando litio actualmente?"}
        else:
            registrar_rut_fallido(texto, nombre, rut)
            return {"respuesta": "Gracias. ¿Cuál es tu nombre completo?"}
    else:
        prefijo = ""
        if rut_en_conversacion:
            nombre = pacientes_en_sesion.get(rut_en_conversacion, "")
        else:
            registrar_rut_fallido(texto, nombre, rut)
            prefijo = (
                "Hola, soy tu asistente médico. Aún no logro registrar tu nombre o RUT. "
                "Cuéntame, ¿cómo te sientes hoy? "
            )

    if requiere_aclaracion(texto):
        return {"respuesta": "¿Podrías explicarme un poco más a qué te refieres con eso? Quiero entender bien para poder ayudarte mejor."}

    resumen = sintetizar_resumen(texto)
    if resumen == "sin hallazgos relevantes":
        resumen = sintetizar_con_ia(texto, client)

    respuesta = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": "Eres un asistente médico experto en seguimiento de pacientes que toman litio. Respondes con empatía y de forma concisa. Evalúas criterios de gravedad de manera no sugestiva y preguntas al menos una vez por semana por síntomas suicidas."},
            {"role": "user", "content": texto}
        ]
    )

    contenido_respuesta = respuesta.choices[0].message.content

    if prefijo:
        contenido_respuesta = prefijo + contenido_respuesta

    if "urgencias" in contenido_respuesta.lower() or any(p in resumen for p in ["síntomas neurológicos", "ideas suicidas"]):
        enviar_correo_alerta(texto, contenido_respuesta)

    registrar_interaccion(nombre, rut, texto, contenido_respuesta, resumen)
    return {"respuesta": contenido_respuesta}

def enviar_correo_alerta(mensaje_original, respuesta):
    remitente = os.getenv("EMAIL_USER")
    destinatario = "uhciphospitalangol@gmail.com"
    password = os.getenv("EMAIL_PASS")

    mensaje = MIMEText(f"Mensaje del paciente:\n{mensaje_original}\n\nRespuesta de ChatGPT:\n{respuesta}")
    mensaje['Subject'] = "ALERTA - Prioridad Alta"
    mensaje['From'] = remitente
    mensaje['To'] = destinatario

    with smtplib.SMTP("smtp.gmail.com", 587) as servidor:
        servidor.starttls()
        servidor.login(remitente, password)
        servidor.send_message(mensaje)

def registrar_interaccion(nombre, rut, mensaje, respuesta, resumen):
    os.makedirs("conversaciones", exist_ok=True)
    fecha = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    with open("registro_resumen.csv", "a", newline='', encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([fecha, nombre, rut, resumen])

    archivo = f"conversaciones/{rut.replace('-', '').lower()}.txt"
    with open(archivo, "a", encoding="utf-8") as f:
        f.write(f"[{fecha}] Usuario: {mensaje}\n")
        f.write(f"[{fecha}] Bot: {respuesta}\n\n")

def registrar_rut_fallido(texto, nombre, rut):
    os.makedirs("logs", exist_ok=True)
    with open("logs/rut_fallido.log", "a", encoding="utf-8") as f:
        fecha = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        f.write(f"[{fecha}] Nombre detectado: '{nombre}' | RUT detectado: '{rut}' | Texto original: {texto}\n")

def extraer_rut(texto):
    texto = texto.replace(".", "").replace(" ", "").lower()
    match = re.search(r"\d{7,8}-?[0-9k]", texto)
    return match.group(0) if match else ""

def normalizar_rut(rut):
    rut = rut.replace(".", "").replace(" ", "").upper()
    if "-" not in rut and len(rut) >= 8:
        rut = rut[:-1] + "-" + rut[-1]
    if re.match(r"^\d{7,8}-[\dK]$", rut):
        return rut
    return ""

def extraer_nombre(texto):
    texto_limpio = re.sub(r"\b\d{7,8}-?[0-9kK]\b", "", texto, flags=re.IGNORECASE)
    texto_limpio = re.sub(r"\brut\b", "", texto_limpio, flags=re.IGNORECASE)

    patron = re.compile(
        r"(?:me\s+llamo|mi\s+nombre\s+es|soy)\s+" +
        r"([A-Za-zÁÉÍÓÚáéíóúÑñ]{2,})\s+([A-Za-zÁÉÍÓÚáéíóúÑñ]{2,})",
        flags=re.IGNORECASE,
    )
    m = patron.search(texto_limpio)
    if m:
        return f"{m.group(1).capitalize()} {m.group(2).capitalize()}"

    palabras = re.findall(r"[A-Za-zÁÉÍÓÚáéíóúÑñ]{2,}", texto_limpio)
    if len(palabras) >= 2:
        return f"{palabras[-2].capitalize()} {palabras[-1].capitalize()}"
    return ""

def requiere_aclaracion(texto):
    frases_vagas = ["no sé", "cosas raras", "me siento raro", "algo pasa", "no entiendo bien", "mal", "terrible", "así no más", "extraño", "como que"]
    return any(f in texto.lower() for f in frases_vagas)

def sintetizar_resumen(texto):
    texto = texto.lower()
    sintomas = []
    if any(p in texto for p in ["temblor", "temblores", "tiritón", "tiritones", "visión", "vision", "mareo", "convulsión", "náusea", "confusión"]):
        sintomas.append("síntomas neurológicos")
    if any(p in texto for p in ["suicidio", "matarme", "morir", "quitarme la vida", "dejar de existir"]):
        sintomas.append("ideas suicidas")
    if "litio" in texto:
        sintomas.append("consulta sobre litio")
    return ", ".join(sintomas) or "sin hallazgos relevantes"

def sintetizar_con_ia(texto, client):
    resumen = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": "Resume en una línea los síntomas o preocupaciones médicas más relevantes de este paciente para su ficha clínica."},
            {"role": "user", "content": texto}
        ]
    )
    return resumen.choices[0].message.content.strip()

@app.get("/", response_class=HTMLResponse)
async def serve_index():
    path = os.path.join(os.path.dirname(__file__), "index.html")
    with open(path, "r", encoding="utf-8") as f:
        return f.read()
