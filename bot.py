import os
import requests
import yfinance as yf

TOKEN = os.environ["TELEGRAM_TOKEN"]
CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]

activos = {
    "Santander": "SAN.MC",
    "Iberdrola": "IBE.MC",
    "Inditex": "ITX.MC",
}

mensaje = "📊 Precios actuales:\n\n"

for nombre, ticker in activos.items():
    datos = yf.Ticker(ticker).history(period="1d")
    if not datos.empty:
        precio = round(datos["Close"].iloc[-1], 2)
        mensaje += f"{nombre}: {precio} €\n"
    else:
        mensaje += f"{nombre}: no se pudo obtener el precio\n"

url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
requests.post(url, data={"chat_id": CHAT_ID, "text": mensaje})

