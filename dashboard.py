import streamlit as st
import pandas as pd
import yfinance as yf
from datetime import datetime
import pytz

# --- SETUP ---
st.set_page_config(page_title="Sniper V10.5", page_icon="🎯", layout="centered")
cet = pytz.timezone('Europe/Berlin')
now = datetime.now(cet)

USER_NAME = "Kraus Markus"

# Initialisierung des ersten Signals (Session State)
if 'first_alert_time' not in st.session_state:
    st.session_state.first_alert_time = None

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

if 'capital' not in st.session_state: 
    st.session_state.capital = 3836.29

def get_safe_val(dp):
    return float(dp.iloc[0]) if isinstance(dp, pd.Series) else float(dp)

def get_timing_info(markt):
    if "DAX" in markt:
        return "09:15-11:30 & 15:45-17:30"
    else:
        return "15:45-21:00"

def check_timing(markt):
    stunde = now.hour
    minute = now.minute
    zeit_f = stunde + minute / 60.0
    if "DAX" in markt:
        return (9.25 <= zeit_f <= 11.5) or (15.75 <= zeit_f <= 17.5)
    else:
        return (15.75 <= zeit_f <= 21.0)

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
        checks['TIME'] = check_timing(markt)
        if checks['TIME']: score += 20
        
        entry, sl = hi * 1.001, lo * 0.995
        tp = entry + ((entry - sl) * 2)
        
        return {"score": score, "price": p, "entry": entry, "sl": sl, "tp": tp, "checks": checks, "t": ticker}
    except: return None

# --- UI ---
st.title("🎯 SNIPER V10.5")

with st.sidebar:
    st.header("⚙️ Settings")
    c_in = st.text_input("Kapital (€)", value=str(st.session_state.capital))
    if st.button("Speichern"): st.session_state.capital = float(c_in)
    m_sel = st.selectbox("Markt", list(WATCHLISTS.keys()))
    st.metric("Budget", f"{st.session_state.capital:,.2f} €")
    
    # Anzeige des ersten Signals in der Sidebar
    st.divider()
    if st.session_state.first_alert_time:
        st.success(f"🚀 Erstes Signal heute:\n{st.session_state.first_alert_time}")
    else:
        st.info("Kein Signal bisher.")
    st.caption(f"Operator: {USER_NAME}")

if st.button(f"🔍 ANALYSE STARTEN", use_container_width=True):
    vx_d = yf.download("^VIX", period="1d", progress=False)
    v_val = get_safe_val(vx_d['Close'].iloc[-1])
    ix_d = yf.download(INDEX_TICKERS[m_sel], period="2d", interval="15m", progress=False)
    i_perf = ((get_safe_val(ix_d['Close'].iloc[-1]) / get_safe_val(ix_d['Close'].iloc[-2])) - 1) * 100
    
    st.info(f"VIX: {v_val:.2f} | {m_sel} Index: {i_perf:+.2f}%")
    
    res = []
    for t in WATCHLISTS[m_sel]:
        data = calc_pro_entry(t, v_val, i_perf, m_sel)
        if data and data['score'] > 0:
            res.append(data)
            # LOGIK: Erstes Signal des Tages (Score >= 80) speichern
            if data['score'] >= 80 and st.session_state.first_alert_time is None:
                st.session_state.first_alert_time = now.strftime("%H:%M:%S")
    
    res = sorted(res, key=lambda x: x['score'], reverse=True)
    zeit_fenster = get_timing_info(m_sel)
    
    for item in res:
        qty = (st.session_state.capital * 0.01) / (item['entry'] - item['sl'])
        with st.container(border=True):
            col1, col2 = st.columns([2, 1])
            with col1:
                st.subheader(ASSET_NAMES.get(item['t'], item['t']))
                st.write(f"💹 **Kurs: {item['price']:.2f} €**")
            with col2:
                st.metric("Score", f"{item['score']}%")
            
            ch = item['checks']
            st.write(f"{'✅' if ch['VIX'] else '❌'} VIX | {'✅' if ch['RSX'] else '❌'} RSX | {'✅' if ch['SM'] else '❌'} SM | {'✅' if ch['TIME'] else '❌'} Zeit")
            
            if ch['TIME']:
                st.success(f"🕒 **Einstieg:** Jetzt (Fenster: {zeit_fenster})")
            else:
                st.warning(f"🕒 **Fenster:** {zeit_fenster}")
            
            st.info(f"**ENTRY:** {item['entry']:.2f} € | **STÜCK:** {int(qty)}")
            ca, cb = st.columns(2)
            ca.error(f"Stop: {item['sl']:.2f} €")
            cb.success(f"Ziel: {item['tp']:.2f} €")

st.divider()
st.caption(f"Letzter Scan: {now.strftime('%H:%M:%S')} | Operator: {USER_NAME}")
