# Chatbot Litio MVP

Este proyecto es un MVP para un chatbot de seguimiento de pacientes en tratamiento con litio. Utiliza:

- Frontend web simple (HTML)
- Backend en FastAPI
- API de ChatGPT para análisis
- SMTP para alertas por correo a uhciphospitalangol@gmail.com

## Cómo usar

1. Configura tus variables de entorno en `.env`:
```
OPENAI_API_KEY=tu_clave
EMAIL_USER=tu_correo@gmail.com
EMAIL_PASS=tu_contraseña
```

2. Instala dependencias:
```
pip install -r requirements.txt
```

3. Corre el servidor:
```
uvicorn main:app --reload
```

4. Visita `http://localhost:8000/` en tu navegador.

El bot recuerda tu nombre o RUT si los envías por separado. Una vez que se registran ambos datos, te consultará si estás tomando litio para ofrecerte acompañamiento personalizado. Si no logra identificar tus datos, de todas formas seguirá la conversación preguntando cómo te sientes.

Para ejecutar las pruebas:
```
pip install -r requirements.txt
pytest
```
