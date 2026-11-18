import os
import requests

TOKEN = os.environ["TELEGRAM_TOKEN"]
CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]

mensaje = "🤖 Tradia está conectado y funcionando correctamente."

url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
response = requests.post(url, data={"chat_id": CHAT_ID, "text": mensaje})

print("Respuesta de Telegram:", response.status_code, response.text)
