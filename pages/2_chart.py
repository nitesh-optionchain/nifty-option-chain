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

# ==============================================================================
# 🗄️ 1. AUTOMATIC TIME-FRAME DATA ARCHITECTURE
# ==============================================================================
def init_market_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS market_history (
            asset TEXT, timeframe TEXT, timestamp INTEGER, open REAL, high REAL, low REAL, close REAL,
            PRIMARY KEY (asset, timeframe, timestamp)
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS institutional_zones (
            asset TEXT, zone_type TEXT, price_level REAL, is_frozen INTEGER, last_updated INTEGER,
            PRIMARY KEY (asset, zone_type)
        )
    """)
    conn.commit()
    conn.close()

init_market_db()

# ==============================================================================
# 🔌 2. PRODUCTION SDK CONNECTORS
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

# Streamlit Active Workspace Sidebar Dropdowns
target_index = st.sidebar.selectbox("Active Asset Frame", ["NIFTY", "SENSEX"], index=0)
selected_tf = st.sidebar.selectbox("Timeframe Window", ["5m", "10m", "15m", "30m", "1d"], index=0)

tf_map = {"5m": 5, "10m": 10, "15m": 15, "30m": 30, "1d": 1440}
interval_minutes = tf_map[selected_tf]
interval_seconds = interval_minutes * 60

# ==============================================================================
# 📊 3. STRICT HISTORICAL DATA SYNC GENERATOR (FAIL-SAFE)
# ==============================================================================
def force_sync_historical_bars(asset_name, engine, timeframe):
    if engine is None:
        return
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Check current row count to verify database dry/empty state
        cursor.execute("SELECT COUNT(*) FROM market_history WHERE asset=? AND timeframe=?", (asset_name, timeframe))
        current_bars = cursor.fetchone()[0]
        
        # FIXED FAILSAFE: If database has less than 40 bars, force pull historical batch data instantly
        if current_bars < 40:
            exch = "NSE" if asset_name == "NIFTY" else "BSE"
            end_d = datetime.utcnow()
            start_d = end_d - timedelta(days=6) # 6 Days Deep Range Fetch
            
            response = engine.historical_data({
                "exchange": exch, "type": "INDEX", "values": [asset_name],
                "fields": ["open", "high", "low", "close"],
                "startDate": start_d.strftime("%Y-%m-%dT%H:%M:%S.000Z"),
                "endDate": end_d.strftime("%Y-%m-%dT%H:%M:%S.000Z"),
                "interval": timeframe, 
                "intraDay": False, "realTime": False
            })
            
            if response and hasattr(response, 'result') and response.result:
                for chart_data in response.result:
                    vals = getattr(chart_data, 'values', None) or []
                    for element in (vals if isinstance(vals, list) else [vals]):
                        chart = element.get(asset_name) if isinstance(element, dict) else getattr(element, asset_name, None)
                        if chart:
                            opens = getattr(chart, 'open', None) or []
                            highs = getattr(chart, 'high', None) or []
                            lows = getattr(chart, 'low', None) or []
                            closes = getattr(chart, 'close', None) or []
                            
                            for i in range(len(opens)):
                                try:
                                    raw_ts = opens[i].timestamp
                                    sec_ts = int(raw_ts // 1000000000) if raw_ts > 9999999999 else int(raw_ts)
                                    
                                    o_f = float(opens[i].value)
                                    h_f = float(highs[i].value) if i < len(highs) else o_f
                                    l_f = float(lows[i].value) if i < len(lows) else o_f
                                    c_f = float(closes[i].value) if i < len(closes) else o_f

                                    o_f = o_f / 100.0 if o_f > 100000 else o_f
                                    h_f = h_f / 100.0 if h_f > 100000 else h_f
                                    l_f = l_f / 100.0 if l_f > 100000 else l_f
                                    c_f = c_f / 100.0 if c_f > 100000 else c_f

                                    cursor.execute("""
                                        INSERT OR REPLACE INTO market_history (asset, timeframe, timestamp, open, high, low, close)
                                        VALUES (?, ?, ?, ?, ?, ?, ?)
                                    """, (asset_name, timeframe, sec_ts, o_f, h_f, l_f, c_f))
                                except Exception:
                                    continue
                conn.commit()
        conn.close()
    except Exception:
        pass

# Force trigger un-locked baseline validation directly inside lifecycle loop
force_sync_historical_bars(target_index, market_engine, selected_tf)

# ==============================================================================
# ⚡ 4. LIVE RUNTIME INDEX PIPELINE
# ==============================================================================
if market_engine is not None:
    try:
        exch_name = "NSE" if target_index == "NIFTY" else "BSE"
        snap = market_engine.current_price(target_index, exchange=exch_name)
        if snap and getattr(snap, 'price', None):
            raw_price = float(snap.price)
            base_val = raw_price / 100.0 if raw_price > 100000 else raw_price
            current_rounded_unix = (int(time.time()) // interval_seconds) * interval_seconds
            
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute("SELECT open, high, low, close FROM market_history WHERE asset=? AND timeframe=? AND timestamp=?", (target_index, selected_tf, current_rounded_unix))
            existing_candle = cursor.fetchone()
            
            if existing_candle:
                cursor.execute("""
                    UPDATE market_history SET high=?, low=?, close=? WHERE asset=? AND timeframe=? AND timestamp=?
                """, (max(existing_candle[1], base_val), min(existing_candle[2], base_val), base_val, target_index, selected_tf, current_rounded_unix))
            else:
                cursor.execute("""
                    INSERT OR REPLACE INTO market_history (asset, timeframe, timestamp, open, high, low, close)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (target_index, selected_tf, current_rounded_unix, base_val, base_val, base_val, base_val))
            conn.commit()
            conn.close()
    except Exception:
        pass

