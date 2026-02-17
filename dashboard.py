import streamlit as st
import pandas as pd
import yfinance as yf
from datetime import datetime
import pytz

# --- SETUP ---
st.set_page_config(page_title="Sniper V10.22", page_icon="🎯", layout="wide")
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
        sl_status = f"🛑 STOP LOSS ERREICHT (@ {now.strftime('%H:%M')})" if p <= sl else "🟢 SL OK"
        
        return {"score": score, "price": p, "entry": entry, "sl": sl, "tp": tp, "checks": checks, "t": ticker, "sl_status": sl_status}
    except: return None

# --- SIDEBAR: KLARE STRUKTUR ---
with st.sidebar:
    st.header("🎯 Dashboard")
    m_sel = st.selectbox("Markt wählen", list(WATCHLISTS.keys()))
    
    st.divider()
    st.subheader("📋 Tages-Log")
    if not st.session_state.signal_log:
        st.write("Warte auf Signale...")
    else:
        for t, data in st.session_state.signal_log.items():
            with st.expander(f"{ASSET_NAMES.get(t, t)} ({data['time']})"):
                st.write(f"**Kauf:** {data['price']:.2f}€")
                if data.get("exit_triggered"):
                    st.write(f"**Verkauf:** {data['exit_time']} (@ {data['exit_price']:.2f}€)")
                else:
                    st.write("Status: Halten")

    st.divider()
    if st.button("♻️ Reset"):
        st.session_state.signal_log = {}
        st.session_state.golden_window = {}
        st.rerun()
    st.caption(f"User: {USER_NAME}")

# --- MAIN UI ---
st.title("🎯 Sniper Monitor V10.22")

# 1. GOLDEN WINDOW BOX (Fixiert & Live)
if st.session_state.golden_window:
    st.markdown("### ⭐ Golden Window Live (09:30 - 09:45)")
    g_cols = st.columns(len(st.session_state.golden_window))
    for idx, (t, g) in enumerate(st.session_state.golden_window.items()):
        perf = ((g['current_price'] / g['entry_price']) - 1) * 100
        g_cols[idx].info(f"**{ASSET_NAMES.get(t, t)}**\n\nIn: {g['entry_price']:.2f}€\n\n**Aktuell: {g['current_price']:.2f}€** ({perf:+.2f}%)\n\nUpdate: {g['last_update']}")
st.divider()

# 2. ANALYSE
if st.button(f"🔍 ANALYSE STARTEN", use_container_width=True):
    vx_d = yf.download("^VIX", period="1d", progress=False)
    v_val = get_safe_val(vx_d['Close'].iloc[-1])
    ix_d = yf.download(INDEX_TICKERS[m_sel], period="2d", interval="15m", progress=False)
    i_perf = ((get_safe_val(ix_d['Close'].iloc[-1]) / get_safe_val(ix_d['Close'].iloc[-2])) - 1) * 100
    
    st.write(f"**Markt:** VIX {v_val:.2f} | Index {i_perf:+.2f}% | Zeit {now.strftime('%H:%M')}")
    
    current_time_str = now.strftime("%H:%M")
    is_golden_time = "09:30" <= current_time_str <= "09:45"
    
    res = []
    for t in WATCHLISTS[m_sel]:
        data = calc_pro_entry(t, v_val, i_perf, m_sel)
        if data:
            # Golden Window Sync
            if is_golden_time and data['score'] >= 80 and t not in st.session_state.golden_window:
                st.session_state.golden_window[t] = {"time": current_time_str, "entry_price": data['price'], "current_price": data['price'], "last_update": current_time_str}
            if t in st.session_state.golden_window:
                st.session_state.golden_window[t].update({"current_price": data['price'], "last_update": current_time_str})
            
            # Logs
            if data['score'] >= 80 and t not in st.session_state.signal_log:
                st.session_state.signal_log[t] = {"time": current_time_str, "price": data['price'], "exit_triggered": False}
            if t in st.session_state.signal_log and data['score'] < 80 and not st.session_state.signal_log[t].get("exit_triggered"):
                st.session_state.signal_log[t].update({"exit_time": current_time_str, "exit_price": data['price'], "exit_triggered": True})
            
            res.append(data)

    # Asset-Liste mit Stop Loss
    for item in sorted(res, key=lambda x: x['score'], reverse=True):
        with st.container(border=True):
            head1, head2 = st.columns([3, 1])
            head1.subheader(ASSET_NAMES.get(item['t'], item['t']))
            head2.metric("Score", f"{item['score']}%")
            
            # WICHTIG: STOP LOSS ZEILE
            if "ERREICHT" in item['sl_status']:
                st.error(item['sl_status'])
            else:
                st.success(item['sl_status'])
            
            # Trading Daten
            c1, c2, c3 = st.columns(3)
            c1.write(f"💹 Kurs: **{item['price']:.2f} €**")
            c2.write(f"🎯 Ziel: {item['tp']:.2f} €")
            c3.write(f"🛡️ Stop: **{item['sl']:.2f} €**")
            
            # Kriterien
            ch = item['checks']
            st.write(f"{'✅' if ch['VIX'] else '❌'} VIX | {'✅' if ch['RSX'] else '❌'} RSX | {'✅' if ch['SM'] else '❌'} SM | {'✅' if ch['TIME'] else '❌'} Zeit")

st.caption(f"V10.22 | Letzter Scan: {now.strftime('%H:%M:%S')} | Operator: {USER_NAME}")
