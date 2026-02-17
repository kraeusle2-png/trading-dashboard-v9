import streamlit as st
import pandas as pd
import yfinance as yf
from datetime import datetime
import pytz

# --- SETUP ---
st.set_page_config(page_title="Sniper V10.19", page_icon="🎯", layout="centered")
cet = pytz.timezone('Europe/Berlin')
now = datetime.now(cet)

USER_NAME = "Kraus Markus"

# Speicher initialisieren
if 'signal_log' not in st.session_state:
    st.session_state.signal_log = {}
if 'golden_window' not in st.session_state:
    st.session_state.golden_window = {}

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

# --- LOGIK ---
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
    st.header("⚙️ Sniper Setup")
    m_sel = st.selectbox("Markt wählen", list(WATCHLISTS.keys()))
    
    if st.button("♻️ Reset Tages-Daten"):
        st.session_state.signal_log = {}
        st.session_state.golden_window = {}
        st.rerun()
        
    st.divider()
    st.subheader("📊 Signal-Log (Heute)")
    if not st.session_state.signal_log:
        st.caption("Noch keine Signale.")
    else:
        for t, d in st.session_state.signal_log.items():
            st.write(f"🔔 {ASSET_NAMES.get(t, t)}: {d['time']} Uhr")

# --- MAIN UI ---
st.title("🎯 SNIPER MONITOR V10.19")

# 1. GOLDEN WINDOW (Oben fixiert)
if st.session_state.golden_window:
    with st.container(border=True):
        st.subheader("⭐ GOLDEN WINDOW TREFFER (09:30 - 09:45)")
        for t, g in st.session_state.golden_window.items():
            st.success(f"**{ASSET_NAMES.get(t, t)}**: Signal um {g['time']} Uhr bei {g['price']:.2f} € (Score: {g['score']}%)")
st.divider()

# 2. ANALYSE STARTEN
if st.button(f"🔍 ANALYSE STARTEN ({m_sel})", use_container_width=True):
    vx_d = yf.download("^VIX", period="1d", progress=False)
    v_val = get_safe_val(vx_d['Close'].iloc[-1])
    ix_d = yf.download(INDEX_TICKERS[m_sel], period="2d", interval="15m", progress=False)
    i_perf = ((get_safe_val(ix_d['Close'].iloc[-1]) / get_safe_val(ix_d['Close'].iloc[-2])) - 1) * 100
    
    st.info(f"Marktumfeld: VIX {v_val:.2f} | {m_sel} Index {i_perf:+.2f}%")
    
    current_time_str = now.strftime("%H:%M")
    is_golden_hour = "09:30" <= current_time_str <= "09:45"
    
    res = []
    for t in WATCHLISTS[m_sel]:
        data = calc_pro_entry(t, v_val, i_perf, m_sel)
        if data:
            # Golden Window Logik
            if is_golden_hour and data['score'] >= 80:
                if t not in st.session_state.golden_window:
                    st.session_state.golden_window[t] = {"time": current_time_str, "price": data['price'], "score": data['score']}
            
            # Normales Signal Log
            if data['score'] >= 80 and t not in st.session_state.signal_log:
                st.session_state.signal_log[t] = {"time": current_time_str, "price": data['price']}
            
            res.append(data)
    
    # Anzeige der Assets
    for item in sorted(res, key=lambda x: x['score'], reverse=True):
        with st.container(border=True):
            c1, c2 = st.columns([2, 1])
            with c1:
                st.subheader(ASSET_NAMES.get(item['t'], item['t']))
                st.write(f"💹 Kurs: **{item['price']:.2f} €**")
            with c2:
                st.metric("HPS Score", f"{item['score']}%")
            
            # Einstiegshistorie anzeigen
            sig_data = st.session_state.signal_log.get(item['t'])
            if sig_data:
                st.write(f"🔔 **Signal geloggt:** {sig_data['time']} Uhr (@ {sig_data['price']:.2f} €)")

            # Stop Loss Status
            if "ERREICHT" in item['sl_status']:
                st.error(f"🛑 **STOP LOSS:** {item['sl_status']}")
            
            # Trading Plan
            st.info(f"Entry ab: {item['entry']:.2f} | SL: {item['sl']:.2f} | Ziel: {item['tp']:.2f}")
            
            # Kriterien Checks
            ch = item['checks']
            col_a, col_b, col_c, col_d = st.columns(4)
            col_a.write(f"{'✅' if ch['VIX'] else '❌'} VIX")
            col_b.write(f"{'✅' if ch['RSX'] else '❌'} RSX")
            col_c.write(f"{'✅' if ch['SM'] else '❌'} SM")
            col_d.write(f"{'✅' if ch['TIME'] else '❌'} ZEIT")

st.divider()
st.caption(f"Letzter Scan: {now.strftime('%H:%M:%S')} | Operator: {USER_NAME} | V10.19")
