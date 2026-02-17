import streamlit as st
import pandas as pd
import yfinance as yf
from datetime import datetime
import pytz

# --- SETUP ---
st.set_page_config(page_title="Sniper V10.0 Pro", page_icon="🎯", layout="centered")
cet = pytz.timezone('Europe/Berlin')
now = datetime.now(cet)

USER_NAME = "Kraus Markus"

ASSET_NAMES = {
    "SAP.DE": "SAP", "MUV2.DE": "Münchener Rück", "ALV.DE": "Allianz", "SIE.DE": "Siemens", "ENR.DE": "Siemens Energy",
    "AAPL": "Apple", "MSFT": "Microsoft", "NVDA": "NVIDIA", "AMZN": "Amazon", "GOOGL": "Alphabet",
    "TSLA": "Tesla", "META": "Meta", "AVGO": "Broadcom", "COST": "Costco", "NFLX": "Netflix"
}
WATCHLISTS = {
    "DAX 🇩🇪": ["SAP.DE", "MUV2.DE", "ALV.DE", "SIE.DE", "ENR.DE"],
    "S&P 500 🇺🇸": ["AAPL", "MSFT", "AMZN", "GOOGL", "META"],
    "Nasdaq 🚀": ["NVDA", "TSLA", "AVGO", "COST", "NFLX"]
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
        
        # --- SCORE LOGIK ---
        score = 0
        v_ok = vix <= 22.5; score += 20 if v_ok else 0
        r_now = ((p/prev_p)-1)*100 - idx_p
        r_ok = r_now > 0; score += 30 if r_ok else 0
        sm = (p - lo) / (hi - lo) if hi != lo else 0.5
        s_ok = sm > 0.72; score += 30 if s_ok else 0
        t_ok = not ((now.hour == 11 and now.minute >= 30) or (now.hour == 12) or (now.hour == 13 and now.minute < 30))
        score += 20 if t_ok else 0
        
        # --- EINSTIEGS-BERECHNUNG ---
        # Einstieg: 0.1% über dem aktuellen Hoch (Bestätigung des Momentums)
        entry = hi * 1.001 
        # Stop-Loss: 0.5% unter dem aktuellen Tief (eng, aber Sniper-Stil)
        sl = lo * 0.995
        # Ziel: Risiko x 2 (CRV 2.0)
        risk = entry - sl
        tp = entry + (risk * 2)
        
        return {
            "score": score, "price": p, "entry": entry, "sl": sl, "tp": tp,
            "icons": f"VIX:{'✅' if v_ok else '⚠️'} | RSX:{'🔥' if r_ok else '❄️'} | SM:{'💎' if s_ok else '➖'} | T:{'🕒' if t_ok else '⏳'}"
        }
    except: return None

# --- UI ---
st.title("🎯 SNIPER V10.0 PRO-ENTRY")

with st.sidebar:
    st.header("⚙️ Settings")
    c_in = st.text_input("Kapital (€)", value=str(st.session_state.capital))
    if st.button("Save"): st.session_state.capital = float(c_in)
    m_sel = st.selectbox("Markt", list(WATCHLISTS.keys()))
    st.metric("Budget", f"{st.session_state.capital:,.2f} €")
    st.caption(f"Operator: {USER_NAME}")

if st.button(f"🔍 SCAN & CALCULATE ENTRIES", use_container_width=True):
    vx_d = yf.download("^VIX", period="1d", progress=False)
    v_val = get_safe_val(vx_d['Close'].iloc[-1])
    ix_d = yf.download(INDEX_TICKERS[m_sel], period="2d", interval="15m", progress=False)
    i_perf = ((get_safe_val(ix_d['Close'].iloc[-1]) / get_safe_val(ix_d['Close'].iloc[-2])) - 1) * 100
    
    res = []
    for t in WATCHLISTS[m_sel]:
        data = calc_pro_entry(t, v_val, i_perf)
        if data and data['score'] > 0:
            data['t'] = t
            res.append(data)
    
    res = sorted(res, key=lambda x: x['score'], reverse=True)
    
    for item in res:
        qty = (st.session_state.capital * 0.01) / (item['entry'] - item['sl'])
        with st.container(border=True):
            c1, c2 = st.columns([2, 1])
            with c1:
                st.subheader(ASSET_NAMES.get(item['t'], item['t']))
                st.write(f"**Kurs:** {item['price']:.2f} €")
            with c2:
                st.metric("Score", f"{item['score']}%")
            
            # Einstiegs-Box
            st.info(f"👉 **ENTRY:** {item['entry']:.2f} € | **QTY:** {int(qty)} Stk")
            
            # SL / TP Zeile
            col_a, col_b = st.columns(2)
            col_a.error(f"STP: {item['sl']:.2f} €")
            col_b.success(f"TGT: {item['tp']:.2f} €")
            
            st.caption(item['icons'])

st.divider()
st.caption(f"Letzter Scan: {now.strftime('%H:%M:%S')} | Operator: {USER_NAME}")
