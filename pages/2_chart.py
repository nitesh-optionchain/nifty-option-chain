import os
import sys
import json
from datetime import datetime, timedelta
from flask import Flask, jsonify, request
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# 📂 Paths & Imports Setup
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.append(BASE_DIR)

from nubra_python_sdk.start_sdk import InitNubraSdk, NubraEnv
from nubra_python_sdk.marketdata.market_data import MarketData

# ========================================================
# 🔐 SECURE CREDENTIALS SETUP (Apne Real Details Yahan Dalein)
# ========================================================
USER_PHONE = "YOUR_PHONE_NO"  # <-- Apna registered phone no. dalein (e.g., "9876543210")
USER_MPIN = "YOUR_MPIN"        # <-- Apna 4 ya 6 digit MPIN dalein

# Set OS environments before initializing SDK
os.environ["PHONE_NO"] = str(USER_PHONE)
os.environ["MPIN"] = str(USER_MPIN)

market_data = None
client = None

def init_broker_session():
    global client, market_data
    try:
        # Pura secure handshake framework configuration map kiya
        client = InitNubraSdk(NubraEnv.PROD, env_creds=True)
        market_data = MarketData(client)
        print("🚀 Broker SDK Connected & Logged In Successfully!")
        return True
    except Exception as e:
        print(f"❌ SDK Critical Authentication Fail: {e}")
        return False

# Trigger session on server wake up
init_broker_session()

master_storage = {
    "NIFTY": {"price": 0, "change": 0, "master_history": []},
    "SENSEX": {"price": 0, "change": 0, "master_history": []},
    "BANKNIFTY": {"price": 0, "change": 0, "master_history": []},
    "INDIAVIX": {"price": 0, "change": 0, "master_history": []}
}

# --- 📈 HISTORICAL ENGINE WITH STRUCT VALIDATION ---
def load_historical_candles(asset_name, timeframe="5m"):
    if not market_data:
        print("⚠️ SDK Session is dead. Skipping fetch.")
        return

    end_dt = datetime.utcnow()
    days_back = 30 if "d" in timeframe or "w" in timeframe else 5
    start_dt = end_dt - timedelta(days=days_back)
    
    start_str = start_dt.strftime("%Y-%m-%dT00:00:00.000Z")
    end_str = end_dt.strftime("%Y-%m-%dT23:59:59.000Z")
    
    try:
        # VIX and Index payload validation blocks
        if asset_name == "INDIAVIX":
            response = market_data.historical_data({
                "exchange": "NSE_VIX", "type": "VIX", "values": ["INDIAVIX"],
                "fields": ["open", "high", "low", "close"],
                "startDate": start_str, "endDate": end_str, "interval": timeframe,
                "intraDay": True, "realTime": False
            })
        else:
            exch = "BSE" if asset_name == "SENSEX" else "NSE"
            response = market_data.historical_data({
                "exchange": exch, "type": "INDEX", "values": [asset_name],
                "fields": ["open", "high", "low", "close"],
                "startDate": start_str, "endDate": end_str, "interval": timeframe,
                "intraDay": True if "m" in timeframe else False, "realTime": False
            })
            
        # Safe Attribute Extraction Engine (.result check framework)
        if not response or not hasattr(response, 'result') or not response.result:
            print(f"⚠️ Blank or Invalid Struct Response from SDK for {asset_name}")
            return
            
        raw_data = response.result[0].values[0][asset_name]
        parsed = []
        for i in range(len(raw_data.open)):
            parsed.append({
                "open": float(raw_data.open[i].value) / 100,
                "high": float(raw_data.high[i].value) / 100,
                "low": float(raw_data.low[i].value) / 100,
                "close": float(raw_data.close[i].value) / 100
            })
        master_storage[asset_name]["master_history"] = parsed
        print(f"✅ Loaded {len(parsed)} candles for {asset_name} ({timeframe})")
    except Exception as e:
        print(f"⚠️ History fetch failed for {asset_name}: {e}")

# --- 🔌 API ENDPOINT FOR FRONTEND ---
@app.route('/api/live-data', methods=['GET'])
def get_live_data():
    asset = request.args.get('asset', 'NIFTY')
    tf = request.args.get('tf', '5m')
    
    if not master_storage[asset]["master_history"]:
        load_historical_candles(asset, tf)
        
    try:
        if market_data:
            exch_map = "NSE_VIX" if asset == "INDIAVIX" else ("BSE" if asset == "SENSEX" else "NSE")
            live_snap = market_data.current_price(asset, exchange=exch_map)
            if live_snap and hasattr(live_snap, 'price') and live_snap.price:
                master_storage[asset]["price"] = int(live_snap.price)
                master_storage[asset]["change"] = float(live_snap.change) / 100 if hasattr(live_snap, 'change') else 0
    except Exception as e:
        pass
        
    return jsonify(master_storage[asset])

if __name__ == '__main__':
    # Initial base load for active indices
    load_historical_candles("NIFTY", "5m")
    load_historical_candles("INDIAVIX", "5m")
    app.run(host='0.0.0.0', port=5000, debug=True)
