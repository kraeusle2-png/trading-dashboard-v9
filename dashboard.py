import streamlit as st
import pandas as pd
import yfinance as yf
from datetime import datetime
import pytz

# --- KONFIGURATION ---
st.set_page_config(page_title="Sniper V10.8 Final", page_icon="🎯", layout="centered")
cet = pytz.timezone('Europe/Berlin')
now = datetime.now(cet)

USER_NAME = "Kraus Markus"

# Speicher für Signale (Asset -> {Zeit, Kurs})
if 'signal_log' not in st.session_state:
    st.session_state.signal_log = {}

# Falls Kapital noch nicht gesetzt ist
if 'capital' not in st.session_state: 
    st.session_state.capital = 3836.29

# --- LISTEN & NAMEN ---
ASSET_NAMES = {
    "SAP.DE": "SAP", "MUV2.DE": "Münchener Rück", "ALV.DE": "Allianz", "SIE.DE": "Siemens", "ENR.DE": "Siemens Energy",
    "AAPL": "Apple", "MSFT": "Microsoft", "NVDA": "NVIDIA", "AMZN": "Amazon", "GOOGL": "Alphabet",
    "TSLA": "Tesla", "META": "Meta", "AVGO": "Broadcom", "COST": "Costco", "NFLX": "Netflix",
    "ASML": "ASML", "AMD": "AMD", "V": "Visa"
}

WATCHLISTS = {
    "DAX 🇩🇪": ["SAP.DE", "MUV2.DE", "ALV.DE", "SIE.DE", "ENR.DE"],
    "S&P 500 🇺🇸": ["AAPL", "MSFT", "AMZN", "GOOGL", "META", "V"],
    "Nasdaq 🚀": ["NVDA", "TSLA", "AVGO", "COST", "NFLX", "ASML", "AMD"]
}

INDEX_TICKERS = {"DAX 🇩🇪": "^GDAXI", "S&P 500 🇺🇸": "^GSPC", "Nasdaq 🚀": "^IXIC"}

# --- HILFSFUNKTIONEN ---
def get_safe_val(dp):
    """Sicheres Auslesen von Einzelwerten aus Pandas Series"""
    return float(dp.iloc[0]) if isinstance(dp, pd.Series) else float(dp)

def calc_pro_entry(ticker, vix, idx_p, markt):
    try:
        # Lade 2 Tage Daten im 15m Intervall
        s = yf.download(ticker, period="2d", interval="15m", progress=False)
        if len(s) < 3: return None
        
        # Aktuelle Werte (letzte Kerze)
        p = get_safe_val(s['Close'].iloc[-1])
        hi = get_safe_val(s['High'].iloc[-1])
        
        # Vorherige Werte (vorletzte Kerze) - WICHTIG für Stabilen SL
        prev_p = get_safe_val(s['Close'].iloc[-2])
        prev_lo = get_safe_val(s['Low'].iloc[-2]) 
        
        checks = {}
        score = 0
        
        # 1. VIX Check
        checks['VIX'] = vix <= 22.5
        if checks['VIX']: score += 20
        
        # 2. RSX Check (Momentum)
        r_now = ((p/prev_p)-1)*100 - idx_p
        checks['RSX'] = r_now > 0
        if checks['RSX']: score += 30
        
        # 3. Smart Money Check (Intraday Stärke)
        # Hier nehmen wir das aktuelle High/Low für die Kerzenform
        curr_lo = get_safe_val(s['Low'].iloc[-1])
        sm = (p - curr_lo) / (hi - curr_lo) if hi != curr_lo else 0.5
        checks['SM'] = sm > 0.72
        if checks['SM']: score += 30
        
        # 4. Timing Check
        zeit_f = now.hour + now.minute / 60.0
        if "DAX" in markt:
            checks['TIME'] = (9.25 <= zeit_f <= 11.5) or (15.75 <= zeit_f <= 17.5)
        else:
            checks['TIME'] = (15.75 <= zeit_f <= 21.0)
            
        if checks['TIME']: score += 20
        
        # --- TRADING BERECHNUNG ---
        # Einstieg: Breakout über das aktuelle Hoch
        entry = hi * 1.001 
        
        # Stop-Loss: Unter dem Tief der VORHERIGEN Kerze (Stabil!)
        sl = prev_lo * 0.995
        
        # Target: Risk Ratio 2.0
        risk = entry - sl
        if risk <= 0: risk = p * 0.01 # Fallback falls Kerzen sehr klein
        tp = entry + (risk * 2)
        
        # Status prüfen
        sl_status = "Offen"
        if p <= sl:
            sl_status = f"ERREICHT ({now.strftime('%H:%M')})"
            
        return {
            "score": score, 
            "price": p, 
            "entry": entry, 
            "sl": sl, 
            "tp": tp,
            "checks": checks, 
            "t": ticker, 
            "sl_status": sl_status
        }
    except: return None

# --- UI LAYOUT ---
st.title("🎯 SNIPER V10.8 FINAL")

with st.sidebar:
    st.header("⚙️ Einstellungen")
    
    # Kapital Eingabe
    c_in = st.text_input("Kapital (€)", value=str(st.session_state.capital))
    if st.button("Speichern"): 
        st.session_state.capital = float(c_in)
        
    # Markt Auswahl
    m_sel = st.selectbox("Markt", list(WATCHLISTS.keys()))
    
    st.metric("Verfügbar", f"{st.session_state.capital:,.2f} €")
    st.divider()
    st.caption(f"Operator: {USER_NAME}")

# --- HAUPTBEREICH ---
if st.button(f"🔍 SCAN {m_sel} STARTEN", use_container_width=True):
    
    # Marktdaten holen
    vx_d = yf.download("^VIX", period="1d", progress=False)
    v_val = get_safe_val(vx_d['Close'].iloc[-1])
    
    ix_d = yf.download(INDEX_TICKERS[m_sel], period="2d", interval="15m", progress=False)
    i_perf = ((get_safe_val(ix_d['Close'].iloc[-1]) / get_safe_val(ix_d['Close'].iloc[-2])) - 1) * 100
    
    st.info(f"Markt-Status: VIX @ {v_val:.2f} | {m_sel} Trend: {i_perf:+.2f}%")
    
    results = []
    
    # Alle Ticker scannen
    progress_bar = st.progress(0)
    total_tickers = len(WATCHLISTS[m_sel])
    
    for i, t in enumerate(WATCHLISTS[m_sel]):
        data = calc_pro_entry(t, v_val, i_perf, m_sel)
        if data:
            # Signal Logik: Nur wenn Score >= 80% UND noch nicht geloggt
            if data['score'] >= 80 and t not in st.session_state.signal_log:
                st.session_state.signal_log[t] = {
                    "time": now.strftime("%H:%M"),
                    "price": data['price']
                }
            results.append(data)
        progress_bar.progress((i + 1) / total_tickers)
        
    progress_bar.empty()
    
    # Sortierung: Höchster Score zuerst
    results = sorted(results, key=lambda x: x['score'], reverse=True)
    
    # --- ERGEBNIS ANZEIGE ---
    for item in results:
        # Berechnung der Stückzahl (Risiko-basiert oder Kapital-basiert)
        risk_per_share = item['entry'] - item['sl']
        if risk_per_share > 0:
            # Wir riskieren max 1% des Kapitals pro Trade
            qty = (st.session_state.capital * 0.01) / risk_per_share
