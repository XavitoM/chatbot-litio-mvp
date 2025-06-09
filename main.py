import os
import re
import csv
from datetime import datetime
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
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

# Helpers ---------------------------------------------------------------

def extraer_rut(texto: str) -> str:
    """Extrae la primera secuencia parecida a un RUT."""
    texto = texto.replace(".", "")
    patron = r"\b\d{7,8}-?[0-9Kk]\b"
    m = re.search(patron, texto)
    return m.group(0) if m else ""


def extraer_nombre(texto: str) -> str:
    """Intenta extraer un nombre compuesto de al menos dos palabras."""
    patrones = [
        r"(?:me\s+llamo|soy|nombre\s+es)\s+([a-zA-ZÁÉÍÓÚÑñ]+\s+[a-zA-ZÁÉÍÓÚÑñ]+)",
        r"([a-zA-ZÁÉÍÓÚÑñ]+\s+[a-zA-ZÁÉÍÓÚÑñ]+)(?=\s*rut|\s*\d|$)",
    ]
    for pat in patrones:
        m = re.search(pat, texto, re.IGNORECASE)
        if m:
            palabras = m.group(1).split()
            return " ".join(p.capitalize() for p in palabras)
    return ""


def normalizar_rut(rut: str) -> str:
    """Normaliza formato y valida contenido básico."""
    rut = rut.upper().replace(".", "").replace("-", "")
    if len(rut) < 2 or not rut[:-1].isdigit() or rut[-1] not in "0123456789K":
        return ""
    return f"{rut[:-1]}-{rut[-1]}"


# Modelo ----------------------------------------------------------------
class MensajeUsuario(BaseModel):
    content: str
    nombre: str
    rut: str
    tipo_usuario: str


# Endpoint ---------------------------------------------------------------
@app.post("/mensaje")
async def recibir_mensaje(mensaje: MensajeUsuario):
    """Genera respuesta con GPT-4 y registra la conversación."""
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    prompt_sistema = (
        "Eres un asistente médico virtual experto en tratamiento con litio. "
        "Evalúa síntomas, riesgo suicida con la escala Columbia y sugiere acudir "
        "a urgencias si detectas riesgo alto."
    )
    mensajes = [
        {"role": "system", "content": prompt_sistema},
        {"role": "user", "content": mensaje.content},
    ]
    try:
        respuesta = client.chat.completions.create(model="gpt-4o", messages=mensajes)
        contenido = respuesta.choices[0].message.content
    except Exception as e:
        contenido = f"Error del asistente: {e}"

    guardar_registro(mensaje, contenido)
    detectar_y_escalar(mensaje, contenido)
    return {"respuesta": contenido}


@app.get("/", response_class=HTMLResponse)
async def serve_index():
    with open("index.html", "r", encoding="utf-8") as f:
        return f.read()


# Utilidades de registro y alerta --------------------------------------

def guardar_registro(msg: MensajeUsuario, respuesta: str) -> None:
    nombre = msg.nombre or extraer_nombre(msg.content)
    rut_raw = msg.rut or extraer_rut(msg.content)
    rut = normalizar_rut(rut_raw)
    fecha = datetime.now().isoformat()
    fila = [fecha, nombre, rut, msg.tipo_usuario, msg.content, respuesta]
    try:
        archivo = "registros.csv"
        existe = os.path.exists(archivo)
        with open(archivo, "a", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            if not existe:
                writer.writerow(["fecha", "nombre", "rut", "tipo", "mensaje", "respuesta"])
            writer.writerow(fila)
        # guardar conversación completa por usuario
        if rut:
            with open(f"{rut}.txt", "a", encoding="utf-8") as ftxt:
                ftxt.write(f"[{fecha}] usuario: {msg.content}\n")
                ftxt.write(f"[{fecha}] bot: {respuesta}\n")
    except Exception:
        pass


def detectar_y_escalar(msg: MensajeUsuario, respuesta: str) -> None:
    """Envía un correo si se detectan palabras clave de riesgo."""
    texto = f"{msg.content} {respuesta}".lower()
    alertas = ["suicidio", "matarme", "urgencia", "convulsiones"]
    if any(p in texto for p in alertas):
        usuario = os.getenv("EMAIL_USER")
        clave = os.getenv("EMAIL_PASS")
        destinatario = os.getenv("EMAIL_ALERT", usuario)
        if not usuario or not clave:
            return
        mensaje = MIMEText(
            f"Se detectó posible emergencia en mensaje de {msg.nombre} ({msg.rut})."
        )
        mensaje["Subject"] = "Alerta Asistente Litio"
        mensaje["From"] = usuario
        mensaje["To"] = destinatario
        try:
            with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
                smtp.login(usuario, clave)
                smtp.sendmail(usuario, destinatario, mensaje.as_string())
        except Exception:
            pass


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
