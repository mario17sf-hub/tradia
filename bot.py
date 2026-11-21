import os, json, requests, feedparser
from datetime import datetime
import yfinance as yf

TOKEN = os.environ["TELEGRAM_TOKEN"]
CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]
GH_TOKEN = os.environ["GH_TOKEN"]
GH_REPO = "mario17sf-hub/tradia"

ACTIVOS = {
    "Santander":"SAN.MC","BBVA":"BBVA.MC","Inditex":"ITX.MC",
    "Iberdrola":"IBE.MC","Repsol":"REP.MC","Telefónica":"TEF.MC",
    "CaixaBank":"CABK.MC","Amadeus":"AMS.MC","Ferrovial":"FER.MC",
    "ACS":"ACS.MC","Mapfre":"MAP.MC","Meliá":"MEL.MC","IAG":"IAG.MC",
    "Acciona":"ANA.MC","Red Eléctrica":"REE.MC","Enagás":"ENG.MC",
    "Endesa":"ELE.MC","Naturgy":"NTGY.MC","Grifols":"GRF.MC",
    "Bankinter":"BKT.MC","Sabadell":"SAB.MC","Colonial":"COL.MC",
    "Merlin":"MRL.MC","Fluidra":"FDR.MC","Solaria":"SLR.MC",
    "Pharma Mar":"PHM.MC","Viscofan":"VIS.MC","Vidrala":"VID.MC",
    "Logista":"LOG.MC","Unicaja":"UNI.MC","Acerinox":"ACX.MC",
    "ArcelorMittal":"MTS.MC","Cellnex":"CLNX.MC","Indra":"IDR.MC",
    "Almirall":"ALM.MC",
    "SAP":"SAP.DE","Siemens":"SIE.DE","Allianz":"ALV.DE",
    "BASF":"BAS.DE","BMW":"BMW.DE","Deutsche Bank":"DBK.DE",
    "Volkswagen":"VOW3.DE","Bayer":"BAYN.DE","Adidas":"ADS.DE",
    "Deutsche Telekom":"DTE.DE","Mercedes-Benz":"MBG.DE",
    "Rheinmetall":"RHM.DE","Infineon":"IFX.DE","Munich Re":"MUV2.DE",
    "Hannover Re":"HNR1.DE","Puma":"PUM.DE","Zalando":"ZAL.DE",
    "Vonovia":"VNA.DE","RWE":"RWE.DE","E.ON":"EOAN.DE",
    "Continental":"CON.DE","Brenntag":"BNR.DE",
    "LVMH":"MC.PA","TotalEnergies":"TTE.PA","Sanofi":"SAN.PA",
    "LOreal":"OR.PA","BNP Paribas":"BNP.PA","Airbus":"AIR.PA",
    "AXA":"CS.PA","Schneider Electric":"SU.PA","Air Liquide":"AI.PA",
    "Danone":"BN.PA","Pernod Ricard":"RI.PA","Michelin":"ML.PA",
    "Renault":"RNO.PA","Saint-Gobain":"SGO.PA","Capgemini":"CAP.PA",
    "Dassault Systemes":"DSY.PA","Kering":"KER.PA","Hermes":"RMS.PA",
    "Engie":"ENGI.PA","Societe Generale":"GLE.PA","Credit Agricole":"ACA.PA",
    "Legrand":"LR.PA","Vinci":"DG.PA","Bouygues":"EN.PA",
    "ENI":"ENI.MI","Enel":"ENEL.MI","UniCredit":"UCG.MI",
    "Intesa Sanpaolo":"ISP.MI","Generali":"G.MI","Ferrari":"RACE.MI",
    "Leonardo":"LDO.MI","Mediobanca":"MB.MI","Pirelli":"PIRC.MI",
    "Stellantis":"STLAM.MI","Prysmian":"PRY.MI","Moncler":"MONC.MI",
    "ASML":"ASML.AS","Shell":"SHEL.AS","Philips":"PHIA.AS",
    "ING":"INGA.AS","Heineken":"HEIA.AS","Wolters Kluwer":"WKL.AS",
    "NN Group":"NN.AS","IMCD":"IMCD.AS","Aegon":"AGN.AS",
    "ASM International":"ASM.AS",
    "EDP":"EDP.LS","Galp":"GALP.LS","Jerónimo Martins":"JMT.LS",
    "Sonae":"SON.LS","BCP":"BCP.LS",
    "ETF Ibex35":"BBVAI.MC","ETF EuroStoxx50":"DBXT.MI",
    "ETF DAX":"EXS1.DE","ETF Defensa EU":"ASWC.AS",
    "ETF Energía limpia":"IQQH.DE","ETF Semiconductores":"SEMI.AS",
    "ETF Dividendo EU":"EUDV.AS","ETF Oro EUR":"IGLN.AS",
}

