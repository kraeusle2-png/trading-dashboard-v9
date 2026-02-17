import streamlit as st
import pandas as pd
import yfinance as yf
import numpy as np
from datetime import datetime
import pytz

# --- KONFIGURATION & SETUP ---
st.set_page_config(page_title="V9.8 Safe-Guard Elite", layout="wide")
cet = pytz.timezone('Europe/Berlin')
now = datetime.now(cet)

# Mapping für Assets
ASSET_NAMES = {
    "SAP.DE": "SAP", "MUV2.DE": "Münchener Rück", "ALV.DE": "Allianz", "SIE.DE": "Siemens", "ENR.DE": "Siemens Energy",
    "AAPL": "Apple", "MSFT": "Microsoft", "NVDA": "NVIDIA", "AMZN": "Amazon", "GOOGL": "Alphabet",
    "TSLA": "Tesla", "META": "Meta", "AVGO": "Broadcom", "COST": "Costco", "NFLX": "Netflix",
    "ASML": "ASML", "AMD": "AMD", "V": "Visa"
}

WATCHLISTS = {
    "DAX (Bluechips)": ["SAP.DE", "MUV2.DE", "ALV.DE", "SIE.DE", "ENR.DE"],
    "S&P 500 (Leaders)": ["AAPL", "MSFT", "AMZN", "GOOGL", "META", "V"],
    "Nasdaq 100 (Tech)": ["NVDA", "TSLA", "AVGO", "COST", "NFLX", "ASML", "AMD"]
}

INDEX_TICKERS = {
    "DAX (Bluechips)": "^GDAXI",
    "S&P 500 (Leaders)": "^GSPC",
    "Nasdaq 100 (Tech)": "^IXIC"
}

if 'capital' not in st.session_state: 
    st.session_state.capital = 3836.29

# --- CORE ENGINE (DOUBLE CHECK LOGIC) ---
def get_safe_value(data_point):
    """Extrahiert einen Float-Wert, egal ob Series oder Scalar."""
    if isinstance(data_point, pd.Series):
        return float(data_point.iloc[0])
    return float(data_point)

def get_vix_level():
    try:
        vix_data = yf.download("^VIX", period="1d", interval="1m", progress=False)
        if not vix_data.empty:
            return get_safe_value(vix_data['Close'].iloc[-1])
    except: pass
    return 20.0

def get_index_performance(index_name):
    try:
        ticker = INDEX_TICKERS.get(index_name, "^GDAXI")
        idx_data = yf.download(ticker, period="2d", interval="15m", progress=False)
        if not idx_data.empty:
            c_now = get_safe_value(idx_data['Close'].iloc[-1])
            c_prev = get_safe_value(idx_data['Close'].iloc[-2])
            return ((c_now / c_prev) - 1) * 100
    except: pass
    return 0.0

def calculate_hps_validated(ticker, current_vix, index_perf):
    try:
        # 1. Datenabruf (2 Tage für Trend-Check)
        stock = yf.download(ticker, period="2d", interval="15m", progress=False)
        if len(stock) < 3: return 0, 0, {"Status": "Datenlücke"}
        
        # 2. Kurswerte extrahieren
        p_now = get_safe_value(stock['Close'].iloc[-1])
        p_prev = get_safe_value(stock['Close'].iloc[-2])
        p_old = get_safe_value(stock['Close'].iloc[-3])
        d_high = get_safe_value(stock['High'].iloc[-1])
        d_low = get_safe_value(stock['Low'].iloc[-1])

        # 3. DOPPELTE PRÜFUNG (PLAUSIBILITÄT)
        perf_15m = (p_now / p_prev) - 1
        if abs(perf_15m) > 0.10: # Ausreißer-Schutz (10% in 15 Min)
            return 0, p_now, {"Status": "Vola-Check Fehlgeschlagen"}

        score = 0
        checks = {}

        # KRITERIUM 1: VIX Guard (20 Pkt)
        checks['VIX'] = current_vix <= 22.5
        if checks['VIX']: score += 20
        
        # KRITERIUM 2: RSX Trend-Validierung (30 Pkt)
        rsx_now = (perf_15m * 100) - index_perf
        rsx_prev_perf = ((p_prev / p_old) - 1) * 100
        rsx_prev = rsx_prev_perf - index_perf
        # Validierung: Aktuelle Stärke muss da sein UND der Trend darf nicht kippen
        checks['RSX'] = rsx_now > 0 and (rsx_now + rsx_prev) > -0.1
        if checks['RSX']: score += 30
        
        # KRITERIUM 3: Smart Money (30 Pkt)
        sm_ratio = (p_now - d_low) / (d_high - d_low) if d_high != d_low else 0.5
        checks['SM'] = sm_ratio > 0.72 # Verschärfter Schwellenwert
        if checks['SM']: score += 30
        
        # KRITERIUM 4: Timing (20 Pkt)
        is_lunch = (now.hour == 11 and now.minute >= 30) or (now.hour == 12) or (now.hour == 13 and now.minute < 30)
        checks['Time'] = not is_lunch
        if checks['Time']: score += 20

        return score, p_now, checks
    except:
        return 0, 0, {"Status": "Fehler"}

# --- BENUTZEROBERFLÄCHE (UI) ---
st.title("⚡ MASTER-DASHBOARD 9.8 SAFE-GUARD ELITE")

st.sidebar.header("Kommando-Zentrale")
input_cap = st.sidebar.text_input("Trading-Kapital", value=str(st.session_state.capital))
if st.sidebar.button("Kapital Aktualisieren"):
    st.session_state.capital = float(input_cap)

st.sidebar.divider()
selected_market = st.sidebar.selectbox("Markt-Segment wählen", list(WATCHLISTS.keys()))

st.sidebar.metric("Verfügbares Kapital", f"{st.session_state.capital:,.2f} €")
st.sidebar.write(f"Markt-Phase: **{'⌛ PAUSE (LUNCH)' if (11 <= now.hour < 13) else '🚀 HANDELSAKTIV'}**")

if st.button(f"Sicherheits-Scan: {selected_market}"):
    vix = get_vix_level()
    idx_p = get_index_performance(selected_market)
    
    results = []
    with st.spinner(f'Führe doppelte Prüfung für {selected_market} durch...'):
        for t in WATCHLISTS[selected_market]:
            score, price, c = calculate_hps_validated(t, vix, idx_p)
            
            # Nur Scores über 0 werden angezeigt
            if score > 0:
                risk_amount = st.session_state.capital * 0.01
                stop_dist = price * 0.015
                qty = risk_amount / stop_dist if stop_dist > 0 else 0
                
                results.append({
                    "Asset": ASSET_NAMES.get(t, t),
                    "HPS-Score": f"{score}%",
                    "Kurs": f"{price:.2f}",
                    "RSX (V)": "✅" if c.get('RSX') else "❌",
                    "VIX": "✅" if c.get('VIX') else "⚠️",
                    "SM": "✅" if c.get('SM') else "➖",
                    "Timing": "✅" if c.get('Time') else "⏳",
                    "Stückzahl": int(qty)
                })
    
    if results:
        df = pd.DataFrame(results).sort_values(by="HPS-Score", ascending=False)
        st.table(df)
        st.success(f"Validierung abgeschlossen. VIX: {vix:.2f} | Index-Perf: {idx_p:+.2f}%")
    else:
        st.warning("Keine Titel erfüllen die Sicherheits-Kriterien für einen Score > 0.")

st.sidebar.divider()
st.sidebar.info("V9.8 nutzt 15m Echtzeit-Intervalle und einen doppelten RSX-Trend-Check.")