# ==============================================================================
# 🧠 5. INTERNAL TECHNICAL CALCULATIONS ARRAY DECK
# ==============================================================================
master_history_array = []
try:
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT timestamp, open, high, low, close FROM market_history 
        WHERE asset=? AND timeframe=? ORDER BY timestamp ASC LIMIT 250
    """, (target_index, selected_tf))
    rows = cursor.fetchall()
    conn.close()
    
    prices = [r[4] for r in rows]
    cum_pv = 0.0
    cum_vol = 0.0
    
    for idx, row in enumerate(rows):
        t, o, h, l, c = row
        typ_p = (h + l + c) / 3.0
        sim_v = 100.0
        cum_pv += typ_p * sim_v
        cum_vol += sim_v
        vwap_val = round(cum_pv / cum_vol, 2)
        
        ma9 = round(sum(prices[max(0, idx-8):idx+1]) / len(prices[max(0, idx-8):idx+1]), 2)
        ma20 = round(sum(prices[max(0, idx-19):idx+1]) / len(prices[max(0, idx-19):idx+1]), 2)
        ma50 = round(sum(prices[max(0, idx-49):idx+1]) / len(prices[max(0, idx-49):idx+1]), 2)
        
        macd_line = round(ma9 - ma20, 2)
        signal_line = round(macd_line * 0.9, 2)
        
        atr_range = (h - l) if (h - l) > 0 else 5.0
        supertrend = round(((h + l) / 2.0) - (2.5 * atr_range) if c >= o else ((h + l) / 2.0) + (2.5 * atr_range), 2)
        
        master_history_array.append({
            "time": int(t), "open": o, "high": h, "low": l, "close": c,
            "vwap": vwap_val, "ma9": ma9, "ma20": ma20, "ma50": ma50,
            "macd": macd_line, "signal": signal_line, "supertrend": supertrend
        })
except Exception:
    pass

runtime_payload = {
    target_index: {
        "price": int((master_history_array[-1]["close"] * 100) if master_history_array else 0),
        "master_history": master_history_array,
        "max_vol_zone": 0.0,
        "max_oi_zone": 0.0
    }
}

st.sidebar.markdown(f"**Interval Active:** `{selected_tf}`")
st.sidebar.markdown(f"**Total Sequenced Bars:** `{len(master_history_array)}`")

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
            iframeWin.postMessage({{ type: "LIVE_TICK_UPDATE", payload: {json_data}, asset: "{target_index}" }}, "*");
        }}, 250);
    </script>
    """
    html_content = html_content.replace("<head>", f"<head>{injection_script}")
    components.html(html_content, height=720, scrolling=False)
    time.sleep(2.0)
    st.rerun()
