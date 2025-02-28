from twilio.rest import Client
import os
from dotenv import load_dotenv

load_dotenv()

def enviar_mensaje_whatsapp(mensaje: str, numero_destino: str):
    # Configura tus credenciales de Twilio
    account_sid = os.getenv('TWILIO_ACCOUNT_SID')
    auth_token = os.getenv('TWILIO_AUTH_TOKEN')
    client = Client(account_sid, auth_token)

    # Envía el mensaje de WhatsApp
    try:
        message = client.messages.create(
            body=mensaje,
            from_=os.getenv('TWILIO_WHATSAPP_FROM'),  # Número de WhatsApp de Twilio
            to=os.getenv('TWILIO_WHATSAPP_TO')
        )
        print(f"Mensaje enviado: {message.sid}")
    except Exception as e:
        print(f"Error al enviar mensaje: {e}")

# Ejemplo de uso
enviar_mensaje_whatsapp("Hola, este es un mensaje de prueba", "+1234567890")