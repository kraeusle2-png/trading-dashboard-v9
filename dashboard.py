import streamlit as st
import pandas as pd
import yfinance as yf
from datetime import datetime
import pytz

# --- SETUP ---
st.set_page_config(page_title="Sniper V10.7", page_icon="🎯", layout="centered")
cet = pytz.timezone('Europe/Berlin')
now = datetime.now(cet)

USER_NAME = "Kraus Markus"

# Speicher für Signale (Asset -> {Zeit, Kurs})
if 'signal_log' not in st.session_state:
    st.session_state.signal_log = {}

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

if 'capital' not in st.session_state: 
    st.session_state.capital = 3836.29

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
        
        zeit_f = now.hour + now.minute / 60.0
        if "DAX" in markt:
            checks['TIME'] = (9.25 <= zeit_f <= 11.5) or (15.75 <= zeit_f <= 17.5)
        else:
            checks['TIME'] = (15.75 <= zeit_f <= 21.0)
        if checks['TIME']: score += 20
        
        entry, sl = hi * 1.001, lo * 0.995
        tp = entry + ((entry - sl) * 2)
        
        sl_hit = "Offen"
        if p <= sl:
            sl_hit = f"ERREICHT ({now.strftime('%H:%M')})"
            
        return {
            "score": score, "price": p, "entry": entry, "sl": sl, "tp": tp,
            "checks": checks, "t": ticker, "sl_status": sl_hit
        }
    except: return None

# --- UI ---
st.title("🎯 SNIPER V10.7 MONITOR")

with st.sidebar:
    st.header("⚙️ Settings")
    c_in = st.text_input("Kapital (€)", value=str(st.session_state.capital))
    if st.button("Speichern"): st.session_state.capital = float(c_in)
    m_sel = st.selectbox("Markt", list(WATCHLISTS.keys()))
    st.metric("Budget", f"{st.session_state.capital:,.2f} €")
    st.caption(f"Operator: {USER_NAME}")

if st.button(f"🔍 ANALYSE & MONITORING STARTEN", use_container_width=True):
    vx_d = yf.download("^VIX", period="1d", progress=False)
    v_val = get_safe_val(vx_d['Close'].iloc[-1])
    ix_d = yf.download(INDEX_TICKERS[m_sel], period="2d", interval="15m", progress=False)
    i_perf = ((get_safe_val(ix_d['Close'].iloc[-1]) / get_safe_val(ix_d['Close'].iloc[-2])) - 1) * 100
    
    res = []
    for t in WATCHLISTS[m_sel]:
        data = calc_pro_entry(t, v_val, i_perf, m_sel)
        if data:
            # Signal-Zeit UND Kurs loggen, wenn Score >= 80
            if data['score'] >= 80 and t not in st.session_state.signal_log:
                st.session_state.signal_log[t] = {
                    "time": now.strftime("%H:%M"),
                    "price": data['price']
                }
            res.append(data)
    
    res = sorted(res, key=lambda x: x['score'], reverse=True)
    
    for item in res:
        # Roter Kasten, wenn SL erreicht
        border_color = "red" if "ERREICHT" in item['sl_status'] else "normal"
        
        with st.container(border=True):
            col1, col2 = st.columns([2, 1])
            with col1:
                st.subheader(ASSET_NAMES.get(item['t'], item['t']))
                st.write(f"💹 **Aktueller Kurs: {item['price']:.2f} €**")
            with col2:
                st.metric("Score", f"{item['score']}%")
            
            # MONITORING ZEILE
            sig_data = st.session_state.signal_log.get(item['t'], None)
            if sig_data:
                sig_display = f"{sig_data['time']} Uhr (@ {sig_data['price']:.2f} €)"
            else:
                sig_display = "Offen"
            
            m_col1, m_col2 = st.columns(2)
            m_col1.write(f"🔔 **Signal:** {sig_display}")
            
            # SL Status mit Farbe
            if "ERREICHT" in item['sl_status']:
                m_col2.markdown(f"🛑 **SL:** <span style='color:red; font-weight:bold;'>{item['sl_status']}</span>", unsafe_allow_html=True)
            else:
                m_col2.write(f"🛑 **SL:** {item['sl_status']}")
            
            # Trading Plan
            st.info(f"**Einstieg ab:** {item['entry']:.2f} € | **STOP:** {item['sl']:.2f} € | **ZIEL:** {item['tp']:.2f} €")
            
            ch = item['checks']
            st.write(f"{'✅' if ch['VIX'] else '❌'} VIX | {'✅' if ch['RSX'] else '❌'} RSX | {'✅' if ch['SM'] else '❌'} SM | {'✅' if ch['TIME'] else '❌'} Zeit")

st.divider()
st.caption(f"Letzter Scan: {now.strftime('%H:%M:%S')} | Operator: {USER_NAME}")
