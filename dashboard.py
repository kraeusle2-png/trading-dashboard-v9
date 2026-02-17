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

# --- DATA ENGINE (FIXED) ---
def get_vix_level():
    try:
        vix_data = yf.download("^VIX", period="1d", interval="1m", progress=False)
        if not vix_data.empty:
            # Wir nehmen den letzten Close-Wert als Zahl (float)
            val = vix_data['Close'].iloc[-1]
            return float(val.iloc[0]) if isinstance(val, pd.Series) else float(val)
    except: pass
    return 20.0

def get_index_performance():
    try:
        dax = yf.download("^GDAXI", period="2d", interval="15m", progress=False)
        if not dax.empty:
            close_now = dax['Close'].iloc[-1]
            close_prev = dax['Close'].iloc[-2]
            # Sicherstellen, dass es Zahlen sind
            c_now = float(close_now.iloc[0]) if isinstance(close_now, pd.Series) else float(close_now)
            c_prev = float(close_prev.iloc[0]) if isinstance(close_prev, pd.Series) else float(close_prev)
            return ((c_now / c_prev) - 1) * 100
    except: pass
    return 0.0

def calculate_hps(ticker, current_vix, index_perf):
    score = 0
    filters = {}
    
    try:
        stock = yf.download(ticker, period="2d", interval="15m", progress=False)
        if stock.empty: return 0, 0, {"Error": "No Data"}
        
        # Werte sicher extrahieren
        p_now = float(stock['Close'].iloc[-1].iloc[0]) if isinstance(stock['Close'].iloc[-1], pd.Series) else float(stock['Close'].iloc[-1])
        p_prev = float(stock['Close'].iloc[-2].iloc[0]) if isinstance(stock['Close'].iloc[-2], pd.Series) else float(stock['Close'].iloc[-2])
        d_high = float(stock['High'].iloc[-1].iloc[0]) if isinstance(stock['High'].iloc[-1], pd.Series) else float(stock['High'].iloc[-1])
        d_low = float(stock['Low'].iloc[-1].iloc[0]) if isinstance(stock['Low'].iloc[-1], pd.Series) else float(stock['Low'].iloc[-1])

        stock_perf = ((p_now / p_prev) - 1) * 100
        
        # FILTER 1: VIX-Guard
        filters['VIX-Safe'] = current_vix <= 22
        if filters['VIX-Safe']: score += 20
        
        # FILTER 2: Timing
        is_lunch = (now.hour == 11 and now.minute >= 30) or (now.hour == 12) or (now.hour == 13 and now.minute < 30)
        filters['Timing-OK'] = not is_lunch
        if filters['Timing-OK']: score += 20
        
        # FILTER 3: RSX
        rsx = stock_perf - index_perf
        filters['RSX-Strong'] = rsx > 0
        if filters['RSX-Strong']: score += 30
        
        # FILTER 4: Smart-Money
        sm_ratio = (p_now - d_low) / (d_high - d_low) if d_high != d_low else 0.5
        filters['Smart-Money'] = sm_ratio > 0.7
        if filters['Smart-Money']: score += 30
        
        return score, p_now, filters
    except:
        return 0, 0, {"Error": "Calc Error"}

# --- UI ---
st.title("⚡ MASTER-DASHBOARD 9.0 ULTRA-ELITE")

st.sidebar.header("Engine Control")
cmd = st.sidebar.text_input("Befehl", f"Kapital {st.session_state.capital}")
if "Kapital" in cmd:
    try: st.session_state.capital = float(cmd.split(" ")[-1])
    except: pass

st.sidebar.metric("Kapitalbasis", f"{st.session_state.capital:,.2f} €")

if st.button("DASHBOARD AKTUELL"):
    vix = get_vix_level()
    idx_p = get_index_performance()
    
    watchlist = ["SAP.DE", "MUV2.DE", "ALV.DE", "SIE.DE", "ENR.DE", "TSLA", "NVDA"]
    results = []
    
    for t in watchlist:
        score, price, f = calculate_hps(t, vix, idx_p)
        if score > 0:
            risk = st.session_state.capital * 0.01
            sl_dist = price * 0.015
            qty = risk / sl_dist if sl_dist > 0 else 0
            
            results.append({
                "Asset": t,
                "Score": f"{score}%",
                "Preis": f"{price:.2f}",
                "RSX": "Strong" if f.get('RSX-Strong') else "Weak",
                "VIX": "✅" if f.get('VIX-Safe') else "❌",
                "Timing": "✅" if f.get('Timing-OK') else "⌛ PAUSE",
                "Stück": int(qty)
            })
    
    if results:
        st.table(pd.DataFrame(results).sort_values(by="Score", ascending=False))
        st.info(f"Markt-Daten: VIX {vix:.2f} | DAX {idx_p:+.2f}%")
