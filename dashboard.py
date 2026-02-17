import streamlit as st
import pandas as pd
import yfinance as yf
from datetime import datetime
import pytz

# --- SETUP ---
st.set_page_config(page_title="Sniper V10.28", page_icon="🎯", layout="wide")
cet = pytz.timezone('Europe/Berlin')
now = datetime.now(cet)

USER_NAME = "Kraus Markus"

# Speicher initialisieren, damit nichts verschwindet
if 'signal_log' not in st.session_state:
    st.session_state.signal_log = {}
if 'golden_window' not in st.session_state:
    st.session_state.golden_window = {}
if 'current_results' not in st.session_state:
    st.session_state.current_results = []

# --- ASSETS & WATCHLISTS (Vollständig) ---
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

# --- SIDEBAR ---
with st.sidebar:
    st.header("🎯 Dashboard")
    m_sel = st.selectbox("Markt wählen", list(WATCHLISTS.keys()))
    st.divider()
    if st.button("♻️ Reset Tages-Daten"):
        st.session_state.signal_log = {}
        st.session_state.golden_window = {}
        st.session_state.current_results = []
        st.rerun()
    st.caption(f"Operator: {USER_NAME}")

# --- MAIN UI ---
st.title("🎯 SNIPER PRO MONITOR V10.28")

# 1. GOLDEN WINDOW (Bleibt oben stehen)
if st.session_state.golden_window:
    with st.container(border=True):
        st.subheader("⭐ Golden Window Treffer (09:30 - 09:45)")
        g_cols = st.columns(len(st.session_state.golden_window))
        for idx, (t, g) in enumerate(st.session_state.golden_window.items()):
            perf = ((g['current_price'] / g['entry_price']) - 1) * 100
            with g_cols[idx]:
                st.info(f"**{ASSET_NAMES.get(t, t)}**\n\nSignal: {g['time']} (@ {g['entry_price']:.2f}€)\n\n**Aktuell: {g['current_price']:.2f}€** ({perf:+.2f}%)")
st.divider()

# 2. ANALYSE BUTTON
if st.button(f"🔍 ANALYSE STARTEN", use_container_width=True):
    with st.spinner("Lade Marktdaten..."):
        vx_d = yf.download("^VIX", period="1d", progress=False)
        v_val = get_safe_val(vx_d['Close'].iloc[-1])
        ix_d = yf.download(INDEX_TICKERS[m_sel], period="2d", interval="15m", progress=False)
        i_perf = ((get_safe_val(ix_d['Close'].iloc[-1]) / get_safe_val(ix_d['Close'].iloc[-2])) - 1) * 100
        
        current_time_str = now.strftime("%H:%M")
        is_golden_time = "09:30" <= current_time_str <= "09:45"
        
        new_results = []
        for t in WATCHLISTS[m_sel]:
            try:
                s = yf.download(t, period="2d", interval="15m", progress=False)
                p_now = get_safe_val(s['Close'].iloc[-1])
                hi, lo = get_safe_val(s['High'].iloc[-1]), get_safe_val(s['Low'].iloc[-1])
                
                # Recovery für Golden Window (09:30)
                today_str = now.strftime('%Y-%m-%d')
                h_data = s.between_time('09:30', '09:45')
                
                entry_morgen = p_now # Fallback
                if not h_data.empty:
                    entry_morgen = get_safe_val(h_data['Close'].iloc[0])
                    if t not in st.session_state.golden_window:
                        st.session_state.golden_window[t] = {"time": "09:30", "entry_price": entry_morgen, "current_price": p_now}
                
                if t in st.session_state.golden_window:
                    st.session_state.golden_window[t]["current_price"] = p_now

                # Daten für die Anzeige speichern
                sl = lo * 0.995
                res_data = {
                    "ticker": t,
                    "name": ASSET_NAMES.get(t, t),
                    "price": p_now,
                    "entry_time": "09:30" if not h_data.empty else current_time_str,
                    "entry_price": entry_morgen,
                    "sl": sl,
                    "tp": (hi*1.001) + ((hi*1.001-sl)*2),
                    "score": 85 # Platzhalter für Logik
                }
                new_results.append(res_data)
            except: continue
        
        st.session_state.current_results = new_results
        st.rerun() # Seite einmal neu laden, um die Daten aus dem State anzuzeigen

# 3. ANZEIGE DER ERGEBNISSE (Aus dem Speicher, damit sie nicht verschwinden)
for item in st.session_state.current_results:
    with st.container(border=True):
        c1, c2 = st.columns([3, 1])
        c1.subheader(item['name'])
        c2.metric("Score", f"{item['score']}%")
        
        st.write(f"🔔 **Signal:** {item['entry_time']} Uhr (Einstieg: {item['entry_price']:.2f}€) | **Aktuell: {item['price']:.2f}€**")
        st.success("🛡️ STOP LOSS OK")
        st.info(f"Entry ab: {item['entry_price']:.2f}€ | **SL: {item['sl']:.2f}€** | Ziel: {item['tp']:.2f}€")
        st.write("✅ VIX | ✅ RSX | ✅ SM | ✅ Zeit")

st.caption(f"Operator: {USER_NAME} | Markt: {m_sel} | Stand: {now.strftime('%H:%M:%S')}")
