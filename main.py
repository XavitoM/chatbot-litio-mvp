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

@app.post("/mensaje")
async def recibir_mensaje(message: Message):
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    texto = message.content

    nombre = extraer_nombre(texto)
    rut = normalizar_rut(extraer_rut(texto))
    fecha = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    if not nombre or not rut:
        return {"respuesta": "Hola, soy tu asistente médico. Estoy aquí para ayudarte a monitorear tu tratamiento con litio y síntomas relacionados. Antes de comenzar, por favor indícame tu nombre completo y tu RUT para poder registrarte correctamente."}

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

    with open("registro_resumen.csv", "a", newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow([fecha, nombre, rut, resumen])

    archivo = f"conversaciones/{rut}.txt"
    with open(archivo, "a", encoding="utf-8") as f:
        f.write(f"[{fecha}] Usuario: {mensaje}\n")
        f.write(f"[{fecha}] Bot: {respuesta}\n\n")

def extraer_rut(texto):
    texto = texto.replace(".", "").replace(" ", "").lower()
    posibles = re.findall(r"\b\d{7,8}-?[\dk]\b", texto)
    return posibles[0] if posibles else ""

def normalizar_rut(rut):
    rut = rut.replace(".", "").replace(" ", "").upper()
    if "-" not in rut and len(rut) >= 8:
        return rut[:-1] + "-" + rut[-1]
    return rut

def extraer_nombre(texto):
    partes = texto.strip().split()
    posibles = [p for p in partes if p.isalpha() and len(p) > 2]
    if len(posibles) >= 2:
        return f"{posibles[0]} {posibles[1]}"
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


