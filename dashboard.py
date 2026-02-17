import streamlit as st
import pandas as pd
import yfinance as yf
from datetime import datetime
import pytz

# --- CONFIG ---
st.set_page_config(page_title="Sniper V9.9 Sorted", layout="centered")
cet = pytz.timezone('Europe/Berlin')
now = datetime.now(cet)

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

def calc_hps(ticker, vix, idx_p):
    try:
        s = yf.download(ticker, period="2d", interval="15m", progress=False)
        if len(s) < 3: return 0, 0, ""
        p, p_p, p_o = get_safe_val(s['Close'].iloc[-1]), get_safe_val(s['Close'].iloc[-2]), get_safe_val(s['Close'].iloc[-3])
        hi, lo = get_safe_val(s['High'].iloc[-1]), get_safe_val(s['Low'].iloc[-1])
        
        score = 0
        v_ok = vix <= 22.5; score += 20 if v_ok else 0
        r_now = ((p/p_p)-1)*100 - idx_p
        r_pre = ((p_p/p_o)-1)*100 - idx_p
        r_ok = r_now > 0 and (r_now + r_pre) > -0.1; score += 30 if r_ok else 0
        sm = (p - lo) / (hi - lo) if hi != lo else 0.5
        s_ok = sm > 0.72; score += 30 if s_ok else 0
        t_ok = not ((now.hour == 11 and now.minute >= 30) or (now.hour == 12) or (now.hour == 13 and now.minute < 30))
        score += 20 if t_ok else 0
        
        icons = f"VIX:{'✅' if v_ok else '⚠️'} | RSX:{'🔥' if r_ok else '❄️'} | SM:{'💎' if s_ok else '➖'} | T:{'🕒' if t_ok else '⏳'}"
        return score, p, icons
    except: return 0, 0, ""

# --- UI ---
st.title("⚡ SNIPER V9.9 SORTED")

with st.sidebar:
    st.header("⚙️ Setup")
    c_in = st.text_input("Kapital (€)", value=str(st.session_state.capital))
    if st.button("Save"): st.session_state.capital = float(c_in)
    m_sel = st.selectbox("Markt", list(WATCHLISTS.keys()))
    st.metric("Budget", f"{st.session_state.capital:,.2f} €")

if st.button(f"🔍 SCAN {m_sel}", use_container_width=True):
    try:
        vx_d = yf.download("^VIX", period="1d", progress=False)
        v_val = get_safe_val(vx_d['Close'].iloc[-1])
        ix_d = yf.download(INDEX_TICKERS[m_sel], period="2d", interval="15m", progress=False)
        i_perf = ((get_safe_val(ix_d['Close'].iloc[-1]) / get_safe_val(ix_d['Close'].iloc[-2])) - 1) * 100
        st.caption(f"VIX: {v_val:.2f} | Index: {i_perf:+.2f}%")
        
        res = []
        for t in WATCHLISTS[m_sel]:
            sc, pr, ico = calc_hps(t, v_val, i_perf)
            if sc > 0: res.append({"t": t, "s": sc, "p": pr, "i": ico})
        
        # Sortierung
        res = sorted(res, key=lambda x: x['s'], reverse=True)
        
        for item in res:
            qty = (st.session_state.capital * 0.01) / (item['p'] * 0.015)
            with st.container(border=True):
                col1, col2 = st.columns([3, 1])
                with col1:
                    st.subheader(ASSET_NAMES.get(item['t'], item['t']))
                    st.write(f"**{item['p']:.2f} €** | Stück: {int(qty)}")
                with col2:
                    st.metric("Score", f"{item['s']}%")
                st.write(item['i'])
    except: st.error("Fehler beim Datenabruf. Bitte erneut versuchen.")

st.divider()
st.caption(f"Letzter Scan: {now.strftime('%H:%M:%S')} | Rank-Mode")
