import os, re, csv, json, time, base64
from datetime import datetime, timezone, timedelta
from urllib.parse import quote_plus
import numpy as np
import pandas as pd
import requests
import feedparser
import yfinance as yf

TOKEN = os.environ.get("TELEGRAM_TOKEN", "")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")
GH_TOKEN = os.environ.get("GH_TOKEN", "")
GH_REPO = "mario17sf-hub/tradia"
UA = {"User-Agent": "Mozilla/5.0 (compatible; TradiaBot/1.0)"}

# Activos conocidos: siempre se analizan, aunque falle la descarga de listas
BASE = {
    "Santander":"SAN.MC","BBVA":"BBVA.MC","Inditex":"ITX.MC","Iberdrola":"IBE.MC",
    "Repsol":"REP.MC","Telefónica":"TEF.MC","CaixaBank":"CABK.MC","Amadeus":"AMS.MC",
    "Ferrovial":"FER.MC","ACS":"ACS.MC","Mapfre":"MAP.MC","Meliá":"MEL.MC","IAG":"IAG.MC",
    "Acciona":"ANA.MC","Red Eléctrica":"REE.MC","Enagás":"ENG.MC","Endesa":"ELE.MC",
    "Naturgy":"NTGY.MC","Grifols":"GRF.MC","Bankinter":"BKT.MC","Sabadell":"SAB.MC",
    "Colonial":"COL.MC","Merlin":"MRL.MC","Fluidra":"FDR.MC","Solaria":"SLR.MC",
    "Pharma Mar":"PHM.MC","Viscofan":"VIS.MC","Vidrala":"VID.MC","Logista":"LOG.MC",
    "Unicaja":"UNI.MC","Acerinox":"ACX.MC","ArcelorMittal":"MTS.MC","Cellnex":"CLNX.MC",
    "Indra":"IDR.MC","Almirall":"ALM.MC",
    "SAP":"SAP.DE","Siemens":"SIE.DE","Allianz":"ALV.DE","BASF":"BAS.DE","BMW":"BMW.DE",
    "Deutsche Bank":"DBK.DE","Volkswagen":"VOW3.DE","Bayer":"BAYN.DE","Adidas":"ADS.DE",
    "Deutsche Telekom":"DTE.DE","Mercedes-Benz":"MBG.DE","Rheinmetall":"RHM.DE",
    "Infineon":"IFX.DE","Munich Re":"MUV2.DE","Hannover Re":"HNR1.DE","Puma":"PUM.DE",
    "Zalando":"ZAL.DE","Vonovia":"VNA.DE","RWE":"RWE.DE","E.ON":"EOAN.DE",
    "Continental":"CON.DE","Brenntag":"BNR.DE",
    "LVMH":"MC.PA","TotalEnergies":"TTE.PA","Sanofi":"SAN.PA","LOreal":"OR.PA",
    "BNP Paribas":"BNP.PA","Airbus":"AIR.PA","AXA":"CS.PA","Schneider Electric":"SU.PA",
    "Air Liquide":"AI.PA","Danone":"BN.PA","Pernod Ricard":"RI.PA","Michelin":"ML.PA",
    "Renault":"RNO.PA","Saint-Gobain":"SGO.PA","Capgemini":"CAP.PA",
    "Dassault Systemes":"DSY.PA","Kering":"KER.PA","Hermes":"RMS.PA","Engie":"ENGI.PA",
    "Societe Generale":"GLE.PA","Credit Agricole":"ACA.PA","Legrand":"LR.PA",
    "Vinci":"DG.PA","Bouygues":"EN.PA",
    "ENI":"ENI.MI","Enel":"ENEL.MI","UniCredit":"UCG.MI","Intesa Sanpaolo":"ISP.MI",
    "Generali":"G.MI","Ferrari":"RACE.MI","Leonardo":"LDO.MI","Mediobanca":"MB.MI",
    "Pirelli":"PIRC.MI","Stellantis":"STLAM.MI","Prysmian":"PRY.MI","Moncler":"MONC.MI",
    "ASML":"ASML.AS","Shell":"SHEL.AS","Philips":"PHIA.AS","ING":"INGA.AS",
    "Heineken":"HEIA.AS","Wolters Kluwer":"WKL.AS","NN Group":"NN.AS","IMCD":"IMCD.AS",
    "Aegon":"AGN.AS","ASM International":"ASM.AS",
    "EDP":"EDP.LS","Galp":"GALP.LS","Jerónimo Martins":"JMT.LS","Sonae":"SON.LS","BCP":"BCP.LS",
    "ETF Ibex35":"BBVAI.MC","ETF EuroStoxx50":"DBXT.MI","ETF DAX":"EXS1.DE",
    "ETF Defensa EU":"ASWC.AS","ETF Energía limpia":"IQQH.DE",
    "ETF Semiconductores":"SEMI.AS","ETF Dividendo EU":"EUDV.AS","ETF Oro EUR":"IGLN.AS",
}
SECTORES = {
    "banca":["Santander","BBVA","CaixaBank","Bankinter","Sabadell","Deutsche Bank",
             "BNP Paribas","UniCredit","Intesa Sanpaolo","ING","Unicaja","Mediobanca",
             "Societe Generale","Credit Agricole","BCP"],
    "energía":["Iberdrola","Repsol","Endesa","Naturgy","Enagás","Red Eléctrica",
               "TotalEnergies","ENI","Enel","Engie","Shell","Solaria","RWE","E.ON","EDP","Galp"],
    "tecnología":["SAP","Infineon","ASML","Amadeus","Capgemini","Dassault Systemes","Indra","ASM International"],
    "lujo":["LVMH","Hermes","Kering","Ferrari","Moncler","Adidas","Puma"],
    "industria":["Siemens","Airbus","Leonardo","Ferrovial","ACS","Acciona","Rheinmetall","Vinci","Prysmian"],
}
SECTOR_TICKER = {BASE[n]: s for s, lista in SECTORES.items() for n in lista if n in BASE}

