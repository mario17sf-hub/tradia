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

def calcular_rsi(precios, periodo=14):
    delta = precios.diff()
    ganancias = delta.where(delta > 0, 0.0)
    perdidas = -delta.where(delta < 0, 0.0)
    media_ganancias = ganancias.rolling(window=periodo).mean()
    media_perdidas = perdidas.rolling(window=periodo).mean()
    rs = media_ganancias / media_perdidas
    rsi = 100 - (100 / (1 + rs))
    return rsi.iloc[-1]

mensaje = "📊 Análisis técnico:\n\n"

for nombre, ticker in activos.items():
    datos = yf.Ticker(ticker).history(period="6mo")

    if datos.empty or len(datos) < 50:
        mensaje += f"{nombre}: datos insuficientes\n\n"
        continue

    precio_actual = round(datos["Close"].iloc[-1], 2)
    media_20 = round(datos["Close"].rolling(window=20).mean().iloc[-1], 2)
    media_50 = round(datos["Close"].rolling(window=50).mean().iloc[-1], 2)
    rsi = round(calcular_rsi(datos["Close"]), 1)

    if media_20 > media_50:
        tendencia = "alcista 📈"
    else:
        tendencia = "bajista 📉"

    if rsi > 70:
        estado_rsi = "sobrecomprado"
    elif rsi < 30:
        estado_rsi = "sobrevendido"
    else:
        estado_rsi = "neutral"

    mensaje += (
        f"{nombre}: {precio_actual} €\n"
        f"Tendencia: {tendencia}\n"
        f"RSI: {rsi} ({estado_rsi})\n\n"
    )

url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
requests.post(url, data={"chat_id": CHAT_ID, "text": mensaje})


