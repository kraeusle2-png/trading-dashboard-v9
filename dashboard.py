import streamlit as st
import pandas as pd
import yfinance as yf
from datetime import datetime
import pytz

# --- SETUP ---
st.set_page_config(page_title="Sniper V10.21", page_icon="🎯", layout="wide")
cet = pytz.timezone('Europe/Berlin')
now = datetime.now(cet)

USER_NAME = "Kraus Markus"

if 'signal_log' not in st.session_state:
    st.session_state.signal_log = {}
if 'golden_window' not in st.session_state:
    st.session_state.golden_window = {}

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

def calc_pro_entry(ticker, vix, idx_p, markt):
    try:
        s = yf.download(ticker, period="2d", interval="15m", progress=False)
        if len(s) < 3: return None
        p = get_safe_val(s['Close'].iloc[-1])
        hi, lo = get_safe_val(s['High'].iloc[-1]), get_safe_val(s['Low'].iloc[-1])
        prev_p = get_safe_val(s['Close'].iloc[-2])
        
        checks = {}
        score = 0
        checks['VIX'] = vix <= 22.5
        if checks['VIX']: score += 20
        r_now = ((p/prev_p)-1)*100 - idx_p
        checks['RSX'] = r_now > 0
        if checks['RSX']: score += 30
        sm = (p - lo) / (hi - lo) if hi != lo else 0.5
        checks['SM'] = sm > 0.72
        if checks['SM']: score += 30
        
        zf = now.hour + now.minute / 60.0
        if "DAX" in markt:
            checks['TIME'] = (9.25 <= zf <= 11.5) or (15.75 <= zf <= 17.5)
        else:
            checks['TIME'] = (15.75 <= zf <= 21.0)
        if checks['TIME']: score += 20
        
        entry, sl = hi * 1.001, lo * 0.995
        tp = entry + ((entry - sl) * 2)
        sl_hit = f"ERREICHT ({now.strftime('%H:%M')})" if p <= sl else "Offen"
        return {"score": score, "price": p, "entry": entry, "sl": sl, "tp": tp, "checks": checks, "t": ticker, "sl_status": sl_hit}
    except: return None

# --- UI SIDEBAR ---
with st.sidebar:
    st.header("🎯 Sniper Dashboard")
    m_sel = st.selectbox("Markt wählen", list(WATCHLISTS.keys()))
    if st.button("♻️ Reset Tages-Daten"):
        st.session_state.signal_log = {}
        st.session_state.golden_window = {}
        st.rerun()
    st.divider()
    st.subheader("📊 Tages-Log")
    for t, data in st.session_state.signal_log.items():
        with st.expander(f"{ASSET_NAMES.get(t,t)} ({data['time']})"):
            st.write(f"🟢 In: {data['price']:.2f}€")
            if data.get("exit_triggered"): st.write(f"🟠 Out: {data['exit_price']:.2f}€")

# --- MAIN UI ---
st.title("🎯 SNIPER PRO V10.21")

# 1. GOLDEN WINDOW (Mit Live-Update)
if st.session_state.golden_window:
    st.markdown("### ⭐ GOLDEN WINDOW LIVE-MONITOR (09:30 - 09:45)")
    cols = st.columns(len(st.session_state.golden_window))
    for idx, (t, g) in enumerate(st.session_state.golden_window.items()):
        with cols[idx]:
            diff = ((g['current_price'] / g['entry_price']) - 1) * 100
            color = "#2ecc71" if diff >= 0 else "#e74c3c"
            st.markdown(f"""
            <div style="padding:15px; border-radius:10px; border: 2px solid #f1c40f; background-color: rgba(241, 196, 15, 0.05);">
                <h4 style="margin:0;">{ASSET_NAMES.get(t, t)}</h4>
                <small>Einstieg: {g['time']} (@ {g['entry_price']:.2f}€)</small><br>
                <b style="color:{color}; font-size:1.2em;">Aktuell: {g['current_price']:.2f}€ ({diff:+.2f}%)</b><br>
                <small>Letzter Check: {g['last_update']}</small>
            </div>
            """, unsafe_allow_html=True)
st.divider()

# 2. ANALYSE
if st.button(f"🔍 ANALYSE STARTEN", use_container_width=True):
    vx_d = yf.download("^VIX", period="1d", progress=False)
    v_val = get_safe_val(vx_d['Close'].iloc[-1])
    ix_d = yf.download(INDEX_TICKERS[m_sel], period="2d", interval="15m", progress=False)
    i_perf = ((get_safe_val(ix_d['Close'].iloc[-1]) / get_safe_val(ix_d['Close'].iloc[-2])) - 1) * 100
    
    current_time_str = now.strftime("%H:%M")
    is_golden_time = "09:30" <= current_time_str <= "09:45"
    
    res = []
    for t in WATCHLISTS[m_sel]:
        data = calc_pro_entry(t, v_val, i_perf, m_sel)
        if data:
            # GOLDEN WINDOW UPDATE LOGIK
            if is_golden_time and data['score'] >= 80:
                if t not in st.session_state.golden_window:
                    st.session_state.golden_window[t] = {
                        "time": current_time_str, "entry_price": data['price'], 
                        "current_price": data['price'], "last_update": current_time_str, "score": data['score']
                    }
            
            # Update für bestehende Golden-Window Titel (unabhängig von der Uhrzeit)
            if t in st.session_state.golden_window:
                st.session_state.golden_window[t].update({
                    "current_price": data['price'], "last_update": current_time_str
                })

            # SIGNAL LOGIK (Wie gehabt)
            if data['score'] >= 80 and t not in st.session_state.signal_log:
                st.session_state.signal_log[t] = {"time": current_time_str, "price": data['price'], "exit_triggered": False}
            if t in st.session_state.signal_log and data['score'] < 80 and not st.session_state.signal_log[t].get("exit_triggered"):
                st.session_state.signal_log[t].update({"exit_time": current_time_str, "exit_price": data['price'], "exit_triggered": True})
            
            res.append(data)
    
    # Assets rendern (Score-Liste unten)
    for item in sorted(res, key=lambda x: x['score'], reverse=True):
        with st.container(border=True):
            col1, col2 = st.columns([2, 1])
            with col1:
                st.subheader(ASSET_NAMES.get(item['t'], item['t']))
                st.write(f"💹 Kurs: **{item['price']:.2f} €**")
            with col2: st.metric("HPS Score", f"{item['score']}%")
            
            sig_data = st.session_state.signal_log.get(item['t'])
            if sig_data:
                st.write(f"🔔 Signal: {sig_data['time']} (@ {sig_data['price']:.2f} €)")
                if sig_data.get("exit_triggered"):
                    st.warning(f"⚠️ Verkaufssignal: {sig_data['exit_time']} (@ {sig_data['exit_price']:.2f} €)")
            
            if "ERREICHT" in item['sl_status']: st.error(f"🛑 STOP LOSS: {item['sl_status']}")
            st.info(f"SL: {item['sl']:.2f} | Ziel: {item['tp']:.2f}")
            ch = item['checks']
            c1, c2, c3, c4 = st.columns(4)
            c1.write(f"{'✅' if ch['VIX'] else '❌'} VIX")
            c2.write(f"{'✅' if ch['RSX'] else '❌'} RSX")
            c3.write(f"{'✅' if ch['SM'] else '❌'} SM")
            c4.write(f"{'✅' if ch['TIME'] else '❌'} ZEIT")

st.caption(f"Update: {now.strftime('%H:%M:%S')} | Operator: {USER_NAME}")
