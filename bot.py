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

def calcular_indices(precio, media_20, media_50, rsi):
    compra = 0
    venta = 0
    motivos_compra = []
    motivos_venta = []

    if media_20 > media_50:
        compra += 35
        motivos_compra.append("tendencia alcista")
    else:
        venta += 35
        motivos_venta.append("tendencia bajista")

    if precio > media_50:
        compra += 15
        motivos_compra.append("precio sobre su media de 50 días")
    else:
        venta += 15
        motivos_venta.append("precio bajo su media de 50 días")

    if rsi < 30:
        compra += 50
        motivos_compra.append("RSI sobrevendido")
    elif rsi < 45:
        compra += 25
        motivos_compra.append("RSI bajo")
    elif rsi > 70:
        venta += 50
        motivos_venta.append("RSI sobrecomprado")
    elif rsi > 60:
        venta += 20
        motivos_venta.append("RSI alto")

    return compra, venta, motivos_compra, motivos_venta

avisos = []

for nombre, ticker in activos.items():
    datos = yf.Ticker(ticker).history(period="6mo")
    if datos.empty or len(datos) < 50:
        continue

    precio = round(datos["Close"].iloc[-1], 2)
    media_20 = datos["Close"].rolling(window=20).mean().iloc[-1]
    media_50 = datos["Close"].rolling(window=50).mean().iloc[-1]
    rsi = round(calcular_rsi(datos["Close"]), 1)

    compra, venta, mot_c, mot_v = calcular_indices(precio, media_20, media_50, rsi)

    if compra >= 70:
        avisos.append(
            f"🟢 COMPRA: {nombre} ({precio} €)\n"
            f"Índice de confianza: {compra}%\n"
            f"Señales: {', '.join(mot_c)}\n"
            f"RSI: {rsi}"
        )
    elif venta >= 55:
        avisos.append(
            f"🔴 VENTA: {nombre} ({precio} €)\n"
            f"Índice de confianza: {venta}%\n"
            f"Señales: {', '.join(mot_v)}\n"
            f"RSI: {rsi}"
        )

if avisos:
    mensaje = "⚠️ Tradia — Señal de inversión:\n\n" + "\n\n".join(avisos)
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    requests.post(url, data={"chat_id": CHAT_ID, "text": mensaje})



