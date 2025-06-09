from fastapi import FastAPI, Request
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
import os
import re
import smtplib
from email.mime.text import MIMEText
from openai import OpenAI
import json

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

pacientes_en_sesion = {}

class Message(BaseModel):
    content: str
    nombre: str
    rut: str
    tipo_usuario: str

@app.post("/mensaje")
async def recibir_mensaje(message: Message):
    nombre = message.nombre.strip()
    rut = normalizar_rut(message.rut.strip())
    tipo = message.tipo_usuario

    guardar_resumen(nombre, rut, tipo, message.content)
    guardar_mensaje_completo(nombre, rut, message.content)

    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    respuesta = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": "Eres un asistente médico experto en seguimiento de pacientes con litio. Evalúas criterios de gravedad y riesgo suicida usando la escala Columbia. Si identificas riesgo médico moderado, avisas al equipo clínico y sugieres consulta precoz. Clasificas y resguardas la información por paciente según su RUT."},
            {"role": "user", "content": message.content}
        ]
    )

    contenido_respuesta = respuesta.choices[0].message.content

    if contiene_alerta_medica(contenido_respuesta):
        enviar_correo_alerta(nombre, rut, message.content, contenido_respuesta)

    return {"respuesta": contenido_respuesta}

def normalizar_rut(rut):
    rut = rut.upper().replace(".", "").replace("-", "")
    if len(rut) > 1:
        return f"{rut[:-1]}-{rut[-1]}"
    return rut

def contiene_alerta_medica(texto):
    patrones = ["urgencia", "riesgo vital", "hospital", "convulsion", "desmayo", "visión borrosa", "ideas suicidas", "querer morir"]
    return any(p in texto.lower() for p in patrones)

def enviar_correo_alerta(nombre, rut, mensaje_original, respuesta):
    remitente = os.getenv("EMAIL_USER")
    destinatario = "uhciphospitalangol@gmail.com"
    password = os.getenv("EMAIL_PASS")

    contenido = f"Nombre: {nombre}\nRUT: {rut}\n\nMensaje del paciente:\n{mensaje_original}\n\nRespuesta del asistente:\n{respuesta}"
    mensaje = MIMEText(contenido)
    mensaje['Subject'] = "ALERTA - Revisión Clínica Prioritaria"
    mensaje['From'] = remitente
    mensaje['To'] = destinatario

    with smtplib.SMTP("smtp.gmail.com", 587) as servidor:
        servidor.starttls()
        servidor.login(remitente, password)
        servidor.send_message(mensaje)

def guardar_resumen(nombre, rut, tipo, mensaje):
    resumen = f"{nombre},{rut},{tipo},{mensaje[:100].replace(',', ' ')}\n"
    try:
        with open("registro_resumen.csv", "a", encoding="utf-8") as f:
            f.write(resumen)
    except Exception as e:
        print(f"ERROR al guardar resumen: {e}")

def guardar_mensaje_completo(nombre, rut, mensaje):
    rut_archivo = rut.replace("-", "").replace(".", "")
    archivo = f"interacciones/{rut_archivo}.txt"
    os.makedirs("interacciones", exist_ok=True)
    try:
        with open(archivo, "a", encoding="utf-8") as f:
            f.write(f"{nombre} ({rut}): {mensaje}\n")
    except Exception as e:
        print(f"ERROR al guardar mensaje completo: {e}")

@app.get("/", response_class=HTMLResponse)
async def serve_index():
    path = os.path.join(os.path.dirname(__file__), "index.html")
    with open(path, "r", encoding="utf-8") as f:
        return f.read()