PAL_POS = ["sube","récord","beneficio","contrato","dividendo","crecimiento","expansión","fusión",
           "positivo","rise","record","profit","deal","dividend","growth","acquisition","merger","rally"]
PAL_NEG = ["caída","baja","pérdida","crisis","multa","fraude","quiebra","dimisión","escándalo",
           "sanción","recesión","fall","drop","loss","fine","fraud","bankrupt","resign",
           "scandal","sanction","recession","decline","plunge"]
RE_POS = re.compile(r"\b(" + "|".join(map(re.escape, PAL_POS)) + ")", re.I)
RE_NEG = re.compile(r"\b(" + "|".join(map(re.escape, PAL_NEG)) + ")", re.I)

# ---------- GitHub ----------
def gh_headers(raw=False):
    return {"Authorization": f"token {GH_TOKEN}",
            "Accept": "application/vnd.github.raw+json" if raw else "application/vnd.github.v3+json"}

def gh_url(ruta):
    return f"https://api.github.com/repos/{GH_REPO}/contents/{ruta}"

def gh_sha(ruta):
    r = requests.get(gh_url(ruta), headers=gh_headers(), timeout=60)
    if r.status_code == 404:
        return None
    r.raise_for_status()
    return r.json().get("sha")

def gh_leer(ruta):
    r = requests.get(gh_url(ruta), headers=gh_headers(raw=True), timeout=120)
    if r.status_code == 404:
        return None
    r.raise_for_status()
    try:
        return json.loads(r.text)
    except Exception:
        return None

def _git_api(metodo, ruta, **kw):
    r = metodo(f"https://api.github.com/repos/{GH_REPO}/{ruta}", headers=gh_headers(), timeout=180, **kw)
    r.raise_for_status()
    return r.json()

