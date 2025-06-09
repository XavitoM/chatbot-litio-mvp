# Chatbot Litio MVP

Pequeño asistente de seguimiento para pacientes en tratamiento con litio. El frontend solicita el nombre, RUT y tipo de usuario antes de iniciar la conversación. Luego permite chatear con un bot que evalúa síntomas, riesgo suicida e informa por correo si detecta emergencia.

## Uso rápido

1. Crea un archivo `.env` con tus claves:
   ```
   OPENAI_API_KEY=tu_clave
   EMAIL_USER=tu_correo@gmail.com
   EMAIL_PASS=tu_contraseña
   ```
2. Instala dependencias:
   ```
   pip install -r requirements.txt
   ```
3. Ejecuta el servidor:
   ```
   uvicorn main:app --reload
   ```
4. Abre `http://localhost:8000/` en tu navegador y completa el formulario para comenzar a chatear.

## Pruebas

```
pytest
```
