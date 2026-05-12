from __future__ import annotations
import math, os, json, threading, time, re
import numpy as np
import pandas as pd
import streamlit as st
from datetime import datetime, timedelta
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from streamlit_autorefresh import st_autorefresh

# ================= 1. CONFIG & PERSISTENCE =================
st.set_page_config(page_title="SMART WEALTH AI 5", layout="wide")

USER_FILE = "authorized_users.json"
SESSION_FILE = "session_login.json"
SETTINGS_FILE = "matrix_settings.json"

def load_json(file_path, default_val):
    if os.path.exists(file_path):
        try:
            with open(file_path, "r") as f: return json.load(f)
        except: pass
    return default_val

def save_json(file_path, data_to_save):
    try:
        with open(file_path, "w") as f: json.dump(data_to_save, f, indent=4)
    except: pass

ADMIN_DB = load_json(USER_FILE, {"9304768496": "Admin Chief", "7982046438": "Admin x"})
SUPER_ADMIN_IDS = ["9304768496", "7982046438"]

# Global Memory Storage for Persistence
@st.cache_resource
def get_global_memory():
    return {"ohlc": {}, "vol": {}, "hist_df": {}}

memory = get_global_memory()

if "is_auth" not in st.session_state: st.session_state.is_auth = False

if not st.session_state.is_auth and os.path.exists(SESSION_FILE):
    saved = load_json(SESSION_FILE, None)
    if saved and saved.get("user_id") in ADMIN_DB:
        st.session_state.is_auth, st.session_state.admin_name = True, ADMIN_DB[saved["user_id"]]
        st.session_state.current_user_id, st.session_state.is_super_admin = saved["user_id"], (saved["user_id"] in SUPER_ADMIN_IDS)

if not st.session_state.is_auth:
    st.markdown("<h1 style='text-align: center;'>🛡️ SMART WEALTH AI 5</h1>", unsafe_allow_html=True)
    _, col2, _ = st.columns([1, 1, 1])
    with col2:
        with st.form("Login"):
            user_key = st.text_input("Enter Mobile ID:", type="password")
            if st.form_submit_button("LOGIN"):
                if user_key in ADMIN_DB:
                    st.session_state.is_auth, st.session_state.admin_name = True, ADMIN_DB[user_key]
                    st.session_state.current_user_id, st.session_state.is_super_admin = user_key, (user_key in SUPER_ADMIN_IDS)
                    save_json(SESSION_FILE, {"user_id": user_key}); st.rerun()
                else: st.error("❌ Invalid Access ID")
    st.stop()

# ================= 2. ENGINE & SIDEBAR =================
st_autorefresh(interval=5000, key="v5_locked_production_master")

@st.cache_resource(show_spinner=False)
def get_engine():
    try:
        from nubra_python_sdk.marketdata.market_data import MarketData
        from nubra_python_sdk.start_sdk import InitNubraSdk, NubraEnv
        from nubra_python_sdk.ticker import websocketdata
        nubra = InitNubraSdk(NubraEnv.PROD, env_creds=True)
        def on_msg(msg):
            name = msg.get('indexname')
            if name:
                if "ticks" not in st.session_state: st.session_state.ticks = {}
                st.session_state.ticks[name] = msg
        socket = websocketdata.NubraDataSocket(client=nubra, on_index_data=on_msg)
        socket.connect()
        socket.subscribe(["NIFTY", "SENSEX", "BANKNIFTY"], data_type="index", exchange="NSE")
        threading.Thread(target=socket.keep_running, daemon=True).start()
        return MarketData(nubra)
    except: return None

md = get_engine()
if "ticks" not in st.session_state: st.session_state.ticks = {}

# Background collector for data persistence
def background_collector(symbol):
    while True:
        try:
            t_data = st.session_state.get('ticks', {}).get(symbol, {})
            l_px = t_data.get('index_value', 0) / 100
            if l_px > 0:
                if symbol not in memory["ohlc"]: memory["ohlc"][symbol] = []
                if symbol not in memory["vol"]: memory["vol"][symbol] = []
                if not memory["ohlc"][symbol] or memory["ohlc"][symbol][-1] != l_px:
                    memory["ohlc"][symbol].append(l_px)
                    memory["vol"][symbol].append(t_data.get('volume', 0))
                    if len(memory["ohlc"][symbol]) > 1000:
                        memory["ohlc"][symbol].pop(0); memory["vol"][symbol].pop(0)
            time.sleep(1)
        except: time.sleep(5)

