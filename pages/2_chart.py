import sys
import os
from datetime import datetime, timedelta
import streamlit as st
import plotly.graph_objects as go
from streamlit_autorefresh import st_autorefresh

# 1. Page & Fast Dynamic Refresh Engine
st.set_page_config(layout="wide")
st.subheader("📊 Live Pure Candle Verification Terminal")
st_autorefresh(interval=3000, key="pure_candle_sync")

# 2. Path routing config for internal sdk blocks
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.append(BASE_DIR)

from nubra_python_sdk.start_sdk import InitNubraSdk, NubraEnv
from nubra_python_sdk.ticker import websocketdata

# 3. Clean RAM state definition purely to map text ticks array
if "pure_ticks" not in st.session_state:
    st.session_state.pure_ticks = {
        "NIFTY": [],
        "SENSEX": []
    }

# Minimalist side elements selection widget matrix
target_asset = st.sidebar.selectbox("🔤 Asset Selector", ["NIFTY", "SENSEX"], index=0)

# 4. Strictly core operational network background websocket thread
@st.cache_resource(show_spinner=False)
def launch_isolated_ticker_stream():
    try:
        nubra = InitNubraSdk(NubraEnv.PROD, env_creds=True)
        
        def process_raw_ohlcv(msg):
            try:
                sym = getattr(msg, 'indexname', None) or getattr(msg, 'symbol', None)
                if sym in ["NIFTY", "SENSEX"]:
                    o = float(getattr(msg, 'open', 0)) / 100.0
                    h = float(getattr(msg, 'high', 0)) / 100.0
                    l = float(getattr(msg, 'low', 0)) / 100.0
                    c = float(getattr(msg, 'close', 0)) / 100.0
                    
                    if c > 0:
                        stamp = datetime.now().strftime("%H:%M:%S")
                        buf = st.session_state.pure_ticks[sym]
                        
                        if len(buf) > 0 and buf[-1]["time"] == stamp:
                            buf[-1].update({"high": max(buf[-1]["high"], h), "low": min(buf[-1]["low"], l), "close": c})
                        else:
                            buf.append({"time": stamp, "open": o, "high": h, "low": l, "close": c})
                            
                        if len(buf) > 100:
                            buf.pop(0)
            except Exception:
                pass

        socket = websocketdata.NubraDataSocket(
            client=nubra,
            on_ohlcv_data=process_raw_ohlcv,
            on_connect=lambda m: print("[status] Active"),
            on_close=lambda r: print(f"Closed: {r}"),
            on_error=lambda e: print(f"Error: {e}")
        )
        socket.connect()
        socket.subscribe(["NIFTY"], data_type="ohlcv", interval="10m", exchange="NSE")
        socket.subscribe(["SENSEX"], data_type="ohlcv", interval="10m", exchange="BSE")
        return socket
    except Exception:
        return None

# Instantiating core background socket channel safely
socket_handle = launch_isolated_ticker_stream()

# 5. Core Fallback Seeder Block (Bypasses initial blank frame screens cleanly)
history = st.session_state.pure_ticks[target_asset]
if len(history) == 0:
    base_price = 24230.0 if target_asset == "NIFTY" else 77460.0
    mock_array = []
    for i in range(35):
        t_stamp = (datetime.now() - timedelta(minutes=10 * (35 - i))).strftime("%H:%M:%S")
        mock_array.append({
            "time": t_stamp, "open": base_price, "high": base_price + 8, "low": base_price - 8, "close": base_price
        })
    st.session_state.pure_ticks[target_asset] = mock_array
    history = st.session_state.pure_ticks[target_asset]

# 6. Boring Yellow Candlestick Plotly native layout engine drawing context
times = [item["time"] for item in history]
opens = [item["open"] for item in history]
highs = [item["high"] for item in history]
lows = [item["low"] for item in history]
closes = [item["close"] for item in history]

fig = go.Figure(data=[go.Candlestick(
    x=times, open=opens, high=highs, low=lows, close=closes,
    increasing_line_color='#facc15', decreasing_line_color='#eab308',
    increasing_fillcolor='#facc15', decreasing_fillcolor='#eab308'
)])

fig.update_layout(
    height=720, template="plotly_dark", xaxis_rangeslider_visible=False,
    paper_bgcolor='#030712', plot_bgcolor='#030712',
    margin=dict(l=20, r=60, t=10, b=20),
    yaxis=dict(side="right", showgrid=True, gridcolor="#1e293b")
)

st.plotly_chart(fig, use_container_width=True)
