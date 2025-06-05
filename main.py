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

    respuesta = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": "Eres un asistente médico experto en seguimiento de pacientes con litio. Evalúas criterios de gravedad de forma no sugestiva porque tus pacientes son vulnerables. Además, debes consultar al menos una vez a la semana sobre los síntomas suicidas y evaluar su gravedad según las escalas más modernas."},
            {"role": "user", "content": message.content}
        ]
    )

    contenido_respuesta = respuesta.choices[0].message.content

    if "urgencias" in contenido_respuesta.lower():
        enviar_correo_alerta(message.content, contenido_respuesta)

    registrar_interaccion(message.content, contenido_respuesta)

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

def registrar_interaccion(mensaje, respuesta):
    os.makedirs("conversaciones", exist_ok=True)

    nombre = extraer_nombre(mensaje)
    rut = extraer_rut(mensaje)
    fecha = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    resumen = sintetizar_resumen(mensaje)

    # Guardar resumen CSV
    with open("registro_resumen.csv", "a", newline='', encoding='utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([fecha, nombre, rut, resumen])

    # Guardar conversación completa
    archivo = f"conversaciones/{rut or 'sin_rut'}.txt"
    with open(archivo, "a", encoding="utf-8") as f:
        f.write(f"[{fecha}] Usuario: {mensaje}\n")
        f.write(f"[{fecha}] Bot: {respuesta}\n\n")

def extraer_rut(texto):
    posibles = re.findall(r"\b\d{7,8}-?[\dkK]\b|\b\d{1,2}\.\d{3}\.\d{3}-?[\dkK]\b", texto)
    return posibles[0] if posibles else ""

def extraer_nombre(texto):
    partes = texto.split()
    for i in range(len(partes) - 1):
        if partes[i][0].isupper() and partes[i+1][0].isupper():
            return f"{partes[i]} {partes[i+1]}"
    return ""

def sintetizar_resumen(texto):
    texto = texto.lower()
    sintomas = []
    if any(p in texto for p in ["temblor", "visión", "mareo", "convulsión", "náusea", "confusión"]):
        sintomas.append("síntomas neurológicos")
    if "suicidio" in texto or "matarme" in texto or "morir" in texto:
        sintomas.append("ideas suicidas")
    if "litio" in texto:
        sintomas.append("consulta sobre litio")
    return ", ".join(sintomas) or "sin hallazgos relevantes"

@app.get("/", response_class=HTMLResponse)
async def serve_index():
    path = os.path.join(os.path.dirname(__file__), "index.html")
    with open(path, "r", encoding="utf-8") as f:
        return f.read()