if "worker_running" not in st.session_state:
    for s in ["NIFTY", "BANKNIFTY", "SENSEX"]:
        threading.Thread(target=background_collector, args=(s,), daemon=True).start()
    st.session_state.worker_running = True

matrix_settings = load_json(SETTINGS_FILE, {"last_index": "NIFTY"})
idx_list = ["NIFTY", "BANKNIFTY", "SENSEX"]
index_choice = st.sidebar.selectbox("Select Index", idx_list, index=idx_list.index(matrix_settings.get("last_index", "NIFTY")))
if index_choice != matrix_settings.get("last_index"): save_json(SETTINGS_FILE, {"last_index": index_choice})

if st.sidebar.button("🔒 LOGOUT"):
    if os.path.exists(SESSION_FILE): os.remove(SESSION_FILE)
    st.session_state.clear(); st.rerun()

if st.session_state.is_super_admin:
    with st.sidebar.expander("👥 User Management"):
        n_id, n_name = st.text_input("New ID"), st.text_input("Name")
        if st.button("ADD"):
            if n_id and n_name: ADMIN_DB[n_id] = n_name; save_json(USER_FILE, ADMIN_DB); st.rerun()
        u_rem = st.selectbox("Remove User", [f"{v} ({k})" for k, v in ADMIN_DB.items() if k != st.session_state.current_user_id])
        if st.button("DELETE"):
            uid_del = u_rem.split('(')[-1].replace(')', ''); del ADMIN_DB[uid_del]; save_json(USER_FILE, ADMIN_DB); st.rerun()

