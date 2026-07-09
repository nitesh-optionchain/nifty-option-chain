import streamlit as st
import streamlit.components.v1 as components
import threading
from dotenv import load_dotenv
from nubra_python_sdk.ticker import websocketdata
from nubra_python_sdk.start_sdk import InitNubraSdk, NubraEnv

st.set_page_config(layout="wide")
st.subheader("📊 Live Multi-Asset Analytical Chart Terminal")
st.markdown("---")

load_dotenv()

# --- NUBRA WEBSOCKET BACKGROUND ENGINE ---
# Yeh backend me data fetch karta rahega aur collision nahi hone dega
if "chart_nubra_connected" not in st.session_state:
    try:
        nubra_chart_client = InitNubraSdk(NubraEnv.PROD, env_creds=True)
        
        def on_ohlcv_data(msg):
            # Yeh data ko server console ya file me check karne ke liye hai
            print("[Live Net Data]:", msg)

        chart_socket = websocketdata.NubraDataSocket(
            client=nubra_chart_client,
            on_ohlcv_data=on_ohlcv_data,
            on_connect=lambda m: print("[Status] Connected"),
            on_close=lambda r: print(f"Closed: {r}"),
            on_error=lambda e: print(f"Error: {e}"),
        )

        def run_socket():
            chart_socket.connect()
            chart_socket.subscribe(["NIFTY"], data_type="ohlcv", interval="10m", exchange="NSE")
            chart_socket.keep_running()

        t = threading.Thread(target=run_socket, daemon=True)
        t.start()
        st.session_state.chart_nubra_connected = True
    except Exception as ex:
        print("Nubra Init Issue:", ex)

# --- AAPKA PURANA IFRAME SETUP ---
components.html(
    '<iframe src="https://nitesh-optionchain.github.io/advance-chart/" width="100%" height="780" style="border:none; background-color: #131722;"></iframe>',
    height=800
)