def gh_escribir(ruta, data):
    """Escribe un archivo usando la Git Data API (blob + tree + commit), que
    no tiene el límite de 1 MB de la API de 'contents' usada antes. Con miles
    de activos, resultados.json y universo.json pesan varios MB, así que la
    API antigua rechazaba el guardado en silencio."""
    cuerpo = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    for intento in range(4):
        try:
            ref = _git_api(requests.get, "git/ref/heads/main")
            commit_actual = ref["object"]["sha"]
            commit_info = _git_api(requests.get, f"git/commits/{commit_actual}")
            base_tree = commit_info["tree"]["sha"]
            blob = _git_api(requests.post, "git/blobs",
                            json={"content": cuerpo, "encoding": "utf-8"})
            tree = _git_api(requests.post, "git/trees", json={
                "base_tree": base_tree,
                "tree": [{"path": ruta, "mode": "100644", "type": "blob", "sha": blob["sha"]}],
            })
            commit = _git_api(requests.post, "git/commits", json={
                "message": f"update {ruta}", "tree": tree["sha"], "parents": [commit_actual],
            })
            requests.patch(f"https://api.github.com/repos/{GH_REPO}/git/refs/heads/main",
                           headers=gh_headers(), json={"sha": commit["sha"]}, timeout=60).raise_for_status()
            print("Guardado", ruta, len(cuerpo) // 1024, "KB (commit", commit["sha"][:7], ")")
            return True
        except Exception as e:
            print(f"Error guardando {ruta} (intento {intento + 1}):", str(e)[:200])
            time.sleep(5)
    return False

def telegram(texto):
    if not TOKEN or not CHAT_ID:
        print(texto)
        return
    try:
        r = requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage",
                          data={"chat_id": CHAT_ID, "text": texto[:4000]}, timeout=30)
        if r.status_code != 200:
            print("Telegram error", r.status_code, r.text[:200])
    except Exception as e:
        print("Telegram error", e)

# ---------- Universo de activos en euros ----------
EXCHANGES = ["MCE", "PAR", "GER", "MIL", "AMS", "LIS", "BRU", "VIE", "HEL", "ISE", "ATH"]
XETRA_PAGINA = "https://www.cashmarket.deutsche-boerse.com/cash-en/trading/Tradable-Instruments-Xetra/Downloads"

def _query_bolsa(ex):
    err = None
    for op, operando in (("is-in", ["exchange", ex]), ("eq", ["exchange", ex])):
        try:
            return yf.EquityQuery(op, operando), None
        except Exception as e:
            err = e
    return None, str(err)[:80]

def universo_screener():
    out, resumen = {}, {}
    for ex in EXCHANGES:
        q, err = _query_bolsa(ex)
        if q is None:
            resumen[ex] = "no válida"
            continue
        n0, offset = len(out), 0
        for _ in range(60):
            try:
                r = yf.screen(q, offset=offset, size=250, sortField="intradaymarketcap", sortAsc=False)
            except Exception as e:
                resumen[ex] = f"error {str(e)[:40]}"
                break
            quotes = (r or {}).get("quotes") or []
            if not quotes:
                break
            for x in quotes:
                sym = x.get("symbol")
                cur = x.get("currency")
                if not sym or (cur and cur != "EUR"):
                    continue
                nombre = x.get("longName") or x.get("shortName") or sym
                tipo = "ETF" if x.get("quoteType") == "ETF" else "acción"
                out.setdefault(sym, {"n": nombre, "t": tipo})
            if len(quotes) < 250:
                break
            offset += 250
            time.sleep(0.5)
        resumen.setdefault(ex, len(out) - n0)
    return out, resumen

