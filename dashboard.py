import streamlit as st
import pandas as pd
import yfinance as yf
from datetime import datetime
import pytz

# --- SETUP ---
st.set_page_config(page_title="Sniper V10.1 Pro", page_icon="🎯", layout="centered")
cet = pytz.timezone('Europe/Berlin')
now = datetime.now(cet)

USER_NAME = "Kraus Markus"

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

if 'capital' not in st.session_state: st.session_state.capital = 3836.29

def get_safe_val(dp):
    return float(dp.iloc[0]) if isinstance(dp, pd.Series) else float(dp)

def calc_pro_entry(ticker, vix, idx_p):
    try:
        s = yf.download(ticker, period="2d", interval="15m", progress=False)
        if len(s) < 3: return None
        
        p = get_safe_val(s['Close'].iloc[-1])
        hi = get_safe_val(s['High'].iloc[-1])
        lo = get_safe_val(s['Low'].iloc[-1])
        prev_p = get_safe_val(s['Close'].iloc[-2])
        
        # --- EINZELPRÜFUNG ---
        checks = {}
        score = 0
        
        # 1. VIX (Marktangst)
        checks['VIX'] = vix <= 22.5
        if checks['VIX']: score += 20
        
        # 2. RSX (Relative Stärke zum Index)
        r_now = ((p/prev_p)-1)*100 - idx_p
        checks['RSX'] = r_now > 0
        if checks['RSX']: score += 30
        
        # 3. Smart Money (Starker Schluss im 15m Chart)
        sm = (p - lo) / (hi - lo) if hi != lo else 0.5
        checks['SM'] = sm > 0.72
        if checks['SM']: score += 30
        
        # 4. Timing (Keine Mittagspause)
        is_lunch = (now.hour == 11 and now.minute >= 30) or (now.hour == 12) or (now.hour == 13 and now.minute < 30)
        checks['TIME'] = not is_lunch
        if checks['TIME']: score += 20
        
        # Einstiegsdaten
        entry = hi * 1.001 
        sl = lo * 0.995
        tp = entry + ((entry - sl) * 2)
        
        return {
            "score": score, "price": p, "entry": entry, "sl": sl, "tp": tp,
            "checks": checks, "t": ticker
        }
    except: return None

# --- UI ---
st.title("🎯 SNIPER V10.1")

with st.sidebar:
    st.header("⚙️ Settings")
    c_in = st.text_input("Kapital (€)", value=str(st.session_state.capital))
    if st.button("Save"): st.session_state.capital = float(c_in)
    m_sel = st.selectbox("Markt", list(WATCHLISTS.keys()))
    st.metric("Budget", f"{st.session_state.capital:,.2f} €")
    st.caption(f"Operator: {USER_NAME}")

if st.button(f"🔍 ANALYSE STARTEN", use_container_width=True):
    vx_d = yf.download("^VIX", period="1d", progress=False)
    v_val = get_safe_val(vx_d['Close'].iloc[-1])
    ix_d = yf.download(INDEX_TICKERS[m_sel], period="2d", interval="15m", progress=False)
    i_perf = ((get_safe_val(ix_d['Close'].iloc[-1]) / get_safe_val(ix_d['Close'].iloc[-2])) - 1) * 100
    
    st.info(f"Markt-Status: VIX @ {v_val:.2f} | Index {m_sel}: {i_perf:+.2f}%")
    
    res = []
    for t in WATCHLISTS[m_sel]:
        data = calc_pro_entry(t, v_val, i_perf)
        if data and data['score'] > 0:
            res.append(data)
    
    res = sorted(res, key=lambda x: x['score'], reverse=True)
    
    for item in res:
        qty = (st.session_state.capital * 0.01) / (item['entry'] - item['sl'])
        with st.container(border=True):
            # Header Zeile
            col1, col2 = st.columns([2, 1])
            with col1:
                st.subheader(ASSET_NAMES.get(item['t'], item['t']))
            with col2:
                st.metric("HPS Score", f"{item['score']}%")
            
            # --- NEUE KRITERIEN ANZEIGE ---
            c = item['checks']
            check_line = (
                f"{'✅' if c['VIX'] else '❌'} VIX | "
                f"{'🔥' if c['RSX'] else '❄️'} RSX | "
                f"{'💎' if c['SM'] else '➖'} SmartMoney | "
                f"{'🕒' if c['TIME'] else '⏳'} Timing"
            )
            st.write(check_line)
            
            # Einstiegs-Details
            st.info(f"**ENTRY:** {item['entry']:.2f} € | **STÜCK:** {int(qty)}")
            
            # SL / TP
            ca, cb = st.columns(2)
            ca.error(f"Stop: {item['sl']:.2f} €")
            cb.success(f"Ziel: {item['tp']:.2f} €")

st.divider()
st.caption(f"Letzter Scan: {now.strftime('%H:%M:%S')} | Operator: {USER_NAME}")
