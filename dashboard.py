import streamlit as st
import pandas as pd
import yfinance as yf
import numpy as np
from datetime import datetime
import pytz

# --- KONFIGURATION ---
st.set_page_config(page_title="V9.5 Multi-Index Terminal", layout="wide")
cet = pytz.timezone('Europe/Berlin')
now = datetime.now(cet)

# Mapping für leserliche Namen & Listen
ASSET_NAMES = {
    "SAP.DE": "SAP", "MUV2.DE": "Münchener Rück", "ALV.DE": "Allianz", "SIE.DE": "Siemens", "ENR.DE": "Siemens Energy",
    "AAPL": "Apple", "MSFT": "Microsoft", "NVDA": "NVIDIA", "AMZN": "Amazon", "GOOGL": "Alphabet",
    "TSLA": "Tesla", "META": "Meta", "AVGO": "Broadcom", "COST": "Costco", "NFLX": "Netflix"
}

WATCHLISTS = {
    "DAX (Top Titel)": ["SAP.DE", "MUV2.DE", "ALV.DE", "SIE.DE", "ENR.DE"],
    "S&P 500 (Leaders)": ["AAPL", "MSFT", "NVDA", "AMZN", "GOOGL", "META", "TSLA"],
    "Nasdaq 100 (Tech)": ["NVDA", "AVGO", "COST", "NFLX", "MSFT", "AAPL"]
}

INDEX_TICKERS = {
    "DAX (Top Titel)": "^GDAXI",
    "S&P 500 (Leaders)": "^GSPC",
    "Nasdaq 100 (Tech)": "^IXIC"
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

def get_index_performance(index_name):
    try:
        ticker = INDEX_TICKERS.get(index_name, "^GDAXI")
        idx_data = yf.download(ticker, period="2d", interval="15m", progress=False)
        if not idx_data.empty:
            c_now = idx_data['Close'].iloc[-1]
            c_prev = idx_data['Close'].iloc[-2]
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
        
        # 1. VIX Check
        vix_ok = current_vix <= 22
        if vix_ok: score += 20
        # 2. Timing
        is_lunch = (now.hour == 11 and now.minute >= 30) or (now.hour == 12) or (now.hour == 13 and now.minute < 30)
        timing_ok = not is_lunch
        if timing_ok: score += 20
        # 3. RSX (Rel. Stärke zum gewählten Index)
        rsx_ok = (stock_perf - index_perf) > 0
        if rsx_ok: score += 30
        # 4. Smart Money
        sm_ratio = (p_now - d_low) / (d_high - d_low) if d_high != d_low else 0.5
        sm_ok = sm_ratio > 0.7
        if sm_ok: score += 30
        
        return score, p_now, {"RSX": rsx_ok, "VIX": vix_ok, "Time": timing_ok}
    except: return 0, 0, {}

# --- UI ---
st.title("⚡ MASTER-DASHBOARD 9.5 MULTI-INDEX")

st.sidebar.header("Kommando-Zentrale")
input_cap = st.sidebar.text_input("Kapital", value=str(st.session_state.capital))
if st.sidebar.button("Kapital Speichern"):
    st.session_state.capital = float(input_cap)

st.sidebar.divider()
selected_market = st.sidebar.selectbox("Markt auswählen", list(WATCHLISTS.keys()))

st.sidebar.metric("Kapitalbasis", f"{st.session_state.capital:,.2f} €")
st.sidebar.write(f"Status: **{'⌛ MITTAGS-PAUSE' if (11 <= now.hour < 13) else '🚀 HANDELSAKTIV'}**")

if st.button(f"SCAN {selected_market.upper()}"):
    vix = get_vix_level()
    idx_p = get_index_performance(selected_market)
    
    results = []
    with st.spinner(f'Analysiere {selected_market}...'):
        for t in WATCHLISTS[selected_market]:
            score, price, f = calculate_hps(t, vix, idx_p)
            if score > 0:
                risk = st.session_state.capital * 0.01
                qty = risk / (price * 0.015) if price > 0 else 0
                results.append({
                    "Asset": ASSET_NAMES.get(t, t),
                    "HPS-Score": f"{score}%",
                    "Kurs": f"{price:.2f}",
                    "Stärke": "🔥 RSX+" if f.get('RSX') else "❄️ RSX-",
                    "VIX": "✅" if f.get('VIX') else "⚠️",
                    "Timing": "✅" if f.get('Time') else "⏳",
                    "Stück": int(qty)
                })
    
    if results:
        df = pd.DataFrame(results).sort_values(by="HPS-Score", ascending=False)
        st.table(df)
        st.caption(f"Index: {INDEX_TICKERS[selected_market]} | VIX: {vix:.2f} | Index Perf: {idx_p:+.2f}%")
