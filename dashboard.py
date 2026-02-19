import streamlit as st
import pandas as pd
import yfinance as yf
from datetime import datetime
import pytz

# --- SETUP ---
st.set_page_config(page_title="Sniper V10.29", page_icon="🎯", layout="wide")
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
        
        entry = hi * 1.001
        sl = lo * 0.995
        tp = entry + ((entry - sl) * 2)
        sl_status = "STOP LOSS OK" if p > sl else "STOP LOSS ERREICHT"
        
        return {"score": score, "price": p, "entry": entry, "sl": sl, "tp": tp, "checks": checks, "t": ticker, "sl_status": sl_status, "hist": s}
    except: return None

# --- SIDEBAR ---
with st.sidebar:
    st.header("🎯 Sniper Dashboard")
    m_sel = st.selectbox("Markt wählen", list(WATCHLISTS.keys()))
    st.divider()
    st.subheader("📊 Signal-Log")
    for t, data in st.session_state.signal_log.items():
        with st.expander(f"{ASSET_NAMES.get(t, t)} ({data['time']})"):
            st.write(f"🟢 Kauf: {data['price']:.2f}€")
            if data.get("exit"): st.write(f"🟠 Verkauf: {data['exit_t']} (@ {data['exit_p']:.2f}€)")
    st.divider()
    if st.button("♻️ Reset"):
        st.session_state.signal_log = {}, st.session_state.golden_window = {}, st.session_state.current_results = []
        st.rerun()

# --- MAIN UI ---
st.title("🎯 SNIPER PRO MONITOR V10.29")

# 1. GOLDEN WINDOW
if st.session_state.golden_window:
    with st.container(border=True):
        st.subheader("⭐ Golden Window Treffer (09:30 - 09:45)")
        g_cols = st.columns(len(st.session_state.golden_window))
        for idx, (t, g) in enumerate(st.session_state.golden_window.items()):
            perf = ((g['curr'] / g['entry']) - 1) * 100
            g_cols[idx].info(f"**{ASSET_NAMES.get(t, t)}**\n\nSignal: {g['time']} (@ {g['entry']:.2f}€)\n\n**Aktuell: {g['curr']:.2f}€** ({perf:+.2f}%)")
st.divider()

# 2. ANALYSE
if st.button(f"🔍 ANALYSE STARTEN", use_container_width=True):
    vx_d = yf.download("^VIX", period="1d", progress=False)
    v_val = get_safe_val(vx_d['Close'].iloc[-1])
    ix_d = yf.download(INDEX_TICKERS[m_sel], period="2d", interval="15m", progress=False)
    i_perf = ((get_safe_val(ix_d['Close'].iloc[-1]) / get_safe_val(ix_d['Close'].iloc[-2])) - 1) * 100
    
    current_time_str = now.strftime("%H:%M")
    is_golden_time = "09:30" <= current_time_str <= "09:45"
    
    temp_results = []
    for t in WATCHLISTS[m_sel]:
        res = calc_pro_entry(t, v_val, i_perf, m_sel)
        if res:
            # Golden Window Recovery & Live
            h_data = res['hist'].between_time('09:30', '09:45')
            if not h_data.empty:
                entry_930 = get_safe_val(h_data['Close'].iloc[0])
                if t not in st.session_state.golden_window:
                    st.session_state.golden_window[t] = {"time": "09:30", "entry": entry_930, "curr": res['price']}
            if t in st.session_state.golden_window:
                st.session_state.golden_window[t]["curr"] = res['price']

            # Logs
            if res['score'] >= 80 and t not in st.session_state.signal_log:
                st.session_state.signal_log[t] = {"time": current_time_str, "price": res['price']}
            
            temp_results.append(res)
    
    st.session_state.current_results = temp_results
    st.rerun()

# 3. ANZEIGE (Dauerhaft)
for item in sorted(st.session_state.current_results, key=lambda x: x['score'], reverse=True):
    with st.container(border=True):
        c1, c2 = st.columns([3, 1])
        c1.subheader(ASSET_NAMES.get(item['t'], item['t']))
        c2.metric("HPS Score", f"{item['score']}%")
        
        # Signal-Zeile
        sig = st.session_state.signal_log.get(item['t'], {"time": "Scan", "price": item['price']})
        st.write(f"🔔 **Signal:** {sig['time']} Uhr (Einstieg: {sig['price']:.2f}€) | **Aktuell: {item['price']:.2f}€**")
        
        # SL Status
        if "ERREICHT" in item['sl_status']: st.error(f"🛑 {item['sl_status']}")
        else: st.success(f"🛡️ {item['sl_status']}")
        
        # Trading Plan
        st.info(f"Entry ab: {item['entry']:.2f}€ | **SL: {item['sl']:.2f}€** | Ziel: {item['tp']:.2f}€")
        
        # Kriterien
        ch = item['checks']
        cols = st.columns(4)
        cols[0].write(f"{'✅' if ch['VIX'] else '❌'} VIX")
        cols[1].write(f"{'✅' if ch['RSX'] else '❌'} RSX")
        cols[2].write(f"{'✅' if ch['SM'] else '❌'} SM")
        cols[3].write(f"{'✅' if ch['TIME'] else '❌'} ZEIT")

st.caption(f"Operator: {USER_NAME} | V10.29 | Stand: {now.strftime('%H:%M:%S')}")
