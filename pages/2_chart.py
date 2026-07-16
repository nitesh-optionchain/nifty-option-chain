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
# 🔌 RAW CONNECTOR INITIALIZATION
# ==============================================================================
from nubra_python_sdk.start_sdk import InitNubraSdk, NubraEnv
from nubra_python_sdk.marketdata.market_data import MarketData

PHONE_NO = st.secrets.get("PHONE_NO") or os.environ.get("PHONE_NO")
MPIN = st.secrets.get("MPIN") or os.environ.get("MPIN")

if PHONE_NO and MPIN:
    os.environ["PHONE_NO"] = str(PHONE_NO)
    os.environ["MPIN"] = str(MPIN)

try:
    sdk_client = InitNubraSdk(NubraEnv.PROD, env_creds=True)
    market_engine = MarketData(sdk_client)
except Exception as e:
    market_engine = None
    st.sidebar.error(f"Login Failure: {str(e)}")

target_index = st.sidebar.selectbox("Active Asset Frame", ["NIFTY", "SENSEX"], index=0)
selected_tf = st.sidebar.selectbox("Timeframe Window", ["1m", "5m", "10m", "15m", "30m", "1d"], index=1)

tf_seconds_map = {"1m": 60, "5m": 300, "10m": 600, "15m": 900, "30m": 1800, "1d": 86400}
interval_seconds = tf_seconds_map[selected_tf]

state_key = f"fetch_done_{target_index}_{selected_tf}"

# ==============================================================================
# 🧠 FOOLPROOF SAFE EXTRACTOR FUNCTION (AVOIDS TIMEOUTS & INSTANCE PASSING ERRORS)
# ==============================================================================
def execute_safe_sdk_fetch(engine, asset, timeframe):
    try:
        exch = "NSE" if asset == "NIFTY" else "BSE"
        end_d = datetime.utcnow()
        start_d = end_d - timedelta(days=4)
        
        req_payload = {
            "exchange": exch,
            "type": "INDEX",
            "values": [asset],
            "fields": ["open", "high", "low", "close", "cumulative_volume", "cumulative_oi"],
            "startDate": start_d.strftime("%Y-%m-%dT%H:%M:%S.000Z"),
            "endDate": end_d.strftime("%Y-%m-%dT%H:%M:%S.000Z"),
            "interval": timeframe,
            "intraDay": False,
            "realTime": False
        }
        
        # Explicitly using object method invocation fallback to handle missing 'self' constraints natively
        if hasattr(engine, 'historical_data'):
            response = engine.historical_data(req_payload)
        else:
            response = MarketData.historical_data(engine, req_payload)
            
        chart_data_list = []
        if response:
            if hasattr(response, 'result') and response.result:
                chart_data_list = response.result
            elif isinstance(response, dict) and 'result' in response:
                chart_data_list = response['result']
            elif isinstance(response, list):
                chart_data_list = response

        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        max_vol_price, max_oi_price = 0.0, 0.0
        highest_vol, highest_oi = -1, -1

        for chart_data in chart_data_list:
            vals_layer = getattr(chart_data, 'values', None) or (chart_data.get('values') if isinstance(chart_data, dict) else None)
            if not vals_layer: continue
            
            elements = vals_layer if isinstance(vals_layer, list) else [vals_layer]
            for element in elements:
                stock_chart = element.get(asset) if isinstance(element, dict) else getattr(element, asset, None)
                if stock_chart:
                    opens = getattr(stock_chart, 'open', None) or []
                    highs = getattr(stock_chart, 'high', None) or []
                    lows = getattr(stock_chart, 'low', None) or []
                    closes = getattr(stock_chart, 'close', None) or []
                    vols = getattr(stock_chart, 'cumulative_volume', None) or []
                    ois = getattr(stock_chart, 'cumulative_oi', None) or []
                    
                    for i in range(len(opens)):
                        try:
                            raw_ts = opens[i].timestamp
                            sec_ts = int(raw_ts // 1000000000) if raw_ts > 9999999999 else int(raw_ts)
                            
                            val_o = float(opens[i].value)
                            val_h = float(highs[i].value) if i < len(highs) else val_o
                            val_l = float(lows[i].value) if i < len(lows) else val_o
                            val_c = float(closes[i].value) if i < len(closes) else val_o

                            o_f = val_o / 100.0 if val_o > 100000 else val_o
                            h_f = val_h / 100.0 if val_h > 100000 else val_h
                            l_f = val_l / 100.0 if val_l > 100000 else val_l
                            c_f = val_c / 100.0 if val_c > 100000 else val_c

                            cursor.execute("""
                                INSERT OR REPLACE INTO market_history (asset, timeframe, timestamp, open, high, low, close)
                                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                            """, (asset, timeframe, sec_ts, o_f, h_f, l_f, c_f))

                            if i < len(vols) and float(vols[i].value) > highest_vol:
                                highest_vol = float(vols[i].value)
                                max_vol_price = c_f
                            if i < len(ois) and float(ois[i].value) > highest_oi:
                                highest_oi = float(ois[i].value)
                                max_oi_price = c_f
                        except Exception:
                            continue

        now_ts = int(time.time())
        current_dt = datetime.now()
        cursor.execute("SELECT price_level FROM institutional_zones WHERE asset=? AND zone_type='MAX_VOL'", (asset,))
        has_zone = cursor.fetchone()
        
        if not (current_dt.hour == 9 and current_dt.minute > 20 and has_zone):
            if max_vol_price > 0:
                cursor.execute("INSERT OR REPLACE INTO institutional_zones VALUES (?, 'MAX_VOL', ?, 1, ?)", (asset, max_vol_price, now_ts))
            if max_oi_price > 0:
                cursor.execute("INSERT OR REPLACE INTO institutional_zones VALUES (?, 'MAX_OI', ?, 1, ?)", (asset, max_oi_price, now_ts))

        conn.commit()
        conn.close()
        return True
    except Exception as ex:
        st.sidebar.warning(f"Fetch Intercepted: {str(ex)}")
        return False

# Execute Single Invocation Guard safely
if market_engine is not None and not st.session_state.get(state_key):
    success = execute_safe_sdk_fetch(market_engine, target_index, selected_tf)
    if success:
        st.session_state[state_key] = True

# ==============================================================================
# ⚡ LIVE QUOTES REAL-TIME BUFFER SYNC
# ==============================================================================
if market_engine is not None:
    try:
        exch_name = "NSE" if target_index == "NIFTY" else "BSE"
        if hasattr(market_engine, 'current_price'):
            snap = market_engine.current_price(target_index, exchange=exch_name)
        else:
            snap = MarketData.current_price(market_engine, target_index, exchange=exch_name)
            
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
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (target_index, selected_tf, current_rounded_unix, base_val, base_val, base_val, base_val))
            conn.commit()
            conn.close()
    except Exception:
        pass

