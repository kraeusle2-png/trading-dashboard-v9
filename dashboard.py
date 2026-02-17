import streamlit as st
import pandas as pd
import yfinance as yf
import numpy as np
from datetime import datetime
import pytz

# --- SETUP ---
st.set_page_config(page_title="Master-Dashboard 9.0", layout="wide")

if 'capital' not in st.session_state: st.session_state.capital = 3836.29
if 'hps_threshold' not in st.session_state: st.session_state.hps_threshold = 90.0

cet = pytz.timezone('Europe/Berlin')
now = datetime.now(cet)

# --- ENGINE ---
def run_sniper_flow(ticker, vix_val):
    # Einfache Logik, die nicht abstürzen kann
    score = np.random.randint(85, 98) # Simulation für den ersten Start
    price = 100.0
    try:
        data = yf.Ticker(ticker).history(period="1d")
        if not data.empty:
            price = data['Close'].iloc[-1]
    except: pass
    
    return score, price

# --- UI ---
st.title("⚡ MASTER-DASHBOARD 9.0 ULTRA-ELITE")

# Sidebar für Befehle
cmd = st.sidebar.text_input("Befehl eingeben", "")
if "Kapital" in cmd:
    try:
        st.session_state.capital = float(cmd.split(" ")[1])
    except: pass

st.sidebar.metric("Kapital", f"{st.session_state.capital:,.2f} €")

if st.button("DASHBOARD AKTUELL"):
    st.write(f"Scan läuft... Stand: {now.strftime('%H:%M:%S')} CET")
    
    watchlist = ["SAP.DE", "MUV2.DE", "ENR.DE", "SIE.DE", "ALV.DE"]
    results = []
    
    for t in watchlist:
        score, price = run_sniper_flow(t, 20.0)
        if score >= st.session_state.hps_threshold:
            risk = st.session_state.capital * 0.01
            qty = risk / (price * 0.015) if price > 0 else 0
            
            results.append({
                "Asset": t,
                "Score": f"{score}%",
                "Preis": f"{price:.2f} €",
                "Stückzahl": int(qty)
            })
    
    if results:
        st.table(pd.DataFrame(results))
    else:
        st.info("Suche läuft oder Schwelle zu hoch.")
