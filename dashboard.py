import streamlit as st
import pandas as pd
import yfinance as yf
import numpy as np
from datetime import datetime
import pytz

# --- KONFIGURATION ---
st.set_page_config(page_title="V9.2 Ultra-Elite Engine", layout="wide")
cet = pytz.timezone('Europe/Berlin')
now = datetime.now(cet)

if 'capital' not in st.session_state: st.session_state.capital = 3836.29
if 'hps_threshold' not in st.session_state: st.session_state.hps_threshold = 90.0

# --- DATA ENGINE ---
def get_vix_level():
    try:
        vix = yf.download("^VIX", period="1d", interval="1m", progress=False)
        return vix['Close'].iloc[-1]
    except: return 20.0

def get_index_performance():
    try:
        dax = yf.download("^GDAXI", period="2d", interval="15m", progress=False)
        return ((dax['Close'].iloc[-1] / dax['Close'].iloc[-2]) - 1) * 100
    except: return 0.0

def calculate_hps(ticker, current_vix, index_perf):
    score = 0
    filters = {}
    
    # 1. Kursdaten laden
    stock = yf.download(ticker, period="2d", interval="15m", progress=False)
    if stock.empty: return 0, 0, {"Error": "No Data"}
    
    price = stock['Close'].iloc[-1]
    stock_perf = ((price / stock['Close'].iloc[-2]) - 1) * 100
    
    # FILTER 1: VIX-Guard (20 Punkte)
    filters['VIX-Safe'] = current_vix <= 22
    if filters['VIX-Safe']: score += 20
    
    # FILTER 2: Timing (20 Punkte) - Mittagspause 11:30-13:30
    is_lunch = (now.hour == 11 and now.minute >= 30) or (now.hour == 12) or (now.hour == 13 and now.minute < 30)
    filters['Timing-OK'] = not is_lunch
    if filters['Timing-OK']: score += 20
    
    # FILTER 3: RSX (Relative Stärke) (30 Punkte)
    rsx = stock_perf - index_perf
    filters['RSX-Strong'] = rsx > 0
    if filters['RSX-Strong']: score += 30
    
    # FILTER 4: Smart-Money (Körper-Range Proxy) (30 Punkte)
    # Simuliert: Schaut ob Schlusskurs nahe Tageshoch
    day_high = stock['High'].iloc[-1]
    day_low = stock['Low'].iloc[-1]
    sm_ratio = (price - day_low) / (day_high - day_low) if day_high != day_low else 0.5
    filters['Smart-Money'] = sm_ratio > 0.7
    if filters['Smart-Money']: score += 30
    
    return score, price, filters

# --- UI ---
st.title("⚡ MASTER-DASHBOARD 9.0 ULTRA-ELITE")

# Sidebar
st.sidebar.header("Engine Control")
cmd = st.sidebar.text_input("Befehl", "Kapital 3836.29")
if "Kapital" in cmd:
    st.session_state.capital = float(cmd.split(" ")[-1])

st.sidebar.metric("Kapitalbasis", f"{st.session_state.capital:,.2f} €")
st.sidebar.write(f"V9.2 Status: **{'PAUSE (Lunch)' if (11 <= now.hour < 13) else 'ACTIVE'}**")

if st.button("DASHBOARD AKTUELL"):
    with st.spinner('Berechne HPS-Elite Scores...'):
        vix = get_vix_level()
        idx_p = get_index_performance()
        
        # Watchlist (DAX & US Auswahl)
        watchlist = ["SAP.DE", "MUV2.DE", "ALV.DE", "SIE.DE", "ENR.DE", "TSLA", "NVDA"]
        results = []
        
        for t in watchlist:
            score, price, f = calculate_hps(t, vix, idx_p)
            
            if score >= st.session_state.hps_threshold or t in ["SAP.DE", "MUV2.DE"]:
                # Risiko 1%
                risk = st.session_state.capital * 0.01
                sl_dist = price * 0.015 # 1.5% Stop-Loss
                qty = risk / sl_dist if sl_dist > 0 else 0
                
                results.append({
                    "Asset": t,
                    "Score": f"{score}%",
                    "Preis": f"{price:.2f}",
                    "RSX": "Strong" if f.get('RSX-Strong') else "Weak",
                    "VIX-Guard": "✅" if f.get('VIX-Safe') else "❌",
                    "Timing": "✅" if f.get('Timing-OK') else "⌛ PAUSE",
                    "Qty": int(qty)
                })
        
        if results:
            df = pd.DataFrame(results).sort_values(by="Score", ascending=False)
            st.table(df)
            st.info(f"VIX: {vix:.2f} | DAX Perf: {idx_p:.2f}%")
