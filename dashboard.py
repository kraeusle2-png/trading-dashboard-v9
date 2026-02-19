import streamlit as st
import pandas as pd
import yfinance as yf
from datetime import datetime
import pytz

# --- SETUP ---
st.set_page_config(page_title="Sniper V10.36", page_icon="🎯", layout="wide")
cet = pytz.timezone('Europe/Berlin')
now = datetime.now(cet)

USER_NAME = "Kraus Markus"

# Speicher initialisieren
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
    
    if "DAX" in m_sel:
        gw_start = "09:30"
        pre_times = ['09:15', '09:20', '09:25', '09:30']
    else:
        gw_start = "15:30"
        pre_times = ['15:15', '15:20', '15:25', '15:30']
        
    st.divider()
    if st.button("♻️ Reset"):
        st.session_state.golden_window, st.session_state.current_results = {}, []
        st.rerun()

# --- MAIN UI ---
st.title(f"🎯 SNIPER PRO MONITOR V10.36")

# 1. GOLDEN WINDOW (Mit exakter Kurs- und Zeit-Anzeige)
if st.session_state.golden_window:
    with st.container(border=True):
        st.subheader(f"⭐ Golden Window Monitoring (Basis: {gw_start} Uhr)")
        valid_gw = {k: v for k, v in st.session_state.golden_window.items() if 'curr' in v and 'entry' in v}
        
        if valid_gw:
            g_cols = st.columns(len(valid_gw))
            for idx, (t, g) in enumerate(valid_gw.items()):
                perf = ((g['curr'] / g['entry']) - 1) * 100
                with g_cols[idx]:
                    st.markdown(f"### {ASSET_NAMES.get(t, t)}")
                    if 'hps_hist' in g:
                        hist_text = "".join([f"`{time_l}: {s_v}%`  \n" for time_l, s_v in g['hps_hist'].items()])
                        st.info(hist_text)
                    
                    st.write(f"📌 In ({gw_start}): **{g['entry']:.2f}€**")
                    st.write(f"🕒 Aktuell ({g['update_time']}):")
                    st.subheader(f"{g['curr']:.2f}€")
                    st.metric("Performance", f"{perf:+.2f}%")
st.divider()

# 2. ANALYSE BUTTON
if st.button(f"🔍 {m_sel} ANALYSE STARTEN", use_container_width=True):
    with st.spinner("Lade Marktdaten..."):
        vx_d = yf.download("^VIX", period="1d", progress=False)
        v_val = get_safe_val(vx_d['Close'].iloc[-1])
        ix_d = yf.download(INDEX_TICKERS[m_sel], period="2d", interval="5m", progress=False)
        i_perf = ((get_safe_val(ix_d['Close'].iloc[-1]) / get_safe_val(ix_d['Close'].iloc[-2])) - 1) * 100
        
        # Sekundengenaue Zeit für das aktuelle Update
        update_time_str = datetime.now(cet).strftime("%H:%M:%S")
        temp_results = []

        for t in WATCHLISTS[m_sel]:
            try:
                s = yf.download(t, period="2d", interval="5m", progress=False)
                if len(s) < 5: continue
                
                p_now = get_safe_val(s['Close'].iloc[-1])
                hi, lo = get_safe_val(s['High'].iloc[-1]), get_safe_val(s['Low'].iloc[-1])
                prev_p = get_safe_val(s['Close'].iloc[-2])
                
                # Momentum & Golden Window Logik
                h_window = s.between_time(pre_times[0], gw_start)
                hps_history = {}
                entry_price_gw = None
                
                if not h_window.empty:
                    for timestamp, row in h_window.iterrows():
                        t_label = timestamp.strftime('%H:%M')
                        if t_label in pre_times:
                            p_h = get_safe_val(row['Close'])
                            s_h = calc_hps_score(p_h, prev_p, hi, lo, v_val, i_perf, (t_label == gw_start))
                            hps_history[t_label] = s_h
                            if t_label == gw_start: entry_price_gw = p_h

                # Golden Window Update
                if entry_price_gw:
                    st.session_state.golden_window[t] = {
                        "entry": entry_price_gw, 
                        "curr": p_now, 
                        "hps_hist": hps_history,
                        "update_time": update_time_str
                    }
                elif t in st.session_state.golden_window:
                    st.session_state.golden_window[t].update({"curr": p_now, "update_time": update_time_str})

                # Analyse Resultate (Live Liste)
                score_now = calc_hps_score(p_now, prev_p, hi, lo, v_val, i_perf, True)
                temp_results.append({
                    "t": t, "name": ASSET_NAMES.get(t, t), "score": score_now, "price": p_now, 
                    "sl": lo * 0.995, "tp": p_now + (p_now-(lo*0.995))*2, "status": "OK" if p_now > (lo * 0.995) else "STOP"
                })
            except: continue
        
        st.session_state.current_results = temp_results
        st.rerun()

# 3. ANZEIGE DER ERGEBNISSE
for item in sorted(st.session_state.current_results, key=lambda x: x['score'], reverse=True):
    with st.container(border=True):
        c1, c2 = st.columns([3, 1])
        c1.subheader(item['name'])
        c2.metric("Score", f"{item['score']}%")
        st.write(f"💹 Aktuell: {item['price']:.2f} € | SL: {item['sl']:.2f} €")
        if item['status'] == "STOP": st.error("🛑 STOP LOSS")
        else: st.success("🛡️ OK")

st.caption(f"V10.36 | {USER_NAME} | {datetime.now(cet).strftime('%H:%M:%S')}")
