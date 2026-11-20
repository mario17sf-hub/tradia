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

def calcular_indice(tendencia_alcista, rsi):
    puntos = 0
    if tendencia_alcista:
        puntos += 40
    if rsi < 30:
        puntos += 60
    elif rsi < 45:
        puntos += 30
    elif rsi > 70:
        puntos -= 30
    indice_compra = max(0, min(100, puntos))
    indice_venta = max(0, min(100, 100 - puntos - (20 if tendencia_alcista else 0)))
    return indice_compra, indice_venta

avisos = []

for nombre, ticker in activos.items():
    datos = yf.Ticker(ticker).history(period="6mo")
    if datos.empty or len(datos) < 50:
        continue

    precio = round(datos["Close"].iloc[-1], 2)
    media_20 = datos["Close"].rolling(window=20).mean().iloc[-1]
    media_50 = datos["Close"].rolling(window=50).mean().iloc[-1]
    tendencia_alcista = media_20 > media_50
    rsi = round(calcular_rsi(datos["Close"]), 1)

    indice_compra, indice_venta = calcular_indice(tendencia_alcista, rsi)

    if indice_compra >= 70:
        avisos.append(
            f"🟢 COMPRA: {nombre} ({precio} €)\n"
            f"Índice de confianza: {indice_compra}%\n"
            f"Tendencia: {'alcista 📈' if tendencia_alcista else 'bajista 📉'} | RSI: {rsi}\n"
            f"Motivo: señales técnicas positivas"
        )
    elif indice_venta >= 55:
        avisos.append(
            f"🔴 VENTA: {nombre} ({precio} €)\n"
            f"Índice de confianza venta: {indice_venta}%\n"
            f"Tendencia: {'alcista 📈' if tendencia_alcista else 'bajista 📉'} | RSI: {rsi}\n"
            f"Motivo: señales técnicas negativas"
        )

if avisos:
    mensaje = "⚠️ Tradia — Señal de inversión:\n\n" + "\n\n".join(avisos)
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    requests.post(url, data={"chat_id": CHAT_ID, "text": mensaje})


