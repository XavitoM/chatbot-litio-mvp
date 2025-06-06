Chatbot Litio MVP

Este proyecto es un MVP para un chatbot de seguimiento de pacientes en tratamiento con litio. Utiliza:

- Frontend web simple (HTML)
- Backend en FastAPI
- API de ChatGPT para análisis
- SMTP para alertas por correo a uhciphospitalangol@gmail.com

Cómo usar

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

gcudmw-codex/revisar-código-para-respuesta-incorrecta
4. Abre `index.html` en tu navegador.

El bot recuerda tu nombre o RUT si los envías por separado. Una vez que se registran ambos datos, te consultará si estás tomando litio para ofrecerte acompañamiento personalizado.

4. Abre `web/index.html` en tu navegador.

El bot ahora puede recordar tu nombre o RUT si los envías por separado. Si solo
envías tu nombre, se te solicitará el RUT en el siguiente mensaje y viceversa.
main

Para ejecutar las pruebas:
```
pip install -r requirements.txt
pytest
```
