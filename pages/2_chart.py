import sys
import os
import time
import json
import streamlit as st
import streamlit.components.v1 as components
from datetime import datetime, timedelta

st.set_page_config(layout="wide")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
html_file_path = os.path.join(BASE_DIR, 'index.html')

if BASE_DIR not in sys.path:
    sys.path.append(BASE_DIR)

# ==============================================================================
# 🔌 SDK BROKER REBOOT CONTROL DECK (SINGLETON IN STATE)
# ==============================================================================
from nubra_python_sdk.start_sdk import InitNubraSdk, NubraEnv
from nubra_python_sdk.marketdata.market_data import MarketData

if "nubra_engine_instance" not in st.session_state:
    PHONE_NO = st.secrets.get("PHONE_NO") or os.environ.get("PHONE_NO")
    MPIN = st.secrets.get("MPIN") or os.environ.get("MPIN")

    if PHONE_NO and MPIN:
        os.environ["PHONE_NO"] = str(PHONE_NO)
        os.environ["MPIN"] = str(MPIN)
    
    try:
        sdk_client = InitNubraSdk(NubraEnv.PROD, env_creds=True)
        st.session_state["nubra_engine_instance"] = MarketData(sdk_client)
    except Exception:
        st.session_state["nubra_engine_instance"] = None

market_engine = st.session_state["nubra_engine_instance"]

# Active Navigation Panel Options
target_index = st.sidebar.selectbox("Active Asset Frame", ["NIFTY", "SENSEX"], index=0)
selected_tf = st.sidebar.selectbox("Timeframe Window", ["5m", "10m", "15m", "30m", "1d"], index=0)

# ==============================================================================
# 📊 3. STABLE RAW DIRECT API MATRIX (NO DATABASE WRITING LABELS NEEDED)
# ==============================================================================
master_history_array = []

if market_engine is not None:
    try:
        exch = "NSE" if target_index == "NIFTY" else "BSE"
        end_d = datetime.utcnow()
        start_d = end_d - timedelta(days=6) # 6 Days long backup window buffer
        
        response = market_engine.historical_data({
            "exchange": exch, "type": "INDEX", "values": [target_index],
            "fields": ["open", "high", "low", "close"],
            "startDate": start_d.strftime("%Y-%m-%dT%H:%M:%S.000Z"),
            "endDate": end_d.strftime("%Y-%m-%dT%H:%M:%S.000Z"),
            "interval": selected_tf, 
            "intraDay": False, "realTime": False
        })
        
        chart_data_list = []
        if response:
            if hasattr(response, 'result') and response.result:
                chart_data_list = response.result
            elif isinstance(response, dict) and 'result' in response:
                chart_data_list = response['result']

        # Pure in-memory sequence construction dictionary parser
        raw_rows = []
        for chart_data in chart_data_list:
            vals = getattr(chart_data, 'values', None) or (chart_data.get('values') if isinstance(chart_data, dict) else [])
            for element in (vals if isinstance(vals, list) else [vals]):
                chart = element.get(target_index) if isinstance(element, dict) else getattr(element, target_index, None)
                if chart:
                    opens = getattr(chart, 'open', None) or []
                    highs = getattr(chart, 'high', None) or []
                    lows = getattr(chart, 'low', None) or []
                    closes = getattr(chart, 'close', None) or []
                    
                    for i in range(len(opens)):
                        try:
                            raw_ts = opens[i].timestamp
                            sec_ts = int(raw_ts // 1000000000) if raw_ts > 9999999999 else int(raw_ts)
                            
                            val_o = float(opens[i].value)
                            val_h = float(highs[i].value) if i < len(highs) else val_o
                            val_l = float(lows[i].value) if i < len(lows) else val_o
                            val_c = float(closes[i].value) if i < len(closes) else val_o

                            # Normalizing multiplier segments cleanly
                            o_f = val_o / 100.0 if val_o > 100000 else val_o
                            h_f = val_h / 100.0 if val_h > 100000 else val_h
                            l_f = val_l / 100.0 if val_l > 100000 else val_l
                            c_f = val_c / 100.0 if val_c > 100000 else val_c
                            
                            raw_rows.append((sec_ts, o_f, h_f, l_f, c_f))
                        except Exception:
                            continue

        # Sort chronologically by timestamp before tracking indicators
        raw_rows.sort(key=lambda item: item[0])
        prices = [r[4] for r in raw_rows]
        
        cum_pv, cum_vol = 0.0, 0.0
        
        for idx, row in enumerate(raw_rows):
            t, o, h, l, c = row
            
            # A. Clean VWAP calculations accruals
            typ_p = (h + l + c) / 3.0
            cum_pv += typ_p * 100.0
            cum_vol += 100.0
            vwap_val = round(cum_pv / cum_vol, 2)
            
            # B. Moving Averages vectors
            ma9 = round(sum(prices[max(0, idx-8):idx+1]) / len(prices[max(0, idx-8):idx+1]), 2)
            ma20 = round(sum(prices[max(0, idx-19):idx+1]) / len(prices[max(0, idx-19):idx+1]), 2)
            ma50 = round(sum(prices[max(0, idx-49):idx+1]) / len(prices[max(0, idx-49):idx+1]), 2)
            
            # C. MACD 9 lines calculation overlay matrix
            macd_line = round(ma9 - ma20, 2)
            signal_line = round(sum([p_ma9 - p_ma20 for p_ma9, p_ma20 in zip(prices[max(0, idx-8):idx+1], prices[max(0, idx-19):idx+1])]) / len(prices[max(0, idx-8):idx+1]), 2) if idx >= 8 else 0.0
            
            # D. Supertrend Channels Parameters
            atr_range = (h - l) if (h - l) > 0 else 5.0
            supertrend = round(((h + l) / 2.0) - (2.5 * atr_range) if c >= o else ((h + l) / 2.0) + (2.5 * atr_range), 2)
            
            master_history_array.append({
                "time": int(t), "open": o, "high": h, "low": l, "close": c,
                "vwap": vwap_val, "ma9": ma9, "ma20": ma20, "ma50": ma50,
                "macd": macd_line, "signal": signal_line, "supertrend": supertrend
            })
    except Exception:
        pass

if master_history_array:
    current_display_price = master_history_array[-1]["close"]
else:
    current_display_price = 0.0

runtime_payload = {
    "current_asset": target_index,
    "price": int(current_display_price * 100),
    "master_history": master_history_array
}

st.sidebar.markdown(f"⏱️ **Active Interval:** `{selected_tf}`")
st.sidebar.markdown(f"🗂️ **Total Sequenced Bars:** `{len(master_history_array)}`")

if os.path.exists(html_file_path):
    with open(html_file_path, "r", encoding="utf-8") as f:
        html_content = f.read()
    
    json_data = json.dumps(runtime_payload)
    injection_script = f"""
    <script>
        window.chartPayload = {json_data};
        setTimeout(function() {{
            const iframeWin = document.getElementsByTagName('iframe')[0]?.contentWindow || window;
            iframeWin.postMessage({{ type: "DYNAMIC_TERMINAL_RELOAD", data: {json_data} }}, "*");
        }}, 300);
    </script>
    """
    html_content = html_content.replace("<head>", f"<head>{injection_script}")
    components.html(html_content, height=720, scrolling=False)
    time.sleep(2.0)
    st.rerun()
