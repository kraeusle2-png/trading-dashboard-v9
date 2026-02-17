import streamlit as st
import pandas as pd
import yfinance as yf
import numpy as np
from datetime import datetime
import pytz

# --- KONFIGURATION ---
st.set_page_config(page_title="Sniper V9.9 Elite", layout="centered")
cet = pytz.timezone('Europe/Berlin')
now = datetime.now(cet)

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

if 'capital' not in st.session_state: st.session_state.capital = 3836.29

# --- ENGINE ---
def get_safe_val(dp):
    return float(dp.iloc[0]) if isinstance(dp, pd.Series) else float(dp)

def get_market_context(index_name):
    try:
        vix_data = yf.download("^VIX", period="1d", progress=False)
        vix = get_safe_val(vix_data['Close'].iloc[-1])
        idx_ticker = INDEX_TICKERS.get(index_name, "^GDAXI")
        idx_data = yf.download(idx_ticker, period="2d", interval="15m", progress=False)
        idx_perf = ((get_safe_val(idx_data['Close'].iloc[-1]) / get_safe_val(idx_data['Close'].iloc[-2])) - 1) * 100
        return vix, idx_perf
    except: return 20.0, 0.0

def calculate_hps_mobile(ticker, vix, idx_perf):
    try:
        stock = yf.download(ticker, period="2d", interval="15m", progress=False)
        if len(stock) < 3: return 0, 0, {}
        p_now = get_safe_val(stock['Close'].iloc[-1])
        p_prev = get_safe_val(stock['Close'].iloc[-2])
        p_old = get_safe_val(stock['Close'].iloc[-3])
        high, low = get_safe_val(stock['High'].iloc[-1]), get_safe_val(stock['Low'].iloc[-1])
        
        if abs((p_now / p_prev) - 1) > 0.10: return 0, p_now, {}
        
        score = 0
        checks = {}
        checks['VIX'] = vix <= 22.5
        if checks['VIX']: score += 20
        
        perf_15m = ((p_now / p_prev) - 1) * 100
        rsx_now = perf_15m - idx_perf
        rsx_prev = (((p_prev / p_old) - 1) * 100) - idx_perf
        checks['RSX'] = rsx_now > 0 and (rsx_now + rsx_prev) > -0.1
        if checks['RSX']: score += 30
        
        sm_ratio = (p_now - low) / (high - low) if high != low else 0.5
        checks['SM'] = sm_ratio > 0.72
        if checks['SM']: score += 30
        
        # Timing (Mittagspause 11:30-13:30)
        is_lunch = (11 <= now.hour <= 13) and not (now.hour == 11 and now.minute < 30) and not (now.hour == 13 and now.minute >= 30)
        checks['Time'] = not is_lunch
        if checks['Time']: score += 20
        
        return score, p_now, checks
    except: return 0, 0, {}

# --- UI ---
st.title("⚡ SNIPER V9.9 SORTED")

with st.sidebar:
    st.header("⚙️ Setup")
    cap_input = st.text_input("Kapital (€)", value=str(st.session_state.capital))
    if st.button("Save"): st.session_state.capital = float(cap_input)
    market_selection = st.selectbox("Markt", list(WATCHLISTS.keys()))
    st.metric("Budget", f"{st.session_state.capital:,.2f} €")

if st.button(f"🔍 SCAN {market_selection}", use_container_width=True):
    vix, idx_p = get_market_context(market_selection)
    st.caption(f"VIX: {vix:.2f} | Index: {idx_p:+.2f}%")
    
    all_results = []
    with st.spinner('Analysiere & Sortiere...'):
        for ticker in WATCHLISTS[market_selection]:
            score, price, c = calculate_hps_mobile(ticker, vix, idx_p)
            if score > 0:
                all_results.append({
                    "ticker": ticker, "score": score, "price": price, "checks": c
                })
    
    # --- SORTIERUNG (Höchster Score zuerst) ---
    all_results = sorted(all_results, key=lambda x: x['score'], reverse=True)
    
    if all_results:
        for item in all_results:
            t, s, p, c = item['ticker'], item['score'], item['price'], item['checks']
            qty = (st.session_state.capital * 0.01) / (p * 0.015)
            
            with st.container(border=True):
                c1, c2 = st.columns([3, 1])
                with c1:
                    st.subheader(f"{ASSET_NAMES.get(t, t)}")
                    st.write(f"**Preis:** {p:.2f} € | **Stück:** {int(qty)}")
                with c2:
                    st.metric("Score", f"{s}%")
                
                v_ico = "✅" if c.get('