# ================= 3. RENDER CORE =================
try:
    target_exch = "BSE" if index_choice == "SENSEX" else "NSE"
    result = md.option_chain(index_choice, exchange=target_exch)
    chain = result.chain
    spot = chain.current_price / 100 if chain.current_price > 100000 else chain.current_price
    live_px = st.session_state.ticks.get(index_choice, {}).get('index_value', 0)/100 or spot
    
    ivl = 50 if index_choice == "NIFTY" else 100
    atm_val = int(round(live_px / ivl) * ivl)
    
    # Arrow Symbol Logic
    arrow = "▲" if live_px >= spot else "▼"

    # Header
    h_bg, h_txt = ("#e8f5e9", "#1b5e20") if live_px >= spot else ("#ffebee", "#b71c1c")
    st.markdown(f'<div style="background:{h_bg}; padding:10px; border-radius:10px; text-align:center; border:2px solid {h_txt};"><h1 style="color:{h_txt}; margin:0; font-size:32px;">{index_choice} {arrow} {live_px:,.2f}</h1></div>', unsafe_allow_html=True)

    # --- ADVANCED CHART LOGIC ---
    st.write("---")
    c1, c2 = st.columns([1, 5])
    with c1:
        tf_choice = st.radio("TIME FRAME", ["1 Min", "5 Min", "15 Min", "30 Min"], index=1)
        tf_map = {"1 Min": "1m", "5 Min": "5m", "15 Min": "15m", "30 Min": "30m"}
        max_p = 100 

    hist_key = f"{index_choice}_{tf_choice}"
    if hist_key not in memory["hist_df"]:
        try:
            end_t = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.000Z")
            start_t = (datetime.utcnow() - timedelta(days=5)).strftime("%Y-%m-%dT%H:%M:%S.000Z")
            hist_res = md.historical_data({
                "exchange": target_exch, "type": "INDEX", "values": [index_choice],
                "fields": ["open", "high", "low", "close", "cumulative_volume"],
                "startDate": start_t, "endDate": end_t, "interval": tf_map[tf_choice],
                "intraDay": False, "realTime": False
            })
            raw = hist_res.result[0].values[0][index_choice]
            memory["hist_df"][hist_key] = pd.DataFrame({
                "time": [pd.to_datetime(p.timestamp, unit="ns").tz_localize("UTC").tz_convert("Asia/Kolkata") for p in raw.close],
                "open": [p.value/100 for p in raw.open], "high": [p.value/100 for p in raw.high],
                "low": [p.value/100 for p in raw.low], "close": [p.value/100 for p in raw.close],
                "vol": [p.value for p in raw.cumulative_volume]
            })
        except: pass

    if hist_key in memory["hist_df"]:
        df_p = memory["hist_df"][hist_key].copy().tail(max_p)
        if live_px != df_p.iloc[-1]['close']:
            df_p.loc[df_p.index[-1], 'close'] = live_px
            if live_px > df_p.iloc[-1]['high']: df_p.loc[df_p.index[-1], 'high'] = live_px
            if live_px < df_p.iloc[-1]['low']: df_p.loc[df_p.index[-1], 'low'] = live_px

        df_p['MA9'] = df_p['close'].rolling(9).mean()
        df_p['VWAP'] = (df_p['close'] * df_p['vol']).cumsum() / (df_p['vol'].cumsum() + 1)
        df_p['ATR'] = (df_p['high'] - df_p['low']).rolling(10).mean()
        df_p['ST_UP'] = df_p['MA9'] + (df_p['ATR'] * 2.5)
        df_p['ST_DN'] = df_p['MA9'] - (df_p['ATR'] * 2.5)

        df_ce, df_pe = pd.DataFrame([vars(x) for x in chain.ce]), pd.DataFrame([vars(x) for x in chain.pe])
        res_stk = int(df_ce.loc[df_ce[df_ce["strike_price"]/100 >= live_px]["volume"].idxmax(), "strike_price"]/100)
        sup_stk = int(df_pe.loc[df_pe[df_pe["strike_price"]/100 <= live_px]["volume"].idxmax(), "strike_price"]/100)

        fig = make_subplots(rows=1, cols=1)
        fig.add_trace(go.Candlestick(x=df_p['time'], open=df_p['open'], high=df_p['high'], low=df_p['low'], close=df_p['close'], name="Price"))
        fig.add_trace(go.Scatter(x=df_p['time'], y=df_p['MA9'], line=dict(color='blue', width=1.5), name="MA9"))
        fig.add_trace(go.Scatter(x=df_p['time'], y=df_p['VWAP'], line=dict(color='orange', width=2, dash='dash'), name="VWAP"))
        fig.add_trace(go.Scatter(x=df_p['time'], y=df_p['ST_UP'], line=dict(color='rgba(255,0,0,0.3)', width=1), name="ST Sell"))
        fig.add_trace(go.Scatter(x=df_p['time'], y=df_p['ST_DN'], line=dict(color='rgba(0,255,0,0.3)', width=1), name="ST Buy"))
        
        fig.add_hline(y=res_stk, line=dict(color="blue", width=2, dash="dot"), annotation_text="RES")
        fig.add_hline(y=sup_stk, line=dict(color="red", width=2, dash="dot"), annotation_text="SUP")
        
        boring = abs(df_p['close'] - df_p['open']) / (df_p['high'] - df_p['low'] + 0.001) < 0.45
        fig.add_trace(go.Scatter(x=df_p['time'][boring], y=df_p['close'][boring], mode="markers", marker=dict(color="yellow", size=8, symbol="diamond"), name="Boring"))

        fig.update_layout(
            height=550, margin=dict(l=0,r=0,t=0,b=0), xaxis_rangeslider_visible=False, yaxis=dict(autorange=True, fixedrange=False),
            xaxis=dict(type='date', tickformat="%d %b\n%H:%M", rangebreaks=[dict(bounds=["sat", "mon"]), dict(bounds=[15.5, 9], pattern="hour")])
        )
        for d in df_p['time'].dt.date.unique():
            fig.add_vline(x=df_p[df_p['time'].dt.date == d]['time'].min(), line=dict(color="gray", width=1, dash="dash"))
        st.plotly_chart(fig, use_container_width=True)

    # PCR & BEP
    pcr = df_pe["open_interest"].sum() / df_ce["open_interest"].sum()
    mood = "🐂 BULLISH" if pcr > 1.15 else "🐻 BEARISH" if pcr < 0.85 else "↔️ SIDEWAYS"
    st.markdown(f'''<div style="background:#f8fafc; color:#1e293b; padding:10px; border-radius:8px; text-align:center; font-weight:bold; border: 1px solid #cbd5e1; margin-top:10px;">
        <span style="color:#f59e0b;">CE BEP: {int(spot + 100)}</span> | <span>PCR: {pcr:.2f} ({mood})</span> | <span style="color:#ef4444;">PE BEP: {int(spot - 100)}</span>
    </div>''', unsafe_allow_html=True)

    # --- SNIPER TABLE ---
    df_comb = pd.merge(df_ce, df_pe, on="strike_price", suffixes=("_CE","_PE")).fillna(0)
    df_comb["STRIKE_VAL"] = (df_comb["strike_price"]/100).astype(int)
    s_key = f"init_df_v5_{index_choice}"
    if s_key not in st.session_state: st.session_state[s_key] = df_comb.copy()
    init_df = st.session_state[s_key].set_index("STRIKE_VAL")
    df_comb["oi_chg_CE"] = df_comb.apply(lambda r: r["open_interest_CE"] - (init_df.loc[r["STRIKE_VAL"], "open_interest_CE"] if r["STRIKE_VAL"] in init_df.index else r["open_interest_CE"]), axis=1)
    df_comb["oi_chg_PE"] = df_comb.apply(lambda r: r["open_interest_PE"] - (init_df.loc[r["STRIKE_VAL"], "open_interest_PE"] if r["STRIKE_VAL"] in init_df.index else r["open_interest_PE"]), axis=1)

    max_o_ce, max_o_pe = df_comb["open_interest_CE"].max() or 1, df_comb["open_interest_PE"].max() or 1
    max_v_ce, max_v_pe = df_comb["volume_CE"].max() or 1, df_comb["volume_PE"].max() or 1
    d_df = df_comb.iloc[(df_comb["STRIKE_VAL"] - live_px).abs().idxmin()-10 : (df_comb["STRIKE_VAL"] - live_px).abs().idxmin()+11].copy().reset_index(drop=True)

    ui = pd.DataFrame()
    def fmt_v(v, d, m): return f"{v:,.0f}\n({d:+,})\n{(v/m*100):.1f}%"
    ui["CE OI\n(Δ/%)"] = d_df.apply(lambda r: fmt_v(r["open_interest_CE"], r["oi_chg_CE"], max_o_ce), axis=1)
    ui["CE OI CHG"] = d_df["oi_chg_CE"].apply(lambda x: f"{x:+,}")
    ui["CE VOL\n(%)"] = d_df.apply(lambda r: f"{r['volume_CE']:,.0f}\n({(r['volume_CE']/max_v_ce*100):.1f}%)", axis=1)
    ui["STRIKE"] = d_df["STRIKE_VAL"].apply(lambda s: f"⭐ {s} ({arrow}{live_px:,.1f})" if s == atm_val else str(s))
    ui["PE VOL\n(%)"] = d_df.apply(lambda r: f"{r['volume_PE']:,.0f}\n({(r['volume_PE']/max_v_pe*100):.1f}%)", axis=1)
    ui["PE OI CHG"] = d_df["oi_chg_PE"].apply(lambda x: f"{x:+,}")
    ui["PE OI\n(Δ/%)"] = d_df.apply(lambda r: fmt_v(r["open_interest_PE"], r["oi_chg_PE"], max_o_pe), axis=1)

    def apply_s(row):
        styles = [''] * 7; idx = row.name; stk = d_df.loc[idx, "STRIKE_VAL"]
        styles[3] = 'background-color:yellow; color:black; font-weight:bold' if stk == atm_val else 'background-color:#f8f9fa; color:black; font-weight:bold'
        if stk == res_stk: [styles.__setitem__(i, styles[i]+'; border-top:5px solid blue') for i in range(7)]
        if stk == sup_stk: [styles.__setitem__(i, styles[i]+'; border-bottom:5px solid red') for i in range(7)]
        def ch_p(v): 
            m = re.search(r'([\d\.]+)%', str(v))
            return float(m.group(1)) if m else 0.0
        if ch_p(row.iloc[0]) >= 75: styles[0] = 'background-color:#1565c0; color:white'
        if ch_p(row.iloc[2]) >= 75: styles[2] = 'background-color:#2e7d32; color:white'
        if ch_p(row.iloc[4]) >= 75: styles[4] = 'background-color:#c62828; color:white'
        if ch_p(row.iloc[6]) >= 75: styles[6] = 'background-color:#ef6c00; color:white'
        return styles

    st.table(ui.style.apply(apply_s, axis=1))
except Exception as e: st.error(f"Execution Error: {e}")
