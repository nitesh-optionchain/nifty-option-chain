from __future__ import annotations
import math, os, json, threading, time
import numpy as np
import pandas as pd
import streamlit as st
from datetime import datetime
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

@st.cache_resource
def get_global_memory():
    return {"ohlc": {}, "vol": {}, "hist_df": {}}

memory = get_global_memory() # Ye line error fix karegi

if "is_auth" not in st.session_state: st.session_state.is_auth = False

if not st.session_state.is_auth and os.path.exists(SESSION_FILE):
    saved = load_json(SESSION_FILE, None)
    if saved and saved.get("user_id") in ADMIN_DB:
        st.session_state.is_auth = True
        st.session_state.admin_name = ADMIN_DB[saved["user_id"]]
        st.session_state.current_user_id = saved["user_id"]
        st.session_state.is_super_admin = (saved["user_id"] in SUPER_ADMIN_IDS)

if not st.session_state.is_auth:
    st.markdown("<h1 style='text-align: center;'>🛡️ SMART WEALTH AI 5</h1>", unsafe_allow_html=True)
    _, col2, _ = st.columns([1, 1, 1])
    with col2:
        with st.form("Login"):
            user_key = st.text_input("Enter Mobile ID:", type="password")
            if st.form_submit_button("LOGIN"):
                if user_key in ADMIN_DB:
                    st.session_state.is_auth = True
                    st.session_state.admin_name = ADMIN_DB[user_key]
                    st.session_state.current_user_id = user_key
                    st.session_state.is_super_admin = (user_key in SUPER_ADMIN_IDS)
                    save_json(SESSION_FILE, {"user_id": user_key})
                    st.rerun()
                else: st.error("❌ Invalid Access ID")
    st.stop()

# ================= 2. ENGINE & SIDEBAR =================
st_autorefresh(interval=5000, key="v5_analysis_stable")

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

matrix_settings = load_json(SETTINGS_FILE, {"last_index": "NIFTY"})
idx_list = ["NIFTY", "BANKNIFTY", "SENSEX"]
saved_idx = matrix_settings.get("last_index", "NIFTY")
default_idx = idx_list.index(saved_idx) if saved_idx in idx_list else 0

with st.sidebar:
    st.markdown(f"### 👤 User: **{st.session_state.admin_name}**")
    index_choice = st.selectbox("Select Index", idx_list, index=default_idx)
    if index_choice != saved_idx:
        save_json(SETTINGS_FILE, {"last_index": index_choice})
    
    if st.button("🔒 LOGOUT"):
        if os.path.exists(SESSION_FILE): os.remove(SESSION_FILE)
        st.session_state.clear(); st.rerun()

    # --- ADMIN PANEL RESTORED ---
    if st.session_state.is_super_admin:
        with st.expander("👥 User Management"):
            new_uid = st.text_input("Add ID")
            new_uname = st.text_input("Name")
            if st.button("ADD"):
                if new_uid and new_uname:
                    ADMIN_DB[new_uid] = new_uname
                    save_json(USER_FILE, ADMIN_DB); st.rerun()
            u_del = st.selectbox("Remove", [f"{v} ({k})" for k, v in ADMIN_DB.items() if k != st.session_state.current_user_id])
            if st.button("DELETE"):
                uid_del = u_del.split('(')[-1].replace(')', '')
                del ADMIN_DB[uid_del]; save_json(USER_FILE, ADMIN_DB); st.rerun()

target_exch = "BSE" if index_choice == "SENSEX" else "NSE"