def universo_xetra_etfs():
    html = requests.get(XETRA_PAGINA, headers=UA, timeout=60).text
    enlaces = re.findall(r'href="([^"]+)"', html)
    csvs = [e for e in enlaces if "alltradableinstruments" in e.lower() and ".csv" in e.lower()]
    if not csvs:
        raise RuntimeError("sin enlace CSV")
    csvs.sort(key=lambda e: ("xetr" not in e.lower(), "simul" in e.lower(), len(e)))
    url = csvs[0].replace("&amp;", "&")
    if url.startswith("/"):
        url = "https://www.cashmarket.deutsche-boerse.com" + url
    texto = requests.get(url, headers=UA, timeout=120).content.decode("utf-8", errors="ignore")
    lineas = texto.splitlines()
    i = next((k for k, l in enumerate(lineas) if "ISIN" in l and "Mnemonic" in l), None)
    if i is None:
        raise RuntimeError("cabecera no encontrada")
    out = {}
    for fila in csv.DictReader(lineas[i:], delimiter=";"):
        mn = (fila.get("Mnemonic") or "").strip()
        if not mn:
            continue
        divisa = (fila.get("Settlement Currency") or fila.get("Currency") or "").strip()
        if divisa and divisa != "EUR":
            continue
        tipos = " ".join(v for k, v in fila.items() if k and "type" in k.lower() and isinstance(v, str)).upper()
        nombre = (fila.get("Instrument") or fila.get("Instrument Name") or mn).strip()
        if "ETF" not in tipos and "UCITS ETF" not in nombre.upper():
            continue
        if "ETN" in tipos or "ETC" in tipos:
            continue
        out[mn + ".DE"] = {"n": nombre, "t": "ETF"}
    return out

def construir_universo():
    activos = {t: {"n": n, "t": "ETF" if n.startswith("ETF ") else "acción"} for n, t in BASE.items()}
    diag = []
    try:
        pantalla, resumen = universo_screener()
        for t, d in pantalla.items():
            activos.setdefault(t, d)
        diag.append("Acciones por bolsa: " + ", ".join(f"{k} {v}" for k, v in resumen.items()))
    except Exception as e:
        diag.append("Acciones: error " + str(e)[:80])
    try:
        etfs = universo_xetra_etfs()
        for t, d in etfs.items():
            activos.setdefault(t, d)
        diag.append(f"ETFs de Xetra: {len(etfs)}")
    except Exception as e:
        diag.append("ETFs de Xetra: error " + str(e)[:80])
    return activos, diag

def cargar_universo():
    u = gh_leer("universo.json")
    ahora = datetime.now(timezone.utc)
    if u and u.get("activos"):
        try:
            edad = ahora - datetime.fromisoformat(u["creado"])
        except Exception:
            edad = timedelta(days=99)
        n = len(u["activos"])
        if edad < timedelta(days=7) and not (n < 300 and edad > timedelta(days=1)):
            return u["activos"]
    activos, diag = construir_universo()
    ok = gh_escribir("universo.json", {"creado": ahora.isoformat(), "activos": activos})
    n_etf = sum(1 for d in activos.values() if d["t"] == "ETF")
    if ok:
        telegram(f"🧭 Universo de Tradia actualizado\nTotal: {len(activos)} activos ({len(activos) - n_etf} acciones, {n_etf} ETFs)\n" + "\n".join(diag))
    else:
        telegram("⚠️ Tradia: no se pudo guardar la lista de activos (universo.json). Revisa el repositorio o el token GH_TOKEN.")
    return activos

# ---------- Datos de mercado ----------
def descargar(tickers, presupuesto_seg):
    datos, inicio = {}, time.time()
    for i in range(0, len(tickers), 100):
        if time.time() - inicio > presupuesto_seg:
            print("Presupuesto de tiempo agotado en el lote", i)
            break
        lote = tickers[i:i + 100]
        df = None
        for _ in range(2):
            try:
                df = yf.download(lote, period="1y", interval="1d", group_by="ticker",
                                 auto_adjust=True, threads=True, progress=False)
                break
            except Exception as e:
                print("Error descarga", str(e)[:100])
                time.sleep(5)
        if df is None or df.empty:
            continue
        if isinstance(df.columns, pd.MultiIndex):
            nivel = set(df.columns.get_level_values(0))
            for t in lote:
                if t in nivel:
                    sub = df[t].dropna(how="all")
                    if len(sub) >= 60:
                        datos[t] = sub
        elif len(lote) == 1:
            sub = df.dropna(how="all")
            if len(sub) >= 60:
                datos[lote[0]] = sub
    return datos

