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

if BASE_DIR not in sys.path:
    sys.path.append(BASE_DIR)

def init_market_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS market_history (
            asset TEXT,
            timestamp INTEGER,
            open REAL,
            high REAL,
            low REAL,
            close REAL,
            PRIMARY KEY (asset, timestamp)
        )
    """)
    conn.commit()
    conn.close()

init_market_db()

# ==============================================================================
# 🔌 RAW SDK INTENT INSTANTIATION
# ==============================================================================
from nubra_python_sdk.start_sdk import InitNubraSdk, NubraEnv
from nubra_python_sdk.marketdata.market_data import MarketData

PHONE_NO = st.secrets.get("PHONE_NO") or os.environ.get("PHONE_NO")
MPIN = st.secrets.get("MPIN") or os.environ.get("MPIN")

if PHONE_NO and MPIN:
    os.environ["PHONE_NO"] = str(PHONE_NO)
    os.environ["MPIN"] = str(MPIN)

try:
    # Set matching runtime environment setup mappings
    sdk_client = InitNubraSdk(NubraEnv.PROD, env_creds=True)
    market_engine = MarketData(sdk_client)
except Exception as e:
    market_engine = None
    st.sidebar.error(f"Initialization Failed: {str(e)}")

target_index = st.sidebar.selectbox("Active Asset Frame", ["NIFTY", "SENSEX"], index=0)

# ==============================================================================
# 🧠 EXACT HISTORICAL DATA PARSING LOGIC FROM DOCUMENTATION
# ==============================================================================
if market_engine is not None:
    try:
        exch_name = "NSE" if target_index == "NIFTY" else "BSE"
        type_name = "INDEX" # Calibrated index anchor structure map
        
        # Datetime configuration setup rules matching API structure
        end_dt = datetime.utcnow()
        start_dt = end_dt - timedelta(days=2)
        
        # VALIDATED CALL: historical_data mapping from official docs structure
        response = market_engine.historical_data({
            "exchange": exch_name,
            "type": type_name,
            "values": [target_index],
            "fields": ["open", "high", "low", "close"],
            "startDate": start_dt.strftime("%Y-%m-%dT%H:%M:%S.000Z"),
            "endDate": end_dt.strftime("%Y-%m-%dT%H:%M:%S.000Z"),
            "interval": "1m",
            "intraDay": False,
            "realTime": False
        })

        # Step-by-Step Explicit Attribute Traversal based on dynamic signature
        if response and hasattr(response, 'result') and response.result:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            
            for chart_data in response.result:
                if hasattr(chart_data, 'values') and chart_data.values:
                    for element in chart_data.values:
                        if isinstance(element, dict) and target_index in element:
                            stock_chart = element[target_index]
                            
                            # Extract lists of TimeSeriesPoints attributes from object
                            opens = getattr(stock_chart, 'open', None) or []
                            highs = getattr(stock_chart, 'high', None) or []
                            lows = getattr(stock_chart, 'low', None) or []
                            closes = getattr(stock_chart, 'close', None) or []
                            
                            # Zip timeline parameters cleanly using matching structural indices
                            for i in range(len(opens)):
                                try:
                                    # Nanosecond conversion adjustment to standard unix epoch seconds format
                                    raw_ts = opens[i].timestamp
                                    sec_ts = int(raw_ts // 1000000000) if raw_ts > 9999999999 else int(raw_ts)
                                    
                                    o = float(opens[i].value)
                                    h = float(highs[i].value) if i < len(highs) else o
                                    l = float(lows[i].value) if i < len(lows) else o
                                    c = float(closes[i].value) if i < len(closes) else o

                                    # Divide by 100 format handler matching pricing grids layers
                                    o_f = o / 100.0 if o > 100000 else o
                                    h_f = h / 100.0 if h > 100000 else h
                                    l_f = l / 100.0 if l > 100000 else l
                                    c_f = c / 100.0 if c > 100000 else c

                                    cursor.execute("""
                                        INSERT OR REPLACE INTO market_history (asset, timestamp, open, high, low, close)
                                        VALUES (?, ?, ?, ?, ?, ?)
                                    """, (target_index, sec_ts, o_f, h_f, l_f, c_f))
                                except Exception:
                                    continue
            conn.commit()
            conn.close()

        # ==============================================================================
        # ⚡ 2. REAL-TIME TICK SYNC MATRIX OVERLAY
        # ==============================================================================
        snap = market_engine.current_price(target_index, exchange=exch_name)
        if snap and getattr(snap, 'price', None):
            raw_price = float(snap.price)
            base_val = raw_price / 100.0 if raw_price > 100000 else raw_price
            current_rounded_unix = (int(time.time()) // 60) * 60
            
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute("SELECT open, high, low, close FROM market_history WHERE asset=? AND timestamp=?", (target_index, current_rounded_unix))
            existing_candle = cursor.fetchone()
            
            if existing_candle:
                new_high = max(existing_candle[1], base_val)
                new_low = min(existing_candle[2], base_val)
                cursor.execute("""
                    UPDATE market_history SET high=?, low=?, close=? WHERE asset=? AND timestamp=?
                """, (new_high, new_low, base_val, target_index, current_rounded_unix))
            else:
                cursor.execute("""
                    INSERT OR REPLACE INTO market_history (asset, timestamp, open, high, low, close)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (target_index, current_rounded_unix, base_val, base_val, base_val, base_val))
            conn.commit()
            conn.close()
    except Exception as e:
        st.sidebar.error(f"Sync Frame Error: {str(e)}")

# Read operational structural timelines from DB
master_history_array = []
try:
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT timestamp, open, high, low, close FROM market_history 
        WHERE asset=? ORDER BY timestamp ASC LIMIT 200
    """, (target_index,))
    rows = cursor.fetchall()
    conn.close()
    
    for row in rows:
        master_history_array.append({
            "time": int(row[0]), "open": row[1], "high": row[2], "low": row[3], "close": row[4]
        })
except Exception:
    pass

if master_history_array:
    current_display_price = master_history_array[-1]["close"]
else:
    current_display_price = 0.0

runtime_payload = {
    target_index: {
        "price": int(current_display_price * 100),
        "master_history": master_history_array
    }
}

st.sidebar.markdown(f"**Loaded SDK Bars:** `{len(master_history_array)}`")

if os.path.exists(html_file_path):
    with open(html_file_path, "r", encoding="utf-8") as f:
        html_content = f.read()

    json_data = json.dumps(runtime_payload)
    
    injection_script = f"""
    <script>
        window.chartData = {json_data};
        window.currentAsset = "{target_index}";
        
        setTimeout(function() {{
            const iframeWin = document.getElementsByTagName('iframe')[0]?.contentWindow || window;
            iframeWin.postMessage({{ 
                type: "LIVE_TICK_UPDATE", 
                payload: {json_data}, 
                asset: "{target_index}" 
            }}, "*");
        }}, 250);
    </script>
    """
    html_content = html_content.replace("<head>", f"<head>{injection_script}")
    components.html(html_content, height=720, scrolling=False)
    
    time.sleep(2.0)
    st.rerun()
else:
    st.error("❌ 'index.html' file nahi mili!")
