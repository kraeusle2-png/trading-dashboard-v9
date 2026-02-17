import streamlit as st
import pandas as pd
import yfinance as yf
from datetime import datetime
import pytz

# --- SETUP ---
st.set_page_config(page_title="Sniper V10.18", page_icon="🎯", layout="centered")
cet = pytz.timezone('Europe/Berlin')
now = datetime.now(cet)

USER_NAME = "Kraus Markus"

# Speicher für den Tag initialisieren
if 'signal_log' not in st.session_state:
    st.session_state.signal_log = {}
if 'golden_window' not in st.session_state:
    st.session_state.golden_window = {} # Wir nutzen ein Dict für Eindeutigkeit

# --- ASSETS ---
ASSET_NAMES = {
    "SAP.DE": "SAP", "MUV2.DE": "Münchener Rück", "ALV.DE": "Allianz", "SIE.DE": "Siemens", "ENR.DE": "Siemens Energy",
    "AAPL": "Apple", "MSFT": "Microsoft", "NVDA": "NVIDIA", "AMZN": "Amazon", "GOOGL": "Alphabet",
    "TSLA": "Tesla", "META": "Meta", "AVGO": "Broadcom", "COST": "Costco", "NFLX": "Netflix",
    "ASML": "ASML", "AMD": "AMD", "V": "Visa"
}
WATCHLISTS = {
    "DAX 🇩🇪": ["SAP.DE", "MUV2.DE", "ALV.DE", "SIE.DE", "ENR.DE"],
    "US Tech 🇺🇸": ["NVDA", "AAPL", "MSFT", "TSLA", "AMD"]
}
INDEX_TICKERS = {"DAX 🇩🇪": "^GDAXI", "US Tech 🇺🇸": "^IXIC"}

# --- LOGIK FUNKTION ---
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
        return {"score": score, "price": p, "entry": entry, "sl": sl, "tp": tp, "checks": checks, "t": ticker}
    except: return None

# --- SIDEBAR ---
with st.sidebar:
    st.header("⚙️ Sniper Setup")
    m_sel = st.selectbox("Markt wählen", list(WATCHLISTS.keys()))
    if st.button("♻️ Reset Tages-Daten"):
        st.session_state.signal_log = {}
        st.session_state.golden_window = {}
        st.rerun()
    st.divider()
    st.caption(f"Operator: {USER_NAME}")

# --- MAIN UI ---
st.title("🎯 SNIPER MONITOR V10.18")

# 1. GOLDEN WINDOW SEKTION (Oben fixiert)
if st.session_state.golden_window:
    with st.container(border=True):
        st.subheader("⭐ GOLDEN WINDOW (09:30 - 09:45)")
        for t, g in st.session_state.golden_window.items():
            st.success(f"**{ASSET_NAMES.get(t, t)}**: Signal um {g['time']} Uhr bei {g['price']:.2f} € (Score: {g['score']}%)")
st.divider()

# 2. ANALYSE BUTTON
if st.button(f"🔍 ANALYSE STARTEN", use_container_width=True):
    vx_d = yf.download("^VIX", period="1d", progress=False)
    v_val = get_safe_val(vx_d['Close'].iloc[-1])
    ix_d = yf.download(INDEX_TICKERS[m_sel], period="2d", interval="15m", progress=False)
    i_perf = ((get_safe_val(ix_d['Close'].iloc[-1]) / get_safe_val(ix_d['Close'].iloc[-2])) - 1) * 100
    
    st.info(f"VIX: {v_val:.2f} | {m_sel} Index: {i_perf:+.2f}%")
    
    current_time_str = now.strftime("%H:%M")
    is_golden_time = "09:30" <= current_time_str <= "09:45"
    
    res = []
    for t in WATCHLISTS[m_sel]:
        data = calc_pro_entry(t, v_val, i_perf, m_sel)
        if data:
            # Falls im Golden Window und Score >= 80 -> In den Sonderspeicher
            if is_golden_time and data['score'] >= 80:
                if t not in st.session_state.golden_window:
                    st.session_state.golden_window[t] = {"time": current_time_str, "price": data['price'], "score": data['score']}
            
            # Normales Signal Log
            if data['score'] >= 80 and t not in st.session_state.signal_log:
                st.session_state.signal_log[t] = {"time": current_time_str, "price": data['price']}
            
            res.append(data)
    
    # Anzeige der aktuellen Liste (wie gewohnt)
    for item in sorted(res, key=lambda x: x['score'], reverse=True):
        with st.container(border=True):
            st.subheader(ASSET_NAMES.get(item['t'], item['t']))
            st.write(f"💹 Kurs: {item['price']:.2f} € | Score: **{item['score']}%**")
            
            ch = item['checks']
            c1, c2, c3, c4 = st.columns(4)
            c1.write(f"{'✅' if ch['VIX'] else '❌'} VIX")
            c2.write(f"{'✅' if ch['RSX'] else '❌'} RSX")
            c3.write(f"{'✅' if ch['SM'] else '❌'} SM")
            c4.write(f"{'✅' if ch['TIME'] else '❌'} ZEIT")
            st.info(f"SL: {item['sl']:.2f} | Ziel: {item['tp']:.2f}")

st.caption(f"Letztes Update: {now.strftime('%H:%M:%S')} | {USER_NAME}")
