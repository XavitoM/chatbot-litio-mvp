from fastapi import FastAPI
from pydantic import BaseModel
import openai
import smtplib
from email.mime.text import MIMEText
from fastapi.middleware.cors import CORSMiddleware
import os

app = FastAPI()

# Permitir solicitudes desde frontend local
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

openai.api_key = os.getenv("OPENAI_API_KEY")

class Message(BaseModel):
    content: str

@app.post("/mensaje")
async def recibir_mensaje(message: Message):
    respuesta = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": "Eres un asistente médico experto en seguimiento de pacientes con litio, tienes que revisar los criterios de gravedad de cualquier grado para poder preguntarle al paciente los diferentes sintomas que pueda tener de una forma que no se sugestiva, ya que lidias con pacientes que son especialmente vulnerables."},
            {"role": "user", "content": message.content}
        ]
    )
    contenido_respuesta = respuesta['choices'][0]['message']['content']

    if "urgencias" in contenido_respuesta.lower():
        enviar_correo_alerta(message.content, contenido_respuesta)

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
from fastapi.responses import HTMLResponse

@app.get("/", response_class=HTMLResponse)
async def serve_index():
    with open("index.html", "r", encoding="utf-8") as f:
        return f.read()