SECTORES = {
    "banca":["Santander","BBVA","CaixaBank","Bankinter","Sabadell","Deutsche Bank",
             "BNP Paribas","UniCredit","Intesa Sanpaolo","ING","Unicaja","Mediobanca",
             "Societe Generale","Credit Agricole","BCP"],
    "energía":["Iberdrola","Repsol","Endesa","Naturgy","Enagás","Red Eléctrica",
               "TotalEnergies","ENI","Enel","Engie","Shell","Solaria","RWE","E.ON","EDP","Galp"],
    "tecnología":["SAP","Infineon","ASML","Amadeus","Capgemini",
                  "Dassault Systemes","Indra","ASM International"],
    "lujo":["LVMH","Hermes","Kering","Ferrari","Moncler","Adidas","Puma"],
    "industria":["Siemens","Airbus","Leonardo","Ferrovial","ACS",
                 "Acciona","Rheinmetall","Vinci","Prysmian"],
}

RSS_FEEDS = [
    "https://feeds.reuters.com/reuters/businessNews",
    "https://feeds.reuters.com/reuters/companyNews",
    "https://www.expansion.com/rss/mercados.xml",
]
PALABRAS_NEG = ["caída","baja","pérdida","crisis","multa","fraude","quiebra",
    "dimisión","escándalo","sanción","recesión","fall","drop","loss","fine",
    "fraud","bankrupt","resign","scandal","sanction","recession","decline","plunge"]
PALABRAS_POS = ["sube","récord","beneficio","contrato","dividendo","crecimiento",
    "expansión","fusión","positivo","rise","record","profit","deal","dividend",
    "growth","acquisition","merger","rally"]

def get_sector(nombre):
    for s,lista in SECTORES.items():
        if nombre in lista: return s
    return "otros"

def calcular_rsi(p,n=14):
    d=p.diff()
    g=d.where(d>0,0.0).rolling(n).mean()
    l=(-d.where(d<0,0.0)).rolling(n).mean()
    return round((100-(100/(1+g/l))).iloc[-1],1)

def calcular_macd(p):
    return (p.ewm(span=12).mean()-p.ewm(span=26).mean()).ewm(span=9).mean()

def analisis_tecnico(datos):
    c=datos["Close"]; v=datos["Volume"]
    rsi=calcular_rsi(c)
    macd=calcular_macd(c)
    macd_alcista=macd.iloc[-1]>0 and macd.iloc[-1]>macd.iloc[-2]
    ma20=c.rolling(20).mean().iloc[-1]
    ma50=c.rolling(50).mean().iloc[-1]
    ma200=c.rolling(200).mean().iloc[-1] if len(c)>=200 else ma50
    precio=c.iloc[-1]
    bb_m=c.rolling(20).mean(); bb_s=c.rolling(20).std()
    bb_up=(bb_m+2*bb_s).iloc[-1]; bb_lo=(bb_m-2*bb_s).iloc[-1]
    vol_med=v.rolling(20).mean().iloc[-1]
    return {
        "precio":round(precio,2),"rsi":rsi,
        "macd_alcista":macd_alcista,
        "tendencia_alcista":ma20>ma50,
        "sobre_ma200":precio>ma200,
        "volumen_alto":v.iloc[-1]>vol_med*1.5,
        "en_soporte":precio<=bb_lo*1.02,
        "en_resistencia":precio>=bb_up*0.98,
        "ma20":round(ma20,2),"ma50":round(ma50,2),
    }

def analisis_fundamental(tk):
    try:
        info=tk.info
        per=info.get("trailingPE")
        margen=info.get("profitMargins")
        crec=info.get("revenueGrowth")
        deuda=info.get("debtToEquity")
        pts=0; mot=[]
        if per and 5<per<20: pts+=15; mot.append(f"PER atractivo ({round(per,1)})")
        elif per and per>40: pts-=10
        if margen and margen>0.10: pts+=10; mot.append(f"margen {round(margen*100,1)}%")
        if crec and crec>0.05: pts+=10; mot.append("ingresos creciendo")
        if deuda and deuda<50: pts+=5; mot.append("deuda controlada")
        return max(0,min(30,pts)),mot
    except: return 0,[]

def analisis_noticias(nombre):
    pts=0; titulos=[]
    nombre_clave=nombre.lower().split()[0]
    try:
        for url in RSS_FEEDS:
            feed=feedparser.parse(url)
            for e in feed.entries[:25]:
                t=e.get("title","").lower()
                if nombre_clave in t:
                    pos=sum(1 for p in PALABRAS_POS if p in t)
                    neg=sum(1 for p in PALABRAS_NEG if p in t)
                    if pos>neg: pts+=10; titulos.append(f"✅ {e.get('title','')[:60]}")
                    elif neg>pos: pts-=15; titulos.append(f"⚠️ {e.get('title','')[:60]}")
    except: pass
    return max(-30,min(20,pts)),titulos[:2]

