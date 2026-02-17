import streamlit as st
import pandas as pd
import yfinance as yf
import numpy as np
from datetime import datetime
import pytz

# --- KONFIGURATION ---
st.set_page_config(page_title="V9.2 Elite Terminal", layout="wide")
cet = pytz.timezone('Europe/Berlin')
now = datetime.now(cet)

# Mapping für leserliche Namen
ASSET_NAMES = {
    "SAP.DE": "SAP (Software)",
    "MUV2.DE": "Münchener Rück",
    "ALV.DE": "Allianz SE",
    "SIE.DE": "Siemens",
    "ENR.DE": "Siemens Energy",
    "TSLA": "Tesla Inc.",
    "NVDA": "NVIDIA Corp.",
    "^GDAXI": "DAX Index",
    "^VIX": "VIX Angst-Index"
}

if 'capital' not in st.session_state: 
    st.session_state.capital = 3836.29

# --- DATA ENGINE ---
def get_vix_level():
    try:
        vix_data = yf.download("^VIX", period="1d", interval="1m", progress=False)
        if not vix_data.empty:
            val = vix_data['Close'].iloc[-1]
            return float(val.iloc[0]) if isinstance(val, pd.Series) else float(val)
    except: pass
    return 20.0

def get_index_performance():
    try:
        dax = yf.download("^GDAXI", period="2d", interval="15m", progress=False)
        if not dax.empty:
            c_now = dax['Close'].iloc[-1]
            c_prev = dax['Close'].iloc[-2]
            val_now = float(c_now.iloc[0]) if isinstance(c_now, pd.Series) else float(c_now)
            val_prev = float(c_prev.iloc[0]) if isinstance(c_prev, pd.Series) else float(c_prev)
            return ((val_now / val_prev) - 1) * 100
    except: pass
    return 0.0

def calculate_hps(ticker, current_vix, index_perf):
    try:
        stock = yf.download(ticker, period="2d", interval="15m", progress=False)
        if stock.empty: return 0, 0, {}
        
        p_now = float(stock['Close'].iloc[-1].iloc[0]) if isinstance(stock['Close'].iloc[-1], pd.Series) else float(stock['Close'].iloc[-1])
        p_prev = float(stock['Close'].iloc[-2].iloc[0]) if isinstance(stock['Close'].iloc[-2], pd.Series) else float(stock['Close'].iloc[-2])
        d_high = float(stock['High'].iloc[-1].iloc[0]) if isinstance(stock['High'].iloc[-1], pd.Series) else float(stock['High'].iloc[-1])
        d_low = float(stock['Low'].iloc[-1].iloc[0]) if isinstance(stock['Low'].iloc[-1], pd.Series) else float(stock['Low'].iloc[-1])

        stock_perf = ((p_now / p_prev) - 1) * 100
        score = 0
        
        vix_ok = current_vix <= 22
        if vix_ok: score += 20
        
        is_lunch = (now.hour == 11 and now.minute >= 30) or (now.hour == 12) or (now.hour == 13 and now.minute < 30)
        timing_ok = not is_lunch
        if timing_ok: score += 20
        
        rsx_ok = (stock_perf - index_perf) > 0
        if rsx_ok: score += 30
        
        sm_ratio = (p_now - d_low) / (d_high - d_low) if d_high != d_low else 0.5
        sm_ok = sm_ratio > 0.7
        if sm_ok: score += 30
        
        return score, p_now, {"RSX": rsx_ok, "VIX": vix_ok, "Time": timing_ok}
    except: return 0, 0, {}

# --- UI ---
st.title("⚡ MASTER-DASHBOARD 9.0 ULTRA-ELITE")

st.sidebar.header("Kommando-Zentrale")
input_cap = st.sidebar.text_input("Kapital anpassen", value=str(st.session_state.capital))
if st.sidebar.button("Speichern"):
    st.session_state.capital = float(input_cap)

st.sidebar.divider()
st.sidebar.metric("Kapitalbasis", f"{st.session_state.capital:,.2f} €")
st.sidebar.write(f"Status: **{'⌛ MITTAGSPAUSE' if (11 <= now.hour < 13) else '🚀 HANDELSAKTIV'}**")

if st.button("DASHBOARD AKTUELL"):
    vix = get_vix_level()
    idx_p = get_index_performance()
    
    watchlist = ["SAP.DE", "MUV2.DE", "ALV.DE", "SIE.DE", "ENR.DE", "TSLA", "NVDA"]
    results = []
    
    for t in watchlist:
        score, price, f = calculate_hps(t, vix, idx_p)
        if score > 0:
            risk = st.session_state.capital * 0.01
            qty = risk / (price * 0.015) if price > 0 else 0
            
            # Hier war der Fehler - jetzt sicher verpackt:
            results.append({
                "Asset": ASSET_NAMES.get(t, t),
                "HPS-Score": f"{score}%",
                "Preis": f"{price:.2f} €",
                "Stärke": "🔥 Stark" if f.get('RSX') else "❄️ Schwach",
                "VIX": "✅" if f.get('VIX') else "⚠️",
                "Timing": "✅" if f.get('Time') else "⏳",
                "Stück": int(qty)
            })
    
    if results:
        df = pd.DataFrame(results).sort_values(by="HPS-Score", ascending=False)
        st.table(df)
        st.caption(f"Marktdaten: VIX {vix:.2f} | DAX: {idx_p:+.2f}%")
