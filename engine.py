# engine.py
import threading
import streamlit as st

@st.cache_resource(show_spinner=False)
def get_engine():
    st.write("get_engine started")
    try:
        from nubra_python_sdk.marketdata.market_data import MarketData
        from nubra_python_sdk.start_sdk import InitNubraSdk, NubraEnv
        from nubra_python_sdk.ticker import websocketdata
        
        nubra = InitNubraSdk(NubraEnv.PROD, env_creds=True)
        st.write("MarketData created")
        
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
        st.write("MarketData created")
        return MarketData(nubra)
    except: 
        return None