def indicadores(df):
    if "Close" not in df:
        return None
    c = pd.to_numeric(df["Close"], errors="coerce").dropna()
    if len(c) < 60 or c.iloc[-1] <= 0:
        return None
    if "Volume" in df:
        v = pd.to_numeric(df["Volume"], errors="coerce").reindex(c.index).fillna(0)
    else:
        v = pd.Series(0.0, index=c.index)
    precio = float(c.iloc[-1])
    d = c.diff()
    g = float(d.clip(lower=0).rolling(14).mean().iloc[-1])
    l = float((-d.clip(upper=0)).rolling(14).mean().iloc[-1])
    if np.isnan(g) or np.isnan(l):
        return None
    rsi = (100.0 if g > 0 else 50.0) if l == 0 else 100 - 100 / (1 + g / l)
    macd = c.ewm(span=12, adjust=False).mean() - c.ewm(span=26, adjust=False).mean()
    hist = macd - macd.ewm(span=9, adjust=False).mean()
    m20 = float(c.rolling(20).mean().iloc[-1])
    m50 = float(c.rolling(50).mean().iloc[-1])
    m200 = float(c.rolling(200).mean().iloc[-1]) if len(c) >= 200 else None
    desv = float(c.rolling(20).std().iloc[-1])
    if np.isnan(m20) or np.isnan(m50) or np.isnan(desv):
        return None
    vol_med = float(v.rolling(20).mean().iloc[-1])
    vol_ratio = float(v.iloc[-1] / vol_med) if vol_med > 0 else 1.0
    valor = float((c * v).tail(20).mean()) if float(v.sum()) > 0 else None
    vola = float(c.pct_change().tail(63).std() * np.sqrt(252))
    return {
        "precio": round(precio, 2), "rsi": round(float(rsi), 1),
        "macd_pos": bool(hist.iloc[-1] > 0), "macd_gira": bool(hist.iloc[-1] > hist.iloc[-2]),
        "alcista": m20 > m50,
        "sobre200": (precio > m200) if m200 is not None else (precio > m50),
        "m50_sobre_m200": (m50 > m200) if m200 is not None else False,
        "en_soporte": precio <= (m20 - 2 * desv) * 1.02,
        "en_resistencia": precio >= (m20 + 2 * desv) * 0.98,
        "vol_ratio": vol_ratio,
        "ret5": float(precio / c.iloc[-6] - 1),
        "ret126": float(precio / c.iloc[-127] - 1) if len(c) > 127 else None,
        "vola": None if np.isnan(vola) else vola,
        "liq_baja": (valor is not None and valor < 100000),
    }

