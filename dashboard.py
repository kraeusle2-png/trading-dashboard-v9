import streamlit as st
import pandas as pd
import yfinance as yf
import numpy as np
from datetime import datetime
import pytz

# --- KONFIGURATION (MOBILE OPTIMIERT) ---
st.set_page_config(page_title="Sniper V9.9 Elite", layout="centered")
cet = pytz.timezone('Europe/Berlin')
now = datetime.now(cet)

# Asset-Mapping für die Anzeige
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

INDEX_TICKERS = {
    "DAX 🇩🇪": "^GDAXI",
    "S&P 500 🇺🇸": "^GSPC",
    "Nasdaq 🚀": "^IXIC"
}

if 'capital' not in st.session_state: 
    st.session_state.capital = 3836.29

# --- HILFSFUNKTIONEN ---
def get_safe_val(dp):
    if isinstance(dp, pd.Series):
        return float(dp.iloc[0])
    return float(dp)

def get_market_context(index_name):
    try:
        vix_data = yf.download("^VIX", period="1d", progress=False)
        vix = get_safe_val(vix_data['Close'].iloc[-1])
        
        idx_ticker = INDEX_TICKERS.get(index_name, "^GDAXI")
        idx_data = yf.download(idx_ticker, period="2d", interval="15m", progress=False)
        idx_perf = ((get_safe_val(idx_data['Close'].iloc[-1]) / get_safe_val(idx_data['Close'].iloc[-2])) - 1) * 100
        return vix, idx_perf
    except:
        return 20.0, 0.0

def calculate_hps_mobile(ticker, vix, idx_perf):
    try:
        stock = yf.download(ticker, period="2d", interval="15m", progress=False)
        if len(stock) < 3: return 0, 0, {}

        p_now = get_safe_val(stock['Close'].iloc[-1])
        p_prev = get_safe_val(stock['Close'].iloc[-2])
        p_old = get_safe_val(stock['Close'].iloc[-3])
        high = get_safe_val(stock['High'].iloc[-1])
        low = get_safe_val(stock['Low'].iloc[-1])

        # Sicherheits-Check (Ausreißer)
        if abs((p_now / p_prev) - 1) > 0.10: return 0, p_now, {}

        score = 0
        checks = {}

        # 1. VIX Guard
        checks['VIX'] = vix <= 22.5
        if checks['VIX']: score += 20
        
        # 2. RSX Trend Validierung
        perf_15m = ((p_now / p_prev) - 1) * 100
        rsx_now = perf_15m - idx_perf
        rsx_prev = (((p_prev / p_old) - 1) * 100) - idx_perf
        checks['RSX'] = rsx_now > 0 and (rsx_now + rsx_prev) > -0.1
        if checks['RSX']: score += 30
        
        # 3. Smart Money Close
        sm_ratio = (p_now - low) / (high - low) if high != low else 0.5
        checks['SM'] = sm_ratio > 0.72
        if checks['SM']: score += 30
        
        # 4. Timing (Pause 11:30-13:30 CET)
        is_lunch = (now.hour == 11 and now.minute >= 30) or (now.hour == 12) or (now.hour == 13 and now.minute < 30)
        checks['Time'] = not is_lunch
        if checks['Time']: score += 20

        return score, p_now, checks
    except:
        return 0, 0, {}

# --- BENUTZEROBERFLÄCHE (UI) ---
st.title("⚡ SNIPER V9.9 ELITE")

# Sidebar für mobile Einstellungen
with st.sidebar:
    st.header("⚙️ Setup")
    cap_input = st.text_input("Kapital (€)", value=str(st.session_state.capital))
    if st.button("Kapital Speichern"):
        st.session_state.capital = float(cap_input)
    
    st.divider()
    market_selection = st.selectbox("Markt wählen", list(WATCHLISTS.keys()))
    st.metric("Budget", f"{st.session_state.capital:,.2f} €")
    
    phase = "⌛ PAUSE" if (11 <= now.hour < 13 and now.minute >= 30 or now.hour == 12) else "🚀 AKTIV"
    st.write(f"Markt-Phase: **{phase}**")

# Haupt-Aktion
if st.button(f"🔍 SCAN {market_selection}", use_container_width=True):
    current_vix, index_p = get_market_context(market_selection)
    st.caption(f"VIX: {current_vix:.2f} | Index: {index_p:+.2f}%")
    
    results_found = False
    for ticker in WATCHLISTS[market_selection]:
        hps_score, live_price, c = calculate_hps_mobile(ticker, current_vix, index_p)
        
        if hps_score > 0:
            results_found = True
            # Risiko-Berechnung (1% Risk, 1.5% SL)
            risk_amt = st.session_state.capital * 0.01
            qty = risk_amt / (live_price * 0.015)
            
            # Mobile Card Design
            with st.container(border=True):
                c1, c2 = st.columns([3, 1])
                with c1:
                    st.subheader(f"{ASSET_NAMES.get(ticker, ticker)}")
                    st.write(f"**Preis:** {live_price:.2f} €")
                    st.write(f"**Position:** {int(qty)} Stück")
                with c2:
                    st.metric("Score", f"{hps_score}%")
                
                # Status Icons
                v_ico = "✅" if c.get('VIX') else "⚠️"
                r_ico = "🔥" if c.get('RSX') else "❄️"
                s_ico = "💎" if c.get('SM') else "➖"
                t_ico = "🕒" if c.get('Time') else "⏳"
                st.write(f"VIX:{v_ico} | RSX:{r_ico} | SM:{s_ico} | Time:{t_ico}")

    if not results_found:
        st.warning("Keine Titel mit HPS > 0 gefunden.")

st.divider()
st.caption(f"Letzter Scan: {now.strftime('%H:%M:%S')} CET | V9.9 Mobile")