# ================= 3. CORE PROCESSING =================
try:
    result = md.option_chain(index_choice, exchange=target_exch)
    if not result or not result.chain:
        st.info("Syncing Market Matrix... ⏳"); st.stop()

    chain = result.chain
    spot = chain.current_price / 100 if chain.current_price > 100000 else chain.current_price
    atm = chain.at_the_money_strike / 100
    t_idx = st.session_state.ticks.get(index_choice, {})
    live_px = t_idx.get('index_value', 0)/100 or spot
    cur_chg = (live_px - spot)

    # Header
    h_bg, h_txt = ("#e8f5e9", "#1b5e20") if cur_chg >= 0 else ("#ffebee", "#b71c1c")
    arrow = "▲" if cur_chg >= 0 else "▼"
    st.markdown(f'''<div style="background:{h_bg}; padding:15px; border-radius:10px; text-align:center; border: 2px solid {h_txt};">
        <h1 style="color:{h_txt}; margin:0; font-size:32px; font-weight:bold;">{index_choice} {arrow} {live_px:,.2f}</h1>
    </div>''', unsafe_allow_html=True)

    # Data Prep
    df_ce, df_pe = pd.DataFrame([vars(x) for x in chain.ce]), pd.DataFrame([vars(x) for x in chain.pe])
    df_comb = pd.merge(df_ce, df_pe, on="strike_price", suffixes=("_CE","_PE")).fillna(0)
    df_comb["STRIKE_VAL"] = (df_comb["strike_price"]/100).astype(int)
    
    pcr = df_pe["open_interest"].sum() / df_ce["open_interest"].sum()
    res_stk = int(df_comb.loc[df_comb[df_comb["STRIKE_VAL"] >= live_px]["volume_CE"].idxmax(), "STRIKE_VAL"])
    sup_stk = int(df_comb.loc[df_comb[df_comb["STRIKE_VAL"] <= live_px]["volume_PE"].idxmax(), "STRIKE_VAL"])

   # ================= 4. ADVANCED CHART (ST, BORING, S/R) =================
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
            start_t = (datetime.utcnow() - timedelta(days=2)).strftime("%Y-%m-%dT%H:%M:%S.000Z")
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
        except: st.warning("Syncing candles...")

    if hist_key in memory["hist_df"]:
        df_plot = memory["hist_df"][hist_key].copy().tail(max_p)
        if live_px != df_plot.iloc[-1]['close']:
            df_plot.loc[df_plot.index[-1], 'close'] = live_px
        
        # Indicators
        df_plot['MA9'] = df_plot['close'].rolling(9).mean()
        df_plot['VWAP'] = (df_plot['close'] * df_plot['vol']).cumsum() / (df_plot['vol'].cumsum() + 1)
        df_plot['ATR'] = (df_plot['high'] - df_plot['low']).rolling(10).mean()
        df_plot['ST_UP'] = df_plot['MA9'] + (df_plot['ATR'] * 2.5)
        df_plot['ST_DN'] = df_plot['MA9'] - (df_plot['ATR'] * 2.5)

        fig = make_subplots(rows=1, cols=1)
        fig.add_trace(go.Candlestick(x=df_plot['time'], open=df_plot['open'], high=df_plot['high'], low=df_plot['low'], close=df_plot['close'], name="Market"))
        fig.add_trace(go.Scatter(x=df_plot['time'], y=df_plot['MA9'], line=dict(color='blue', width=1.5), name="MA9"))
        fig.add_trace(go.Scatter(x=df_plot['time'], y=df_plot['VWAP'], line=dict(color='orange', width=2, dash='dash'), name="VWAP"))
        fig.add_trace(go.Scatter(x=df_plot['time'], y=df_plot['ST_UP'], line=dict(color='rgba(255,0,0,0.3)'), name="ST Sell"))
        fig.add_trace(go.Scatter(x=df_plot['time'], y=df_plot['ST_DN'], line=dict(color='rgba(0,255,0,0.3)'), name="ST Buy"))
        
        # S/R Dotted Lines
        fig.add_hline(y=res_stk, line=dict(color="blue", width=2, dash="dot"), annotation_text="RES")
        fig.add_hline(y=sup_stk, line=dict(color="red", width=2, dash="dot"), annotation_text="SUP")
        
        # Boring Candles Marker (Yellow)
        boring = abs(df_plot['close']-df_plot['open']) / (df_plot['high']-df_plot['low']+0.001) < 0.45
        fig.add_trace(go.Scatter(x=df_plot['time'][boring], y=df_plot['close'][boring], mode="markers", marker=dict(color="yellow", size=8, symbol="diamond"), name="Boring"))

        # --- 4.5 Layout Fix (Gap Removal + Day Separator) ---
        fig.update_layout(
            height=500, 
            margin=dict(l=0,r=0,t=0,b=0), 
            xaxis_rangeslider_visible=False,
            yaxis=dict(autorange=True, fixedrange=False),
            xaxis=dict(
                type='date',
                tickformat="%d %b\n%H:%M", # Date aur Time dono dikhayega (e.g. 12 May 11:30)
                rangebreaks=[
                    dict(bounds=["sat", "mon"]), 
                    dict(bounds=[15.5, 9], pattern="hour"), 
                ]
            )
        )

        # Aaj aur kal ke beech line khichne ka logic
        unique_days = df_plot['time'].dt.date.unique()
        for day in unique_days:
            # Har naye din ki pehli candle par vertical line
            day_start = df_plot[df_plot['time'].dt.date == day]['time'].min()
            fig.add_vline(x=day_start, line=dict(color="gray", width=1, dash="dash"))
            
        st.plotly_chart(fig, use_container_width=True)

    # PCR Strip & Alert
    mood = "🐂 BULLISH" if pcr > 1.15 else "🐻 BEARISH" if pcr < 0.85 else "↔️ SIDEWAYS"
    st.markdown(f'''<div style="background:#f8fafc; color:#1e293b; padding:10px; border-radius:8px; text-align:center; font-weight:bold; border: 1px solid #cbd5e1; margin-top:10px;">
        <span style="color:#f59e0b;">CE BEP: {atm + 100}</span> | <span>PCR: {pcr:.2f} ({mood})</span> | <span style="color:#ef4444;">PE BEP: {atm - 100}</span>
    </div>''', unsafe_allow_html=True)

    alert_color = "#1b5e20" if pcr >= 1.0 else "#b71c1c"
    alert_text = f"🚀 BIG MOVE: CALL BUY ABOVE {res_stk}" if pcr >= 1.0 else f"🩸 BIG MOVE: PUT BUY BELOW {sup_stk}"
    st.markdown(f'''<div style="background:{alert_color}; color:white; padding:12px; border-radius:8px; text-align:center; font-weight:bold; font-size:20px; margin-top:10px;">
        {alert_text}
    </div>''', unsafe_allow_html=True)

    # OI Fix & Table Data
    state_key = f"initial_df_{index_choice}"
    if state_key not in st.session_state: st.session_state[state_key] = df_comb.copy()
    init_df = st.session_state[state_key].set_index("STRIKE_VAL")

    df_comb["oi_chg_CE"] = df_comb.apply(lambda r: r["open_interest_CE"] - (init_df.loc[r["STRIKE_VAL"], "open_interest_CE"] if r["STRIKE_VAL"] in init_df.index else r["open_interest_CE"]), axis=1)
    df_comb["oi_chg_PE"] = df_comb.apply(lambda r: r["open_interest_PE"] - (init_df.loc[r["STRIKE_VAL"], "open_interest_PE"] if r["STRIKE_VAL"] in init_df.index else r["open_interest_PE"]), axis=1)

    max_oi_ce, max_oi_pe = df_comb["open_interest_CE"].max(), df_comb["open_interest_PE"].max()
    max_vol_ce, max_vol_pe = df_comb["volume_CE"].max(), df_comb["volume_PE"].max()
    max_chg_ce, max_chg_pe = df_comb["oi_chg_CE"].abs().max() or 1, df_comb["oi_chg_PE"].abs().max() or 1

    def fmt_val(val, delta, m_val):
        pct = (val/m_val*100) if m_val > 0 else 0
        return f"{val:,.0f}\n({delta:+,})\n{pct:.1f}%"

    atm_idx = (df_comb["STRIKE_VAL"] - live_px).abs().idxmin()
    d_df = df_comb.iloc[max(atm_idx-10,0): atm_idx+11].copy().reset_index(drop=True)

    ui = pd.DataFrame()
    ui["CE OI\n(Δ/%)"] = d_df.apply(lambda r: fmt_val(r["open_interest_CE"], r["oi_chg_CE"], max_oi_ce), axis=1)
    ui["CE OI CHG"] = d_df.apply(lambda r: f"{r['oi_chg_CE']:+,}\n{(r['oi_chg_CE']/max_chg_ce*100):.1f}%", axis=1)
    ui["CE VOL\n(%)"] = d_df.apply(lambda r: fmt_val(r["volume_CE"], 0, max_vol_ce), axis=1)
    ui["STRIKE"] = d_df["STRIKE_VAL"].apply(lambda s: f"⭐ {s} ({arrow}{live_px:,.1f})" if s == int(atm) else str(s))
    ui["PE VOL\n(%)"] = d_df.apply(lambda r: fmt_val(r["volume_PE"], 0, max_vol_pe), axis=1)
    ui["PE OI CHG"] = d_df.apply(lambda r: f"{r['oi_chg_PE']:+,}\n{(r['oi_chg_PE']/max_chg_pe*100):.1f}%", axis=1)
    ui["PE OI\n(Δ/%)"] = d_df.apply(lambda r: fmt_val(r["open_interest_PE"], r["oi_chg_PE"], max_oi_pe), axis=1)

    def style_table(row):
        s, idx = [''] * 7, row.name
        stk_val = d_df.loc[idx, "STRIKE_VAL"]
        s[3] = 'background-color:#f8f9fa;color:black;font-weight:bold' 
        if stk_val == int(atm): s[3] = 'background-color:yellow;color:black'
        if stk_val == res_stk:
            for i in range(7): s[i] += '; border-top: 5px solid blue;'
        if stk_val == sup_stk:
            for i in range(7): s[i] += '; border-bottom: 5px solid red;'
        if float(row.iloc[0].split('\n')[-1].replace('%','')) >= 70: s[0] = 'background-color:#1565c0;color:white'
        if float(row.iloc[1].split('\n')[-1].replace('%','')) >= 70: s[1] = 'background-color:#2e7d32;color:white'
        if float(row.iloc[2].split('\n')[-1].replace('%','')) >= 75: s[2] = 'background-color:#1b5e20;color:white'
        if float(row.iloc[4].split('\n')[-1].replace('%','')) >= 75: s[4] = 'background-color:#b71c1c;color:white'
        if float(row.iloc[5].split('\n')[-1].replace('%','')) >= 70: s[5] = 'background-color:#c62828;color:white'
        if float(row.iloc[6].split('\n')[-1].replace('%','')) >= 70: s[6] = 'background-color:#ef6c00;color:white'
        return s

    st.table(ui.style.apply(style_table, axis=1))
except Exception as e:
    st.info(f"Syncing Matrix... {e}")
