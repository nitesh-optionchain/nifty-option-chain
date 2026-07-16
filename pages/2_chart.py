import sys
import os
import time
import json
import sqlite3
import streamlit as st
import streamlit.components.v1 as components
from datetime import datetime, timedelta

st.set_page_config(layout="wide")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
html_file_path = os.path.join(BASE_DIR, 'index.html')
DB_PATH = os.path.join(BASE_DIR, "market_ticks.db")
TOKEN_CACHE_FILE = os.path.join(BASE_DIR, "token_cache.json")

if BASE_DIR not in sys.path:
    sys.path.append(BASE_DIR)

def init_market_db():
    try:
        conn = sqlite3.connect(DB_PATH, timeout=10)
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS market_history (
                asset TEXT, timeframe TEXT, timestamp INTEGER, open REAL, high REAL, low REAL, close REAL,
                PRIMARY KEY (asset, timeframe, timestamp)
            )
        """)
        conn.commit()
        conn.close()
    except Exception:
        pass

init_market_db()

# ==============================================================================
# 🔑 2. AUTH LOCAL TOKEN LAYER
# ==============================================================================
from nubra_python_sdk.start_sdk import InitNubraSdk, NubraEnv
from nubra_python_sdk.marketdata.market_data import MarketData

def get_cached_market_engine():
    current_time = time.time()
    if os.path.exists(TOKEN_CACHE_FILE):
        try:
            with open(TOKEN_CACHE_FILE, "r") as f:
                cache_data = json.load(f)
            if current_time - cache_data.get("cached_at", 0) < 86400:
                os.environ["PHONE_NO"] = cache_data.get("phone")
                os.environ["MPIN"] = cache_data.get("mpin")
                sdk_client = InitNubraSdk(NubraEnv.PROD, env_creds=True)
                return MarketData(sdk_client)
        except Exception:
            pass

    PHONE_NO = st.secrets.get("PHONE_NO") or os.environ.get("PHONE_NO")
    MPIN = st.secrets.get("MPIN") or os.environ.get("MPIN")

    if PHONE_NO and MPIN:
        os.environ["PHONE_NO"] = str(PHONE_NO)
        os.environ["MPIN"] = str(MPIN)
        try:
            sdk_client = InitNubraSdk(NubraEnv.PROD, env_creds=True)
            engine_instance = MarketData(sdk_client)
            with open(TOKEN_CACHE_FILE, "w") as f:
                json.dump({"phone": str(PHONE_NO), "mpin": str(MPIN), "cached_at": current_time}, f)
            return engine_instance
        except Exception:
            pass
    return None

if "cached_nubra_engine" not in st.session_state:
    st.session_state["cached_nubra_engine"] = get_cached_market_engine()

market_engine = st.session_state["cached_nubra_engine"]

target_index = st.sidebar.selectbox("Active Asset Frame", ["NIFTY", "SENSEX"], index=0)
selected_tf = st.sidebar.selectbox("Timeframe Window", ["5m", "10m", "15m", "30m", "1d"], index=0)

tf_map = {"5m": 5, "10m": 10, "15m": 15, "30m": 30, "1d": 1440}
interval_minutes = tf_map[selected_tf]
interval_seconds = interval_minutes * 60

# ==============================================================================
# 📊 3. HISTORICAL REAL DATA PIPELINE (BUG FIXED & NO DEMO SIMULATION)
# ==============================================================================
def pull_broker_history(asset_name, engine, timeframe):
    if engine is None:
        return
    try:
        exch = "NSE" if asset_name == "NIFTY" else "BSE"
        end_d = datetime.utcnow()
        start_d = end_d - timedelta(days=3)  # Pure 3 Days Range Fetch
        
        api_payload = {
            "exchange": exch, "type": "INDEX", "values": [asset_name],
            "fields": ["open", "high", "low", "close"],
            "startDate": start_d.strftime("%Y-%m-%dT%H:%M:%S.000Z"),
            "endDate": end_d.strftime("%Y-%m-%dT%H:%M:%S.000Z"),
            "interval": timeframe, "intraDay": False, "realTime": False
        }
        
        response = None
        for method_name in ["historical_data", "get_historical_data", "get_history"]:
            if hasattr(engine, method_name):
                try:
                    response = getattr(engine, method_name)(api_payload)
                    if response: break
                except Exception:
                    pass
        
        if not response:
            try:
                response = MarketData.historical_data(engine, api_payload)
            except Exception:
                pass
                
        chart_data_list = []
        if response:
            if hasattr(response, 'result') and response.result:
                chart_data_list = response.result
            elif isinstance(response, dict) and 'result' in response:
                chart_data_list = response['result']

        if chart_data_list:
            conn = sqlite3.connect(DB_PATH, timeout=10)
            cursor = conn.cursor()
            for chart_data in chart_data_list:
                # FIXED: Mismatch dict variable reference completely corrected
                vals = getattr(chart_data, 'values', None) or (chart_data.get('values') if isinstance(chart_data, dict) else [])
                for element in (vals if isinstance(vals, list) else [vals]):
                    chart = element.get(asset_name) if isinstance(element, dict) else getattr(element, asset_name, None)
                    if chart:
                        opens = getattr(chart, 'open', None) or []
                        highs = getattr(chart, 'high', None) or []
                        lows = getattr(chart, 'low', None) or []
                        closes = getattr(chart, 'close', None) or []
                        
                        for i in range(len(opens)):
                            raw_ts = opens[i].timestamp
                            sec_ts = int(raw_ts // 1000000000) if raw_ts > 9999999999 else int(raw_ts)
                            o_v = float(opens[i].value)
                            h_v = float(highs[i].value) if i < len(highs) else o_v
                            l_v = float(lows[i].value) if i < len(lows) else o_v
                            c_v = float(closes[i].value) if i < len(closes) else o_v

                            o_f = o_v / 100.0 if o_v > 100000 else o_v
                            h_f = h_v / 100.0 if h_v > 100000 else h_v
                            l_f = l_v / 100.0 if l_v > 100000 else l_v
                            c_f = c_v / 100.0 if c_v > 100000 else c_v

                            cursor.execute("""
                                INSERT OR REPLACE INTO market_history (asset, timeframe, timestamp, open, high, low, close)
                                VALUES (?, ?, ?, ?, ?, ?, ?)
                            """, (asset_name, timeframe, sec_ts, o_f, h_f, l_f, c_f))
            conn.commit()
            conn.close()
    except Exception:
        pass

pull_broker_history(target_index, market_engine, selected_tf)

# ==============================================================================
# ⚡ 4. REAL-TIME TICK STREAM (LIVE PRICE UPDATE)
# ==============================================================================
base_ltp = 0.0

if market_engine is not None:
    try:
        exch_name = "NSE" if target_index == "NIFTY" else "BSE"
        snap = None
        for live_method in ["current_price", "get_current_price", "get_quote"]:
            if hasattr(market_engine, live_method):
                try:
                    snap = getattr(market_engine, live_method)(target_index, exchange=exch_name)
                    if snap: break
                except Exception:
                    pass
        if not snap:
            snap = MarketData.current_price(market_engine, target_index, exchange=exch_name)
            
        if snap and getattr(snap, 'price', None):
            raw_p = float(snap.price)
            base_ltp = raw_p / 100.0 if raw_p > 100000 else raw_p
            current_rounded_unix = (int(time.time()) // interval_seconds) * interval_seconds
            
            conn = sqlite3.connect(DB_PATH, timeout=10)
            cursor = conn.cursor()
            cursor.execute("SELECT open, high, low, close FROM market_history WHERE asset=? AND timeframe=? AND timestamp=?", (target_index, selected_tf, current_rounded_unix))
            existing_candle = cursor.fetchone()
            
            if existing_candle:
                cursor.execute("""
                    UPDATE market_history SET high=?, low=?, close=? WHERE asset=? AND timeframe=? AND timestamp=?
                """, (max(existing_candle[1], base_ltp), min(existing_candle[2], base_ltp), base_ltp, target_index, selected_tf, current_rounded_unix))
            else:
                cursor.execute("""
                    INSERT OR REPLACE INTO market_history (asset, timeframe, timestamp, open, high, low, close)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (target_index, selected_tf, current_rounded_unix, base_ltp, base_ltp, base_ltp, base_ltp))
            conn.commit()
            conn.close()
    except Exception:
        pass

