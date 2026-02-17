import streamlit as st
import pandas as pd
import yfinance as yf
from datetime import datetime
import pytz

# --- SETUP ---
st.set_page_config(page_title="Sniper V10.26", page_icon="🎯", layout="wide")
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
        
        # Historische Daten für Golden Window Check (Heute Morgen)
        today_str = datetime.now().strftime('%Y-%m-%d')
        h_data = s.loc[today_str].between_time('09:30', '09:45') if today_str in s.index.get_level_values(0).strftime('%Y-%m-%d') else pd.DataFrame()
        
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
        sl_status = f"🛑 STOP LOSS ERREICHT" if p <= sl else "🛡️ SL OK"
        
        return {"score": score, "price": p, "entry": entry, "sl": sl, "tp": tp, "checks": checks, "t": ticker, "sl_status": sl_status, "h_data": h_data}
    except: return None

# --- SIDEBAR ---
with st.sidebar:
    st.header("🎯 Dashboard")
    m_sel = st.selectbox("Markt wählen", list(WATCHLISTS.keys()))
    st.divider()
    st.subheader("📊 Signal-Log")
    for t, data in st.session_state.signal_log.items():
        with st.expander(f"{ASSET_NAMES.get(t, t)} ({data['time']})"):
            st.write(f"🟢 **Kauf:** {data['price']:.2f}€")
            if data.get("exit_triggered"):
                st.write(f"🟠 **Verkauf:** {data['exit_time']} (@ {data['exit_price']:.2f}€)")
    if st.button("♻️ Reset"):
        st.session_state.signal_log = {}
        st.session_state.golden_window = {}
        st.rerun()

# --- MAIN UI ---
st.title("🎯 SNIPER PRO MONITOR V10.26")

# --- 1. GOLDEN WINDOW ANZEIGE ---
if st.session_state.golden_window:
    with st.container(border=True):
        st.subheader("⭐ Golden Window Treffer (09:30 - 09:45)")
        g_cols = st.columns(len(st.session_state.golden_window))
        for idx, (t, g) in enumerate(st.session_state.golden_window.items()):
            perf = ((g['current_price'] / g['entry_price']) - 1) * 100
            g_cols[idx].info(f"**{ASSET_NAMES.get(t, t)}**\n\nSignal: {g['time']} (@ {g['entry_price']:.2f}€)\n\n**Aktuell: {g['current_price']:.2f}€** ({perf:+.2f}%)")
st.divider()

# --- 2. ANALYSE ---
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
            # GOLDEN WINDOW LOGIK (MIT HISTORIE-RECOVERY)
            if not data['h_data'].empty:
                # Wir simulieren den Fund von heute Morgen, falls wir jetzt erst einschalten
                h_p = get_safe_val(data['h_data']['Close'].iloc[0])
                if t not in st.session_state.golden_window:
                    st.session_state.golden_window[t] = {"time": "09:30", "entry_price": h_p, "current_price": data['price']}
            
            # Live-Update für Golden Window
            if t in st.session_state.golden_window:
                st.session_state.golden_window[t].update({"current_price": data['price']})
            
            # Normales Logging
            if data['score'] >= 80 and t not in st.session_state.signal_log:
                st.session_state.signal_log[t] = {"time": current_time_str, "price": data['price'], "exit_triggered": False}
            
            res.append(data)

    for item in sorted(res, key=lambda x: x['score'], reverse=True):
        with st.container(border=True):
            h1, h2 = st.columns([3, 1])
            h1.subheader(ASSET_NAMES.get(item['t'], item['t']))
            h2.metric("Score", f"{item['score']}%")
            
            sig = st.session_state.signal_log.get(item['t'])
            if sig:
                st.write(f"🔔 **Signal:** {sig['time']} Uhr (Einstieg: {sig['price']:.2f}€) | **Aktuell: {item['price']:.2f}€**")

            if "ERREICHT" in item['sl_status']:
                st.error(item['sl_status'])
            else:
                st.success(item['sl_status'])
            
            st.info(f"Entry ab: {item['entry']:.2f}€ | **SL: {item['sl']:.2f}€** | Ziel: {item['tp']:.2f}€")
            
            ch = item['checks']
            c1, c2, c3, c4 = st.columns(4)
            c1.write(f"{'✅' if ch['VIX'] else '❌'} VIX")
            c2.write(f"{'✅' if ch['RSX'] else '❌'} RSX")
            c3.write(f"{'✅' if ch['SM'] else '❌'} SM")
            c4.write(f"{'✅' if ch['TIME'] else '❌'} Zeit")

st.caption(f"Operator: {USER_NAME} | {now.strftime('%H:%M:%S')}")
