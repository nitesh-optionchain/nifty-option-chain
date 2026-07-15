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
# 🌐 PUBLIC HISTORICAL BYPASS FILTER (Runs Even When Broker API Fails)
# ==============================================================================
def fetch_failsafe_history(asset_name):
    try:
        import yfinance as yf
        ticker_symbol = "^NSEI" if asset_name == "NIFTY" else "^BSESN"
        ticker = yf.Ticker(ticker_symbol)
        
        # Pulling 2 days of solid 1-minute historical bars
        df = ticker.history(period="2d", interval="1m")
        if not df.empty:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            for index, row in df.iterrows():
                t_stamp = int(index.timestamp())
                cursor.execute("""
                    INSERT OR REPLACE INTO market_history (asset, timestamp, open, high, low, close)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (asset_name, t_stamp, float(row['Open']), float(row['High']), float(row['Low']), float(row['Close'])))
            conn.commit()
            conn.close()
    except Exception:
        pass

# ==============================================================================
# 🔌 BROKER LIVE INTEGRATION
# ==============================================================================
from nubra_python_sdk.start_sdk import InitNubraSdk, NubraEnv
from nubra_python_sdk.marketdata.market_data import MarketData

@st.cache_resource(show_spinner=False)
def get_sdk_connector():
    try:
        client = InitNubraSdk(NubraEnv.PROD, env_creds=True)
        return MarketData(client)
    except Exception:
        return None

market_engine = get_sdk_connector()
target_index = st.sidebar.selectbox("Active Asset Frame", ["NIFTY", "SENSEX"], index=0)

# 1. Trigger the Public Failsafe History first so chart never stays empty
fetch_failsafe_history(target_index)

# 2. Intercept and overlay current live ticks onto the historical canvas
if market_engine:
    try:
        exch_name = "NSE" if target_index == "NIFTY" else "BSE"
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
    except Exception:
        pass

# Read final timeline database rows to deliver to Javascript
master_history_array = []
try:
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    # Loading 120 actual historical data blocks sorted chronologically
    cursor.execute("""
        SELECT timestamp, open, high, low, close FROM market_history 
        WHERE asset=? ORDER BY timestamp ASC LIMIT 120
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

st.sidebar.markdown(f"**Total Loaded Bars:** `{len(master_history_array)}`")

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