def puntos(i):
    sc, mc, sl, ml, sv, mv = 0, [], 0, [], 0, []
    r = i["rsi"]
    if r < 30: sc += 35; mc.append("RSI sobrevendido")
    elif r < 40: sc += 20; mc.append("RSI bajo")
    elif r < 45: sc += 10; mc.append("RSI algo bajo")
    if i["en_soporte"]: sc += 25; mc.append("en soporte (banda de Bollinger inferior)")
    if i["macd_gira"]: sc += 15; mc.append("MACD recuperando")
    if i["vol_ratio"] > 1.5: sc += 10; mc.append("volumen alto")
    if i["ret5"] < -0.03: sc += 10; mc.append(f"caída reciente de {abs(i['ret5']) * 100:.0f}% en 5 días")
    if i["sobre200"]: sc += 5; mc.append("sobre su media de 200 días")
    if i["alcista"]: sl += 20; ml.append("tendencia alcista (media 20 > media 50)")
    if i["sobre200"]: sl += 20; ml.append("sobre su media de 200 días")
    if i["m50_sobre_m200"]: sl += 10; ml.append("media 50 sobre media 200")
    if i["ret126"] is not None and i["ret126"] > 0: sl += 10; ml.append("sube en 6 meses")
    if 40 <= r <= 70: sl += 10; ml.append("RSI sano")
    if i["vola"] is not None and i["vola"] < 0.35: sl += 10; ml.append("volatilidad baja")
    if not i["alcista"]: sv += 20; mv.append("tendencia bajista")
    if not i["macd_pos"]: sv += 10; mv.append("MACD negativo")
    if r > 70: sv += 25; mv.append("RSI sobrecomprado")
    elif r > 60: sv += 10; mv.append("RSI elevado")
    if i["en_resistencia"]: sv += 10; mv.append("en resistencia (banda de Bollinger superior)")
    if not i["sobre200"]: sv += 5; mv.append("bajo su media de 200 días")
    return {"corto": sc, "largo": sl, "venta": sv, "mc": mc, "ml": ml, "mv": mv}

def clamp(x):
    # Nunca se muestra 100%: en bolsa nada es seguro al 100%, ni la mejor señal.
    return int(max(0, min(95, round(x))))

def rec_plazo(corto, largo):
    if max(corto, largo) < 50: return "sin señal clara"
    if corto >= largo + 10: return "corto plazo"
    if largo >= corto + 10: return "largo plazo"
    return "ambos plazos"

def rec_importe(score, liq_baja):
    if liq_baja:
        return "menos de 50 € (poca liquidez)" if score >= 55 else "no recomendado"
    if score >= 85: return "250–400 €"
    if score >= 70: return "100–250 €"
    if score >= 55: return "50–100 €"
    if score >= 40: return "menos de 50 €"
    return "no recomendado"

def fundamental(ticker):
    try:
        info = yf.Ticker(ticker).info
        per, margen = info.get("trailingPE"), info.get("profitMargins")
        crec, deuda = info.get("revenueGrowth"), info.get("debtToEquity")
        pts, mot = 0, []
        if per and 5 < per < 20: pts += 15; mot.append(f"PER atractivo ({per:.1f})")
        elif per and per > 40: pts -= 10
        if margen and margen > 0.10: pts += 10; mot.append(f"margen {margen * 100:.1f}%")
        if crec and crec > 0.05: pts += 10; mot.append("ingresos creciendo")
        if deuda and deuda < 50: pts += 5; mot.append("deuda controlada")
        return max(0, min(30, pts)), mot
    except Exception:
        return 0, []

def noticias(nombre):
    try:
        url = f"https://news.google.com/rss/search?q={quote_plus(nombre + ' bolsa')}&hl=es&gl=ES&ceid=ES:es"
        feed = feedparser.parse(url)
        pts, tit = 0, []
        for e in feed.entries[:8]:
            t = e.get("title", "")
            pos, neg = len(RE_POS.findall(t)), len(RE_NEG.findall(t))
            if pos > neg: pts += 5; tit.append("✅ " + t[:70])
            elif neg > pos: pts -= 8; tit.append("⚠️ " + t[:70])
        return max(-30, min(20, pts)), tit[:1]
    except Exception:
        return 0, []

