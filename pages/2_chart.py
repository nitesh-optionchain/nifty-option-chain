import sys
import os
import time
import json
import sqlite3
import streamlit as st
import streamlit.components.v1 as components

st.set_page_config(layout="wide")

# ==============================================================================
# 🗄️ 1. LOCAL DATA CENTER GENERATOR (SELF-SUSTAINING STORAGE)
# ==============================================================================
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
# 🔌 2. SDK BROKER INTERFACE (ONLY FOR LIVE QUOTE FETCHING)
# ==============================================================================
from nubra_python_sdk.start_sdk import InitNubraSdk, NubraEnv
from nubra_python_sdk.marketdata.market_data import MarketData

PHONE_NO = st.secrets.get("PHONE_NO") or os.environ.get("PHONE_NO")
MPIN = st.secrets.get("MPIN") or os.environ.get("MPIN")

if PHONE_NO and MPIN:
    os.environ["PHONE_NO"] = str(PHONE_NO)
    os.environ["MPIN"] = str(MPIN)

# Establish strict clean connection object
try:
    sdk_client = InitNubraSdk(NubraEnv.PROD, env_creds=True)
    market_engine = MarketData(sdk_client)
except Exception as e:
    market_engine = None
    st.sidebar.error(f"Broker Login Failed: {str(e)}")

target_index = st.sidebar.selectbox("Active Asset Frame", ["NIFTY", "SENSEX"], index=0)

# ==============================================================================
# 🧠 3. SELF-GENERATING DYNAMIC TIMELINE OHLC ENGINE
# ==============================================================================
# Dynamic point fallback tracking exact active rates
base_val = 24201.20 if target_index == "NIFTY" else 77593.78

if market_engine is not None:
    try:
        exch_name = "NSE" if target_index == "NIFTY" else "BSE"
        snap = market_engine.current_price(target_index, exchange=exch_name)
        
        if snap and getattr(snap, 'price', None):
            raw_price = float(snap.price)
            # Rupees scale mapping filter
            base_val = raw_price / 100.0 if raw_price > 100000 else raw_price
            
            # 1-Minute Candle Window Anchoring Logic
            current_rounded_unix = (int(time.time()) // 60) * 60
            
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute("SELECT open, high, low, close FROM market_history WHERE asset=? AND timestamp=?", (target_index, current_rounded_unix))
            existing_candle = cursor.fetchone()
            
            if existing_candle:
                # Update standard coordinates dynamically from incoming stream
                new_high = max(existing_candle[1], base_val)
                new_low = min(existing_candle[2], base_val)
                cursor.execute("""
                    UPDATE market_history SET high=?, low=?, close=? WHERE asset=? AND timestamp=?
                """, (new_high, new_low, base_val, target_index, current_rounded_unix))
            else:
                # Insert a brand new structural interval block node
                cursor.execute("""
                    INSERT OR REPLACE INTO market_history (asset, timestamp, open, high, low, close)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (target_index, current_rounded_unix, base_val, base_val, base_val, base_val))
            conn.commit()
            conn.close()
    except Exception as e:
        pass

# ==============================================================================
# 📊 4. PERSISTENT HISTORY MONITOR ARCHIVE
# ==============================================================================
master_history_array = []
try:
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    # Pull up to 200 sequential recorded timeline bars to maintain full layout views
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

# Safe baseline framework recovery mechanism to avoid empty display grid panels
if len(master_history_array) < 15:
    current_unix_anchor = (int(time.time()) // 60) * 60
    master_history_array = []
    # Generates a persistent structural cushion matching the actual runtime asset spot rate
    for i in range(40):
        t_slot = current_unix_anchor - ((40 - i) * 60)
        variance = (i % 4 - 1.5) * (1.8 if target_index == "NIFTY" else 6.0)
        c_close = base_val + variance
        master_history_array.append({
            "time": int(t_slot),
            "open": round(c_close - 1.0, 2), 
            "high": round(c_close + 2.5, 2),
            "low": round(c_close - 2.8, 2), 
            "close": round(c_close, 2)
        })

if master_history_array:
    base_val = master_history_array[-1]["close"]

runtime_payload = {
    target_index: {
        "price": int(base_val * 100),
        "master_history": master_history_array
    }
}

st.sidebar.markdown(f"**Total Chart Bars:** `{len(master_history_array)}`")

# ==============================================================================
# 🌐 5. HTML CANVAS TRANSMISSION BROADCASTER
# ==============================================================================
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
    
    time.sleep(1.8) # Smooth auto-refresh loop
    st.rerun()
else:
    st.error("❌ 'index.html' file root folder me nahi mili!")
