# engine.py
import os
import threading
import streamlit as st

@st.cache_resource(show_spinner=False)
def get_engine():
    try:
        from nubra_python_sdk.marketdata.market_data import MarketData
        from nubra_python_sdk.start_sdk import InitNubraSdk, NubraEnv
        from nubra_python_sdk.ticker import websocketdata

        st.write("PHONE_NO in secrets:", "PHONE_NO" in st.secrets)
        st.write("MPIN in secrets:", "MPIN" in st.secrets)

        os.environ["PHONE_NO"] = st.secrets["PHONE_NO"]
        os.environ["MPIN"] = st.secrets["MPIN"]
        
        nubra = InitNubraSdk(NubraEnv.PROD, env_creds=True)
                
        def on_msg(msg):
            name = msg.get('indexname')
            if name and "ticks" in st.session_state: 
                st.session_state.ticks[name] = msg
            if msg.get('indexname') == 'INDIAVIX' and "ticks" in st.session_state:
                st.session_state.ticks['INDIAVIX'] = msg
                
        socket = websocketdata.NubraDataSocket(client=nubra, on_index_data=on_msg)
        socket.connect()
        socket.subscribe(["NIFTY", "SENSEX", "BANKNIFTY", "INDIAVIX"], data_type="index", exchange="NSE")
        threading.Thread(target=socket.keep_running, daemon=True).start()
        return MarketData(nubra)
    except: 
        return None
