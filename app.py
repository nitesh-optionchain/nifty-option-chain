from __future__ import annotations

import math
import os
import json
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
import streamlit.components.v1 as components
from streamlit_autorefresh import st_autorefresh

# --- SDK IMPORTS ---
try:
    from nubra_python_sdk.marketdata.market_data import MarketData
    from nubra_python_sdk.start_sdk import InitNubraSdk, NubraEnv
except ImportError:
    st.error("Nubra SDK not found. Please install it to run live.")

# ================= 1. CONFIG & CONSTANTS =================
INDEX_SYMBOLS = {
    "NIFTY": {"exchange": "NSE", "type": "INDEX"},
    "SENSEX": {"exchange": "BSE", "type": "INDEX"},
    "BANKNIFTY": {"exchange": "NSE", "type": "INDEX"},
}
TIMEFRAME_MINUTES = [5, 10, 15, 25]
IST = "Asia/Kolkata"
SESSION_FILE = "session_login.json"
USER_FILE = "authorized_users.json"

@dataclass
class DataStatus:
    live: bool
    message: str

# ================= 2. CORE LOGIC (AAPKA CODE) =================

def normalize_price(value: Any) -> float:
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return np.nan
    try:
        price = float(value)
        # Bank Nifty / Nifty Paisa to Rupee conversion
        if abs(price) >= 100000:
            return price / 100.0
        return price
    except:
        return np.nan

def point_series(points: Any, normalize: bool = True) -> pd.Series:
    if not points: return pd.Series(dtype="float64")
    timestamps, values = [], []
    for pt in points:
        ts = getattr(pt, "timestamp", None)
        val = getattr(pt, "value", None)
        if ts is None or val is None: continue
        timestamps.append(ts)
        values.append(normalize_price(val) if normalize else float(val))
    if not timestamps: return pd.Series(dtype="float64")
    idx = pd.to_datetime(timestamps, unit="ns", utc=True).tz_convert(IST)
    return pd.Series(values, index=idx, dtype="float64")

def rsi(series: pd.Series, period: int = 14) -> pd.Series:
    delta = series.diff()
    gain = delta.clip(lower=0).ewm(alpha=1/period, adjust=False).mean()
    loss = -delta.clip(upper=0).ewm(alpha=1/period, adjust=False).mean()
    rs = gain / loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))

def atr(frame: pd.DataFrame, period: int = 14) -> pd.Series:
    hl = frame["high"] - frame["low"]
    hc = (frame["high"] - frame["close"].shift()).abs()
    lc = (frame["low"] - frame["close"].shift()).abs()
    tr = pd.concat([hl, hc, lc], axis=1).max(axis=1)
    return tr.ewm(alpha=1/period, adjust=False).mean()

def supertrend(frame: pd.DataFrame, period=10, mult=3.0):
    df = frame.copy()
    atr_val = atr(df, period)
    hl2 = (df["high"] + df["low"]) / 2
    ub = hl2 + mult * atr_val
    lb = hl2 - mult * atr_val
    final_ub, final_lb = ub.copy(), lb.copy()
    trend = pd.Series(1, index=df.index)
    line = pd.Series(index=df.index)

    for i in range(1, len(df)):
        curr, prev = df.index[i], df.index[i-1]
        final_ub[i] = ub[i] if ub[i] < final_ub[i-1] or df["close"][prev] > final_ub[i-1] else final_ub[i-1]
        final_lb[i] = lb[i] if lb[i] > final_lb[i-1] or df["close"][prev] < final_lb[i-1] else final_lb[i-1]
        
        if trend[prev] == -1 and df["close"][curr] > final_ub[i]: trend[i] = 1
        elif trend[prev] == 1 and df["close"][curr] < final_lb[i]: trend[i] = -1
        else: trend[i] = trend[prev]
        
        line[i] = final_lb[i] if trend[i] == 1 else final_ub[i]
    return line, trend

