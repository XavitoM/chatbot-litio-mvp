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
@app.post("/mensaje")
async def recibir_mensaje(message: Message):
    global nombre_pendiente, rut_pendiente
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    texto = message.content

    nombre = extraer_nombre(texto)
    rut = normalizar_rut(extraer_rut(texto))
    fecha = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    print("DEBUG | Nombre extraído:", nombre, "| RUT normalizado:", rut)

    if rut in pacientes_en_sesion:
        nombre = pacientes_en_sesion[rut]
    elif nombre and rut:
        pacientes_en_sesion[rut] = nombre
        nombre_pendiente = ""
        rut_pendiente = ""
    elif nombre and not rut:
        nombre_pendiente = nombre
        if rut_pendiente:
            pacientes_en_sesion[rut_pendiente] = nombre
            rut = rut_pendiente
            nombre_pendiente = ""
            rut_pendiente = ""
        else:
            registrar_rut_fallido(texto, nombre, rut)
            return {"respuesta": f"Gracias {nombre.split()[0]}, ¿podrías indicarme tu RUT?"}
    elif rut and not nombre:
        rut_pendiente = rut
        if nombre_pendiente:
            pacientes_en_sesion[rut] = nombre_pendiente
            nombre = nombre_pendiente
            nombre_pendiente = ""
            rut_pendiente = ""
        else:
            registrar_rut_fallido(texto, nombre, rut)
            return {"respuesta": "Gracias. ¿Cuál es tu nombre completo?"}
    else:
        registrar_rut_fallido(texto, nombre, rut)
        respuesta_presentacion = (
            "Hola, soy tu asistente médico. Estoy aquí para ayudarte a monitorear tu tratamiento con litio y tus síntomas. "
            "Por ahora no pude registrar tu nombre o RUT correctamente, ya que soy un prototipo aún en desarrollo. "
            "De todos modos, puedes contarme lo que te pasa y haré lo mejor posible por ayudarte."
        )
        return {"respuesta": respuesta_presentacion}

    if requiere_aclaracion(texto):
        return {"respuesta": "¿Podrías explicarme un poco más a qué te refieres con eso? Quiero entender bien para poder ayudarte mejor."}

    resumen = sintetizar_resumen(texto)
    if resumen == "sin hallazgos relevantes":
        resumen = sintetizar_con_ia(texto, client)

    respuesta = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": "Eres un asistente médico experto en seguimiento de pacientes con litio. Evalúas criterios de gravedad de forma no sugestiva porque tus pacientes son vulnerables. Además, debes consultar al menos una vez a la semana sobre los síntomas suicidas y evaluar su gravedad según las escalas más modernas."},
            {"role": "user", "content": texto}
        ]
    )

    contenido_respuesta = respuesta.choices[0].message.content

    if "urgencias" in contenido_respuesta.lower():
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
    palabras = re.findall(r"[A-Za-zÁÉÍÓÚáéíóúÑñ]+", texto_limpio)
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
