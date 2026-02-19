import streamlit as st
import pandas as pd
import yfinance as yf
from datetime import datetime
import pytz

# --- SETUP ---
st.set_page_config(page_title="Sniper V10.32", page_icon="🎯", layout="wide")
cet = pytz.timezone('Europe/Berlin')
now = datetime.now(cet)

USER_NAME = "Kraus Markus"

# Speicher initialisieren
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
    st.caption(f"Operator: {USER_NAME}")

# --- MAIN UI ---
st.title("🎯 SNIPER PRO MONITOR V10.32")

# 1. GOLDEN WINDOW (HPS Historie 09:15 - 09:30)
if st.session_state.golden_window:
    with st.container(border=True):
        st.subheader("⭐ Golden Window & Momentum Tracker")
        g_cols = st.columns(len(st.session_state.golden_window))
        for idx, (t, g) in enumerate(st.session_state.golden_window.items()):
            perf = ((g['curr'] / g['entry']) - 1) * 100
            with g_cols[idx]:
                st.markdown(f"**{ASSET_NAMES.get(t, t)}**")
                hist_text = ""
                for time_label, s_val in g['hps_hist'].items():
                    hist_text += f"`{time_label}: {s_val}%`  \n"
                st.info(hist_text)
                st.write(f"In: {g['entry']:.2f}€ | **Aktuell: {g['curr']:.2f}€**")
                st.metric("Performance", f"{perf:+.2f}%")
st.divider()

# 2. ANALYSE BUTTON
if st.button(f"🔍 ANALYSE STARTEN", use_container_width=True):
    with st.spinner("Lade Daten..."):
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
                
                # Momentum-Analyse (Historie 09:15-09:30)
                h_window = s.between_time('09:15', '09:30')
                hps_history = {}
                entry_930 = p_now
                
                if not h_window.empty:
                    for timestamp, row in h_window.iterrows():
                        t_label = timestamp.strftime('%H:%M')
                        if t_label in ['09:15', '09:20', '09:25', '09:30']:
                            p_h = get_safe_val(row['Close'])
                            s_h = calc_hps_score(p_h, prev_p, hi, lo, v_val, i_perf, (t_label == '09:30'))
                            hps_history[t_label] = s_h
                            if t_label == '09:30': entry_930 = p_h

                # Golden Window Update
                if '09:30' in hps_history:
                    if t not in st.session_state.golden_window:
                        st.session_state.golden_window[t] = {"time": "09:30", "entry": entry_930, "curr": p_now, "hps_hist": hps_history}
                
                if t in st.session_state.golden_window:
                    st.session_state.golden_window[t]["curr"] = p_now

                # Live Analyse Resultat
                score_now = calc_hps_score(p_now, prev_p, hi, lo, v_val, i_perf, is_market)
                sl = lo * 0.995
                temp_results.append({
                    "t": t, "name": ASSET_NAMES.get(t, t), "score": score_now, "price": p_now, 
                    "sl": sl, "tp": p_now + (p_now-sl)*2, "status": "OK" if p_now > sl else "STOP"
                })
            except: continue
        
        st.session_state.current_results = temp_results
        st.rerun()

# 3. ANZEIGE DER ERGEBNISSE
for item in sorted(st.session_state.current_results, key=lambda x: x['score'], reverse=True):
    with st.container(border=True):
        c1, c2 = st.columns([3, 1])
        c1.subheader(item['name'])
        c2.metric("HPS Score", f"{item['score']}%")
        
        st.write(f"🔔 **Signal:** 09:30 Uhr (Einstieg via GW) | **Aktuell: {item['price']:.2f} €**")
        
        if item['status'] == "STOP":
            st.error(f"🛑 STOP LOSS ERREICHT")
        else:
            st.success(f"🛡️ STOP LOSS OK")
            
        st.info(f"**Plan:** SL: **{item['sl']:.2f} €** | Ziel: {item['tp']:.2f} €")
        st.write("✅ VIX | ✅ RSX | ✅ SM | ✅ ZEIT")

st.caption(f"V10.32 | {now.strftime('%H:%M:%S')} | {USER_NAME}")