def add_indicators(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty: return df
    df["rsi"] = rsi(df["close"])
    df["atr"] = atr(df)
    df["st_line"], df["trend"] = supertrend(df)
    df["body_pct"] = (df["close"] - df["open"]).abs() / (df["high"] - df["low"]).replace(0, np.nan)
    df["boring_candle"] = (df["body_pct"] <= 0.22)
    return df

# ================= 3. DATA FETCHING =================

def fetch_history(market_data, symbol, interval, days, exch):
    try:
        end = datetime.now(timezone.utc)
        start = end - timedelta(days=days)
        res = market_data.historical_data({
            "exchange": exch, "type": "INDEX", "values": [symbol],
            "fields": ["open", "high", "low", "close", "cumulative_volume"],
            "startDate": start.strftime("%Y-%m-%dT%H:%M:%S.000Z"),
            "endDate": end.strftime("%Y-%m-%dT%H:%M:%S.000Z"),
            "interval": interval
        })
        # Simplified response parsing
        for group in res.result:
            for inst in group.values:
                for sym, chart in inst.items():
                    if sym == symbol:
                        df = pd.DataFrame({
                            "open": point_series(chart.open),
                            "high": point_series(chart.high),
                            "low": point_series(chart.low),
                            "close": point_series(chart.close),
                            "volume": point_series(chart.cumulative_volume, False).diff().fillna(0)
                        })
                        return df.dropna()
    except: return pd.DataFrame()

# ================= 4. UI COMPONENTS =================

def setup_ui():
    st.set_page_config(page_title="SMART WEALTH PRO", layout="wide")
    st.markdown("""
        <style>
        .signal-long { background:#eefaf4; border-left:5px solid green; padding:15px; border-radius:8px; }
        .signal-short { background:#fff2f0; border-left:5px solid red; padding:15px; border-radius:8px; }
        .signal-wait { background:#fff8e6; border-left:5px solid orange; padding:15px; border-radius:8px; }
        </style>
    """, unsafe_allow_html=True)

def login_system():
    if "auth" not in st.session_state: st.session_state.auth = False
    if not st.session_state.auth:
        with st.form("Login"):
            uid = st.text_input("Mobile ID", type="password")
            if st.form_submit_button("GO LIVE"):
                # Admin list control
                if uid in ["9304768496", "7982046438"]:
                    st.session_state.auth = True
                    st.rerun()
                else: st.error("Access Denied")
        st.stop()

# ================= 5. MAIN APP =================

def main():
    setup_ui()
    login_system()
    st_autorefresh(interval=10000, key="data_refresh")

    # Sidebar
    idx_choice = st.sidebar.selectbox("Index", list(INDEX_SYMBOLS.keys()))
    tf_choice = st.sidebar.selectbox("Timeframe", TIMEFRAME_MINUTES)
    meta = INDEX_SYMBOLS[idx_choice]

    if "nubra" not in st.session_state:
        st.session_state.nubra = InitNubraSdk(NubraEnv.PROD, env_creds=True)
    
    md = MarketData(st.session_state.nubra)

    # DATA SECTION
    df = fetch_history(md, idx_choice, f"{tf_choice}m", 5, meta["exchange"])
    df = add_indicators(df)

    if not df.empty:
        last = df.iloc[-1]
        st.header(f"📊 {idx_choice} LIVE: {last['close']:,.2f}")

        col1, col2 = st.columns([3, 1])

        with col1:
            # CHART
            fig = go.Figure(data=[go.Candlestick(x=df.index, open=df['open'], high=df['high'], low=df['low'], close=df['close'])])
            fig.add_trace(go.Scatter(x=df.index, y=df['st_line'], line=dict(color='gray', width=1), name="Supertrend"))
            fig.update_layout(height=500, margin=dict(l=0,r=0,t=0,b=0), xaxis_rangeslider_visible=False)
            st.plotly_chart(fig, use_container_width=True)

        with col2:
            # SIGNAL BOX
            if last['trend'] == 1 and last['rsi'] > 55 and not last['boring_candle']:
                st.markdown('<div class="signal-long"><h3>🚀 LONG SCALP</h3><p>Trend is UP & RSI is Strong</p></div>', unsafe_allow_html=True)
            elif last['trend'] == -1 and last['rsi'] < 45 and not last['boring_candle']:
                st.markdown('<div class="signal-short"><h3>🔻 SHORT SCALP</h3><p>Trend is DOWN & RSI is Weak</p></div>', unsafe_allow_html=True)
            else:
                st.markdown('<div class="signal-wait"><h3>⏳ WAIT</h3><p>Market Neutral or Boring Candle</p></div>', unsafe_allow_html=True)

            st.write("---")
            st.metric("RSI", f"{last['rsi']:.2f}")
            st.metric("ATR", f"{last['atr']:.2f}")
            if last['boring_candle']: st.warning("⚠️ Boring Candle Detected")

    # OPTION CHAIN
    st.subheader("⛓️ Option Chain Scanner")
    oc_res = md.option_chain(idx_choice, exchange=meta["exchange"])
    if oc_res and oc_res.chain:
        # Simplified Trap logic from your code
        ce_data = pd.DataFrame([vars(x) for x in oc_res.chain.ce])
        pe_data = pd.DataFrame([vars(x) for x in oc_res.chain.pe])
        # Display logic here...
        st.write("Live chain connected. Check strikes for Volume Traps.")
        st.dataframe(ce_data[['strike_price', 'last_traded_price', 'volume', 'open_interest']].tail(10))

if __name__ == "__main__":
    main()