# ==============================================================================
# 📊 GENERATE SMOOTH INDICATORS COEFFICIENTS
# ==============================================================================
master_history_array = []
max_vol_level, max_oi_level = 0.0, 0.0

try:
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT timestamp, open, high, low, close FROM market_history 
        WHERE asset=? AND timeframe=? ORDER BY timestamp ASC LIMIT 150
    """, (target_index, selected_tf))
    rows = cursor.fetchall()
    
    cursor.execute("SELECT zone_type, price_level FROM institutional_zones WHERE asset=?", (target_index,))
    z_rows = cursor.fetchall()
    for z in z_rows:
        if z[0] == 'MAX_VOL': max_vol_level = z[1]
        if z[0] == 'MAX_OI': max_oi_level = z[1]
    conn.close()

    prices = [r[4] for r in rows]
    cum_pv, cum_vol = 0.0, 0.0
    
    for idx, row in enumerate(rows):
        t, o, h, l, c = row
        typ_p = (h + l + c) / 3.0
        cum_pv += typ_p * 100.0
        cum_vol += 100.0
        vwap_val = round(cum_pv / cum_vol, 2)
        
        ma9 = round(sum(prices[max(0, idx-8):idx+1]) / len(prices[max(0, idx-8):idx+1]), 2)
        ma20 = round(sum(prices[max(0, idx-19):idx+1]) / len(prices[max(0, idx-19):idx+1]), 2)
        ma50 = round(sum(prices[max(0, idx-49):idx+1]) / len(prices[max(0, idx-49):idx+1]), 2)
        
        macd_line = round(ma9 - ma20, 2)
        signal_line = round(sum([p_ma9 - p_ma20 for p_ma9, p_ma20 in zip(prices[max(0, idx-8):idx+1], prices[max(0, idx-19):idx+1])]) / len(prices[max(0, idx-8):idx+1]), 2) if idx >= 8 else 0.0
        
        atr = (h - l) if (h - l) > 0 else 5.0
        st_val = round(((h + l) / 2.0) - (2.5 * atr) if c >= o else ((h + l) / 2.0) + (2.5 * atr), 2)

        master_history_array.append({
            "time": int(t), "open": o, "high": h, "low": l, "close": c,
            "vwap": vwap_val, "ma9": ma9, "ma20": ma20, "ma50": ma50,
            "macd": macd_line, "signal": signal_line, "supertrend": st_val
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
    "master_history": master_history_array,
    "max_vol_zone": max_vol_level,
    "max_oi_zone": max_oi_level
}

st.sidebar.markdown(f"⏱️ **Timeframe Matrix:** `{selected_tf}`")
st.sidebar.markdown(f"📌 **Max Vol Zone:** `{max_vol_level}`")
st.sidebar.markdown(f"📊 **Max OI Zone:** `{max_oi_level}`")
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
else:
    st.error("❌ 'index.html' file nahi mili!")