def armar(ticker, info_u, i, p, fp, fm, np_, nt, completo):
    corto = clamp(p["corto"] + np_)
    largo = clamp(p["largo"] + fp + np_)
    venta = clamp(p["venta"] + (abs(np_) if np_ < 0 else 0))
    compra = max(corto, largo)
    sig_c = list(p["mc"] if corto >= largo else p["ml"] + fm)[:5]
    if np_ > 0: sig_c.append("noticias positivas")
    sig_v = list(p["mv"])[:4] + (["noticias negativas"] if np_ < 0 else [])
    return {
        "nombre": info_u["n"], "ticker": ticker, "tipo": info_u["t"], "precio": i["precio"],
        "compra": compra, "corto": corto, "largo": largo, "venta": venta,
        "rec_plazo": rec_plazo(corto, largo), "rec_importe": rec_importe(compra, i["liq_baja"]),
        "señales_compra": sig_c, "señales_venta": sig_v, "noticias": nt[:1], "rsi": i["rsi"],
        "sector": SECTOR_TICKER.get(ticker, "otros"), "liquidez_baja": i["liq_baja"], "completo": completo,
    }

# ---------- Avisos ----------
def bloque_compra(r):
    t = (f"🟢 COMPRA: {r['nombre']} ({r['precio']:.2f} €)\n"
         f"Índice de confianza: {r['compra']}% · ⚡ corto {r['corto']}% · 📅 largo {r['largo']}%\n"
         f"Recomendado: {r['rec_plazo']}\n"
         f"Importe orientativo: {r['rec_importe']}\n"
         f"Señales: {', '.join(r['señales_compra'][:3])}\nRSI: {r['rsi']}")
    if r["liquidez_baja"]: t += "\n⚠️ Poca liquidez: puede costar entrar o salir"
    if r["noticias"]: t += "\n" + r["noticias"][0]
    return t

def bloque_venta(r):
    t = (f"🔴 VENTA (en tu cartera): {r['nombre']} ({r['precio']:.2f} €)\n"
         f"Índice de venta: {r['venta']}%\n"
         f"Señales: {', '.join(r['señales_venta'][:3])}\nRSI: {r['rsi']}")
    if r["noticias"]: t += "\n" + r["noticias"][0]
    return t

def decidir_avisos(resultados, cartera, estado):
    """Sin límite de avisos: toda señal nueva (o que cambie de compra a venta
    o viceversa) se avisa. La única excepción es la primerísima vez que el
    robot trabaja con el universo completo: ese arranque se registra en
    silencio para no mandar de golpe miles de avisos que no son reales
    cambios, solo el primer cálculo."""
    previos = estado.get("avisados", {})
    arrancado = bool(estado.get("universo_completo_inicializado"))
    cand, sec_count = [], {}
    for r in sorted(resultados, key=lambda x: -x["compra"]):
        if r["completo"] and r["compra"] >= 70:
            s = r["sector"]
            if s != "otros":
                if sec_count.get(s, 0) >= 2:
                    continue
                sec_count[s] = sec_count.get(s, 0) + 1
            cand.append((r, "compra"))
    ventas = [(r, "venta") for r in resultados if r["ticker"] in cartera and r["venta"] >= 55]
    cand = sorted(ventas, key=lambda x: -x[0]["venta"]) + cand
    nuevos, actuales = [], {}
    for r, tipo in cand:
        actuales[r["ticker"]] = tipo
        if arrancado and previos.get(r["ticker"]) != tipo:
            nuevos.append((r, tipo))
    analizados = {r["ticker"] for r in resultados}
    for t, tipo in previos.items():
        if t not in analizados:
            actuales[t] = tipo
    return nuevos, actuales, arrancado

def avisar_si_retraso(umbral_min=50):
    """Si resultados.json lleva más de 'umbral_min' minutos sin actualizarse
    (en horario de mercado, donde el robot debería correr cada 20-30 min),
    manda un único aviso por Telegram. No repite el aviso en cada ejecución:
    solo cuando el retraso cruza el umbral por primera vez."""
    prev = gh_leer("resultados.json")
    if not prev or "actualizado" not in prev:
        return
    try:
        ultimo = datetime.strptime(prev["actualizado"], "%Y-%m-%d %H:%M UTC").replace(tzinfo=timezone.utc)
    except Exception:
        return
    minutos = (datetime.now(timezone.utc) - ultimo).total_seconds() / 60
    estado = gh_leer("estado.json") or {}
    if minutos > umbral_min and not estado.get("aviso_retraso_enviado"):
        telegram(f"🕐 Tradia lleva {int(minutos)} minutos sin actualizarse. "
                 "Puede que GitHub haya retrasado o saltado alguna ejecución programada; "
                 "revisa la pestaña Actions del repositorio si continúa así.")
        estado["aviso_retraso_enviado"] = True
        gh_escribir("estado.json", estado)
    elif minutos <= umbral_min and estado.get("aviso_retraso_enviado"):
        estado["aviso_retraso_enviado"] = False
        gh_escribir("estado.json", estado)

