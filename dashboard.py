import streamlit as st
import pandas as pd
import yfinance as yf
from datetime import datetime
import pytz

# --- SETUP ---
st.set_page_config(page_title="Sniper V10.31", page_icon="🎯", layout="wide")
cet = pytz.timezone('Europe/Berlin')
now = datetime.now(cet)

USER_NAME = "Kraus Markus"

if 'signal_log' not in st.session_state:
    st.session_state.signal_log = {}
if 'golden_window' not in st.session_state:
    st.session_state.golden_window = {}
if 'current_results' not in st.session_state:
    st.session_state.current_results = []

# --- ASSETS & WATCHLISTS ---
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

def get_safe_val(dp):
    return float(dp.iloc[0]) if isinstance(dp, pd.Series) else float(dp)

def calc_hps_score(price, prev_price, hi, lo, vix, idx_p, is_market_time):
    score = 0
    if vix <= 22.5: score += 20
    r_now = ((price/prev_price)-1)*100 - idx_p
    if r_now > 0: score += 30
    sm = (price - lo) / (hi - lo) if hi != lo else 0.5
    if sm > 0.72: score += 30
    if is_market_time: score += 20
    return score

# --- SIDEBAR ---
with st.sidebar:
    st.header("🎯 Sniper Dashboard")
    m_sel = st.selectbox("Markt wählen", list(WATCHLISTS.keys()))
    st.divider()
    if st.button("♻️ Reset"):
        st.session_state.signal_log = {}
        st.session_state.golden_window = {}
        st.session_state.current_results = []
        st.rerun()

# --- MAIN UI ---
st.title("🎯 SNIPER PRO MONITOR V10.31")

# 1. GOLDEN WINDOW (Mit HPS-Zeitstrahl)
if st.session_state.golden_window:
    with st.container(border=True):
        st.subheader("⭐ Golden Window & Momentum (09:15 - 09:30)")
        g_cols = st.columns(len(st.session_state.golden_window))
        for idx, (t, g) in enumerate(st.session_state.golden_window.items()):
            perf = ((g['curr'] / g['entry']) - 1) * 100
            with g_cols[idx]:
                st.markdown(f"### {ASSET_NAMES.get(t, t)}")
                # Anzeige der HPS Entwicklung
                st.write("**HPS Entwicklung:**")
                hist_str = ""
                for time_key, s_val in g['hps_hist'].items():
                    hist_str += f"`{time_key}: {s_val}%`  \n"
                st.info(hist_str)
                st.markdown(f"**Aktuell: {g['curr']:.2f}€** ({perf:+.2f}%)")
st.divider()

# 2. ANALYSE
if st.button(f"🔍 ANALYSE STARTEN", use_container_width=True):
    vx_d = yf.download("^VIX", period="1d", progress=False)
    v_val = get_safe_val(vx_d['Close'].iloc[-1])
    ix_d = yf.download(INDEX_TICKERS[m_sel], period="2d", interval="5m", progress=False)
    i_perf = ((get_safe_val(ix_d['Close'].iloc[-1]) / get_safe_val(ix_d['Close'].iloc[-2])) - 1) * 100
    
    current_time_str = now.strftime("%H:%M")
    
    temp_results = []
    for t in WATCHLISTS[m_sel]:
        try:
            s = yf.download(t, period="2d", interval="5m", progress=False)
            if len(s) < 5: continue
            
            p_now = get_safe_val(s['Close'].iloc[-1])
            hi, lo = get_safe_val(s['High'].iloc[-1]), get_safe_val(s['Low'].iloc[-1])
            prev_p = get_safe_val(s['Close'].iloc[-2])
            
            zf = now.hour + now.minute / 60.0
            is_market = (9.25 <= zf <= 11.5) or (15.75 <= zf <= 17.5) if "DAX" in m_sel else (15.75 <= zf <= 21.0)
            score_now = calc_hps_score(p_now, prev_p, hi, lo, v_val, i_perf, is_market)
            
            # --- Momentum-Historie (09:15 - 09:30) ---
            h_window = s.between_time('09:15', '09:30')
            hps_history = {}
            if not h_window.empty:
                # Wir prüfen die exakten Zeitstempel
                for timestamp, row in h_window.iterrows():
                    t_str = timestamp.strftime('%H:%M')
                    if t_str in ['09:15', '09:20', '09:25', '09:30']:
                        p_hist = get_safe_val(row['Close'])
                        # Score Berechnung für den historischen Zeitpunkt
                        s_hist = calc_hps_score(p_hist, prev_p, hi, lo, v_val, i_perf, (t_str == '09:30'))
                        hps_history[t_str] = s_hist

            # Golden Window Logik
            if '09:30' in hps_history:
                if t not in st.session_state.golden_window:
                    st.session_state.golden_window[t] = {
                        "time": "09:30", 
                        "entry": get_safe_val(h_window.loc[h_window.index.strftime('%H:%M') == '09:30']['Close']),
                        "curr": p_now,
                        "hps_hist": hps_history
                    }
            
            if t in st.session_state.golden_window:
                st.session_state.golden_window[t]["curr"] = p_now

            # Resultate für Anzeige unten
            sl = lo * 0.995
            temp_results.append({
                "t": t, "score": score_now, "price": p_now, "sl": sl, 
                "tp": p_now + (p_now-sl)*2, "sl_status": "OK" if p_now > sl else "STOP"
            })
        except: continue
    
    st.session_state.current_results = temp_results
    st.
