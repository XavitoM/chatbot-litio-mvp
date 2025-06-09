from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import os
from dotenv import load_dotenv
from openai import OpenAI
import smtplib
from email.mime.text import MIMEText

load_dotenv()

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

class MensajeUsuario(BaseModel):
    content: str
    nombre: str
    rut: str
    tipo_usuario: str

@app.post("/mensaje")
async def recibir_mensaje(mensaje: MensajeUsuario):
    prompt_sistema = (
        "Eres un asistente médico virtual experto en tratamiento con litio. "
        "Evalúas criterios de gravedad médica, estratificas riesgo suicida según la escala Columbia, "
        "relacionas síntomas con litio, y en caso de urgencia médica o riesgo alto, debes sugerir atención inmediata. "
        "Usa tono humano, cercano y claro."
    )

    mensajes = [
        {"role": "system", "content": prompt_sistema},
        {"role": "user", "content": mensaje.content}
    ]

    try:
        respuesta = client.chat.completions.create(
            model="gpt-4o",
            messages=mensajes
        )
        contenido = respuesta.choices[0].message.content
    except Exception as e:
        contenido = f"Error del asistente: {str(e)}"

    return {"respuesta": contenido}

@app.get("/", response_class=HTMLResponse)
async def serve_index():
    with open("index.html", "r", encoding="utf-8") as f:
        return f.read()