def calcular_indices(tec,fp,np):
    c=0; v=0; mc=[]; mv=[]
    if tec["tendencia_alcista"]: c+=20; mc.append("tendencia alcista")
    else: v+=20; mv.append("tendencia bajista")
    if tec["macd_alcista"]: c+=15; mc.append("MACD positivo")
    else: v+=10; mv.append("MACD negativo")
    rsi=tec["rsi"]
    if rsi<30: c+=25; mc.append("RSI sobrevendido")
    elif rsi<45: c+=10; mc.append("RSI bajo")
    elif rsi>70: v+=25; mv.append("RSI sobrecomprado")
    elif rsi>60: v+=10; mv.append("RSI elevado")
    if tec["en_soporte"]: c+=10; mc.append("en soporte Bollinger")
    if tec["en_resistencia"]: v+=10; mv.append("en resistencia Bollinger")
    if tec["sobre_ma200"]: c+=5; mc.append("sobre media 200")
    else: v+=5
    if tec["volumen_alto"] and tec["tendencia_alcista"]: c+=5; mc.append("volumen alto")
    if fp>0: c+=fp
    elif fp<0: v+=abs(fp)
    if np>0: c+=np; mc.append("noticias positivas")
    elif np<0: v+=abs(np); mv.append("noticias negativas")
    return min(100,c),min(100,v),mc,mv

def horizonte(tec,fp):
    corto=sum([tec["rsi"]<35,tec["en_soporte"],tec["volumen_alto"],tec["macd_alcista"]])>=2
    largo=tec["tendencia_alcista"] and tec["sobre_ma200"] and fp>=15
    return corto,largo

def guardar_resultados(data):
    url=f"https://api.github.com/repos/{GH_REPO}/contents/resultados.json"
    headers={"Authorization":f"token {GH_TOKEN}","Accept":"application/vnd.github.v3+json"}
    import base64
    contenido=base64.b64encode(json.dumps(data,ensure_ascii=False,indent=2).encode()).decode()
    r=requests.get(url,headers=headers)
    sha=r.json().get("sha") if r.status_code==200 else None
    payload={"message":"update resultados","content":contenido}
    if sha: payload["sha"]=sha
    requests.put(url,headers=headers,json=payload)

print(f"Analizando {len(ACTIVOS)} activos...")
resultados=[]; avisos=[]

for nombre,ticker_str in ACTIVOS.items():
    try:
        tk=yf.Ticker(ticker_str)
        datos=tk.history(period="12mo")
        if datos.empty or len(datos)<50: continue
        tec=analisis_tecnico(datos)
        fp,fm=analisis_fundamental(tk)
        np,nt=analisis_noticias(nombre)
        c,v,mc,mv=calcular_indices(tec,fp,np)
        c_corto,c_largo=horizonte(tec,fp)
        h=[]
        if c_corto: h.append("corto")
        if c_largo: h.append("largo")
        if not h: h.append("medio")
        rec_plazo="corto plazo" if c_corto and not c_largo else ("largo plazo" if c_largo else "medio plazo")
        resultados.append({
            "nombre":nombre,"ticker":ticker_str,"precio":tec["precio"],
            "compra":c,"venta":v,"señales_compra":mc+fm,"señales_venta":mv,
            "noticias":nt,"rsi":tec["rsi"],"ma20":tec["ma20"],"ma50":tec["ma50"],
            "horizonte":h,"rec_plazo":rec_plazo,"sector":get_sector(nombre),
            "tendencia_alcista":tec["tendencia_alcista"],
            "sobre_ma200":tec["sobre_ma200"],
        })
    except Exception as e:
        print(f"Error {nombre}: {e}")

sec_count={}
for r in sorted(resultados,key=lambda x:-x["compra"]):
    sec=r["sector"]
    if r["compra"]>=70:
        if sec_count.get(sec,0)>=2: continue
        h_txt=" | ".join(["⚡ Corto plazo" if x=="corto" else "📅 Largo plazo" for x in r["horizonte"]])
        txt=(f"🟢 COMPRA: {r['nombre']} ({r['precio']} €)\n"
             f"Índice de confianza: {r['compra']}%\n"
             f"Horizonte: {h_txt}\n"
             f"Señales: {', '.join(r['señales_compra'][:3])}\n"
             f"RSI: {r['rsi']}")
        if r["noticias"]: txt+=f"\n{r['noticias'][0]}"
        avisos.append(txt)
        sec_count[sec]=sec_count.get(sec,0)+1
    elif r["venta"]>=55:
        txt=(f"🔴 VENTA: {r['nombre']} ({r['precio']} €)\n"
             f"Índice de confianza venta: {r['venta']}%\n"
             f"Señales: {', '.join(r['señales_venta'][:3])}\n"
             f"RSI: {r['rsi']}")
        if r["noticias"]: txt+=f"\n{r['noticias'][0]}"
        avisos.append(txt)

guardar_resultados({
    "actualizado":datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC"),
    "total_analizados":len(resultados),
    "resultados":sorted(resultados,key=lambda x:-x["compra"])
})

tg_url=f"https://api.telegram.org/bot{TOKEN}/sendMessage"
for txt in avisos:
    requests.post(tg_url,data={"chat_id":CHAT_ID,"text":f"⚠️ Tradia — Señal:\n\n{txt}"})

print(f"Listo. Analizados:{len(resultados)} Avisos:{len(avisos)}")





