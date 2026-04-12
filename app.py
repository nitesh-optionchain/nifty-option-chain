import streamlit as st
import pandas as pd
from nubra_python_sdk.ticker import websocketdata
from nubra_python_sdk.start_sdk import InitNubraSdk, NubraEnv
import threading

# -------- PAGE --------
st.set_page_config(page_title="Live Option Data", layout="wide")
st.title("🔥 Live Option Data (WebSocket)")

# -------- STORAGE --------
if "data" not in st.session_state:
    st.session_state.data = []

# -------- INIT --------
nubra = InitNubraSdk(NubraEnv.PROD, env_creds=True)

# -------- CALLBACK --------
def on_option_data(msg):
    try:
        row = {
            "Symbol": msg.get("symbol"),
            "LTP": msg.get("ltp"),
            "OI": msg.get("oi"),
            "Volume": msg.get("volume"),
        }
        st.session_state.data.append(row)

        # Limit rows
        if len(st.session_state.data) > 50:
            st.session_state.data = st.session_state.data[-50:]

    except Exception as e:
        print("Error parsing:", e)

def on_connect(msg):
    print("[Connected]", msg)

def on_close(reason):
    print("Closed:", reason)

def on_error(err):
    print("Error:", err)

# -------- SOCKET THREAD --------
def start_socket():
    socket = websocketdata.NubraDataSocket(
        client=nubra,
        on_option_data=on_option_data,
        on_connect=on_connect,
        on_close=on_close,
        on_error=on_error,
    )

    socket.connect()
    socket.subscribe(["RELIANCE:20250626"], data_type="option", exchange="NSE")
    socket.keep_running()

# Run socket once
if "socket_started" not in st.session_state:
    st.session_state.socket_started = True
    threading.Thread(target=start_socket, daemon=True).start()

# -------- DISPLAY --------
st.subheader("📊 Live Data Table")

df = pd.DataFrame(st.session_state.data)

st.dataframe(df, use_container_width=True)

# -------- AUTO REFRESH --------
import time
time.sleep(2)
st.rerun()