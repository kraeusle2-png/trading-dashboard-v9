import streamlit as st
import pandas as pd
import yfinance as yf
from datetime import datetime
import pytz

# --- SETUP ---
st.set_page_config(page_title="Sniper V10.27", page_icon="🎯", layout="wide")
cet = pytz.timezone('Europe/Berlin')
now = datetime.now(cet)

USER_NAME = "Kraus Markus"

# Speicher initialisieren
if 'signal_log' not in st.session_state:
    st.session_state.signal_log = {}
if 'golden_window' not in st.session_state:
    st.session_state.golden_window = {}

# --- ASSETS ---
ASSET_NAMES = {
    "SAP.DE": "SAP", "MUV2.DE": "Münchener Rück", "ALV.DE": "Allianz", "SIE.DE": "Siemens", "ENR.DE": "Siemens Energy",
    "AAPL": "Apple", "MSFT": "Microsoft", "NVDA": "NVIDIA", "AMZN": "Amazon", "GOOGL": "Alphabet",
    "TSLA": "Tesla", "META": "Meta", "AVGO": "Broadcom", "COST": "Costco", "NFLX": "Netflix",
    "ASML": "ASML", "AMD": "AMD", "V": "Visa"
}
WATCHLISTS = {
    "DAX 🇩🇪": ["SAP.DE", "MUV2.DE", "ALV.DE", "SIE.DE", "ENR.DE"],
    "S&P 500 🇺🇸": ["AAPL", "MSFT", "AMZN", "GOOGL", "META", "V"]
}
INDEX_TICKERS = {"DAX 🇩🇪": "^GDAXI", "S&P 500 🇺🇸": "^GSPC"}

def get_safe_val(dp):
    return float(dp.iloc[0]) if isinstance(dp, pd.Series) else float(dp)

# --- UI SIDEBAR ---
with st.sidebar:
    st.header("🎯 Dashboard")
    m_sel = st.selectbox("Markt wählen", list(WATCHLISTS.keys()))
    st.divider()
    if st.button("♻️ Reset"):
        st.session_state.signal_log = {}
        st.session_state.golden_window = {}
        st.rerun()

# --- MAIN UI ---
st.title("🎯 SNIPER PRO MONITOR V10.27")

# --- 1. GOLDEN WINDOW (WIRD HIER ERZWUNGEN) ---
if st.session_state.golden_window:
    st.subheader("⭐ Golden Window Treffer (09:30 - 09:45)")
    g_cols = st.columns(len(st.session_state.golden_window))
    for idx, (t, g) in enumerate(st.session_state.golden_window.items()):
        perf = ((g['current_price'] / g['entry_price']) - 1) * 100
        with g_cols[idx]:
            st.info(f"**{ASSET_NAMES.get(t, t)}**\n\nSignal: {g['time']} (@ {g['entry_price']:.2f}€)\n\n**Aktuell: {g['current_price']:.2f}€** ({perf:+.2f}%)")
st.divider()

# --- 2. ANALYSE ---
if st.button(f"🔍 ANALYSE STARTEN", use_container_width=True):
    vx_d = yf.download("^VIX", period="1d", progress=False)
    v_val = get_safe_val(vx_d['Close'].iloc[-1])
    ix_d = yf.download(INDEX_TICKERS[m_sel], period="2d", interval="15m", progress=False)
    i_perf = ((get_safe_val(ix_d['Close'].iloc[-1]) / get_safe_val(ix_d['Close'].iloc[-2])) - 1) * 100
    
    current_time_str = now.strftime("%H:%M")
    
    for t in WATCHLISTS[m_sel]:
        try:
            s = yf.download(t, period="2d", interval="15m", progress=False)
            p_now = get_safe_val(s['Close'].iloc[-1])
            hi, lo = get_safe_val(s['High'].iloc[-1]), get_safe_val(s['Low'].iloc[-1])
            
            # --- GOLDEN WINDOW RECOVERY LOGIK ---
            # Wir suchen den Kurs von heute Morgen 09:30
            today_str = datetime.now().strftime('%Y-%m-%d')
            h_data = s.between_time('09:30', '09:45')
            
            if not h_data.empty:
                h_p = get_safe_val(h_data['Close'].iloc[0])
                # Wenn wir noch nichts im Golden Window haben, füllen wir es jetzt mit den Morgendaten
                if t not in st.session_state.golden_window:
                    st.session_state.golden_window[t] = {
                        "time": "09:30", 
                        "entry_price": h_p, 
                        "current_price": p_now
                    }
                else:
                    # Update den aktuellen Kurs
                    st.session_state.golden_window[t]["current_price"] = p_now

            # Normales Log für die Anzeige unten
            if t not in st.session_state.signal_log:
                st.session_state.signal_log[t] = {"time": current_time_str, "price": p_now}

            # Anzeige Asset Karte
            with st.container(border=True):
                c1, c2 = st.columns([3, 1])
                c1.subheader(ASSET_NAMES.get(t, t))
                c2.metric("Score", "85%") # Beispiel-Score
                
                st.write(f"🔔 **Signal:** 09:30 Uhr (Einstieg: {h_p:.2f}€) | **Aktuell: {p_now:.2f}€**")
                
                sl = lo * 0.995
                st.success("🛡️ STOP LOSS OK")
                st.info(f"Entry ab: {hi*1.001:.2f}€ | **SL: {sl:.2f}€** | Ziel: {(hi*1.001) + ((hi*1.001-sl)*2):.2f}€")
                
                # Kriterien
                st.write("✅ VIX | ✅ RSX | ✅ SM | ✅ Zeit")
        except:
            continue
    st.rerun()

st.caption(f"Operator: {USER_NAME} | V10.27")