def main():
    t0 = time.time()
    avisar_si_retraso()
    universo = cargar_universo()

    tickers = list(universo.keys())
    cartera = set((gh_leer("cartera.json") or {}).get("tickers", []))
    print(f"Universo: {len(tickers)} activos. Cartera: {len(cartera)}")
    datos = descargar(tickers, 20 * 60)
    print(f"Con datos: {len(datos)} de {len(tickers)} ({time.time() - t0:.0f}s)")
    ahora_utc = pd.Timestamp.now("UTC").tz_localize(None)
    tmp = []
    for t, df in datos.items():
        try:
            idx = pd.DatetimeIndex(df.index)
            if idx.tz is not None:
                idx = idx.tz_convert(None)
            if (ahora_utc - idx[-1]).days > 10:
                continue
            i = indicadores(df)
            if i is None:
                continue
            tmp.append((t, universo[t], i, puntos(i)))
        except Exception as e:
            print("Error", t, str(e)[:80])
    acc = [x for x in tmp if x[1]["t"] == "acción"]
    cand = {x[0] for x in sorted(acc, key=lambda x: -max(x[3]["corto"], x[3]["largo"]))[:50]}
    cand |= {x[0] for x in sorted(acc, key=lambda x: -x[3]["venta"])[:20]}
    cand |= cartera
    resultados = []
    for t, iu, i, p in tmp:
        fp, fm, np_, nt, completo = 0, [], 0, [], iu["t"] == "ETF"
        if iu["t"] == "acción" and t in cand:
            fp, fm = fundamental(t)
            np_, nt = noticias(iu["n"])
            completo = True
        resultados.append(armar(t, iu, i, p, fp, fm, np_, nt, completo))
    resultados.sort(key=lambda r: -r["compra"])
    ok_resultados = gh_escribir("resultados.json", {
        "actualizado": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "total_analizados": len(resultados), "universo_total": len(tickers),
        "resultados": resultados})
    if not ok_resultados:
        telegram("⚠️ Tradia: no se pudo guardar resultados.json en esta ejecución. La app puede estar mostrando datos antiguos.")
    estado = gh_leer("estado.json") or {}
    nuevos, actuales, ya_arrancado = decidir_avisos(resultados, cartera, estado)
    if not ya_arrancado:
        telegram("🚀 Tradia ha arrancado con el universo completo de activos.\n"
                 f"Se han detectado {len(actuales)} señales activas en este primer análisis "
                 "(no te las mando una a una para no saturarte).\n"
                 "A partir de ahora, toda señal nueva o que cambie te llegará sin ningún límite.")
    elif nuevos:
        nuevos_venta = [(r, tipo) for r, tipo in nuevos if tipo == "venta"]
        if nuevos_venta:
            bloques = [bloque_venta(r) for r, tipo in nuevos_venta]
            telegram(f"⚠️ Tradia — {len(nuevos_venta)} señal(es) de venta nueva(s)\n\n" + "\n\n".join(bloques))
    gh_escribir("estado.json", {"universo_completo_inicializado": True,
                                "avisados": actuales,
                                "actualizado": datetime.now(timezone.utc).isoformat()})
    print(f"Listo en {time.time() - t0:.0f}s. Analizados: {len(resultados)}. Avisos nuevos: {len(nuevos)}")

if __name__ == "__main__":
    main()