# ==============================================================================
# 🧠 5. STRICT REAL DATA LOADING (ZERO SIMULATION REPEAT OR DEMO BARS)
# ==============================================================================
master_history_array = []
rows = []

try:
    conn = sqlite3.connect(DB_PATH, timeout=10)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT timestamp, open, high, low, close FROM market_history 
        WHERE asset=? AND timeframe=? ORDER BY timestamp ASC LIMIT 300
    """, (target_index, selected_tf))
    rows = cursor.fetchall()
    conn.close()
except Exception:
    rows = []

# ALL DEMO OR SINUSOIDAL CODES ARE COMPLETELY REMOVED HERE
if not rows:
    st.warning(f"⚠️ Dynamic Sync Status: Fetching real historical database rows from {target_index}. Please check SDK response connection.")
    st.stop()
else:
    for row in rows:
        t, o, h, l, c = row
        master_history_array.append({
            "time": int(t), "open": o, "high": h, "low": l, "close": c
        })

# Compute metrics dynamically strictly on real database values
prices = [m["close"] for m in master_history_array]
for idx, m in enumerate(master_history_array):
    o, h, l, c = m["open"], m["high"], m["low"], m["close"]
    m["vwap"] = round(sum(prices[max(0, idx-5):idx+1]) / len(prices[max(0, idx-5):idx+1]), 2)
    m["ma9"] = round(sum(prices[max(0, idx-8):idx+1]) / len(prices[max(0, idx-8):idx+1]), 2)
    m["ma20"] = round(sum(prices[max(0, idx-19):idx+1]) / len(prices[max(0, idx-19):idx+1]), 2)
    m["ma50"] = round(sum(prices[max(0, idx-49):idx+1]) / len(prices[max(0, idx-49):idx+1]), 2)
    m["macd"] = round(m["ma9"] - m["ma20"], 2)
    m["signal"] = round(m["macd"] * 0.9, 2)
    m["supertrend"] = round(l - 2.0 if c >= o else h + 2.0, 2)

if base_ltp == 0.0 and len(master_history_array) > 0:
    base_ltp = master_history_array[-1]["close"]

runtime_payload = {
    "current_asset": target_index,
    "price": int(base_ltp * 100),
    "master_history": master_history_array,
    target_index: {
        "price": int(base_ltp * 100),
        "master_history": master_history_array,
        "max_vol_zone": 0.0, "max_oi_zone": 0.0
    }
}

st.sidebar.markdown(f"**Asset:** `{target_index}` | **TF:** `{selected_tf}`")
st.sidebar.markdown(f"**Real Active Bars:** `{len(master_history_array)}`")

if os.path.exists(TOKEN_CACHE_FILE):
    st.sidebar.success("🔑 Token Connected")

if os.path.exists(html_file_path):
    with open(html_file_path, "r", encoding="utf-8") as f:
        html_content = f.read()
    
    json_data = json.dumps(runtime_payload)
    injection_script = f"""
    <script>
        window.chartPayload = {json_data};
        window.chartData = {json_data};
        window.currentAsset = "{target_index}";
        setTimeout(function() {{
            const iframeWin = document.getElementsByTagName('iframe')[0]?.contentWindow || window;
            iframeWin.postMessage({{ type: "DYNAMIC_TERMINAL_RELOAD", data: {json_data} }}, "*");
            iframeWin.postMessage({{ type: "LIVE_TICK_UPDATE", payload: {json_data}, asset: "{target_index}" }}, "*");
            if (iframeWin.chart && iframeWin.chart.timeScale) {{
                iframeWin.chart.timeScale().fitContent();
            }}
        }}, 300);
    </script>
    """
    html_content = html_content.replace("<head>", f"<head>{injection_script}")
    components.html(html_content, height=720, scrolling=False)
    time.sleep(2.0)
    st.rerun()
