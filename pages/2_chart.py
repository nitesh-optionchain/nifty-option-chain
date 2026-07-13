import os
import sys
import json
from datetime import datetime, timedelta
from flask import Flask, jsonify, request
from flask_cors import CORS

app = Flask(__name__)
CORS(app) # Taaki browser index.html ko block na kare

# 📂 Paths & Imports Setup
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.append(BASE_DIR)

from nubra_python_sdk.start_sdk import InitNubraSdk, NubraEnv
from nubra_python_sdk.marketdata.market_data import MarketData

# 🔐 Set Credentials (Apne hisab se change karein ya .env se chalayein)
os.environ["PHONE_NO"] = "YOUR_PHONE_NO"
os.environ["MPIN"] = "YOUR_MPIN"

# Initialize Broker SDK
try:
    client = InitNubraSdk(NubraEnv.PROD, env_creds=True)
    market_data = MarketData(client)
    print("🚀 Broker SDK Connected Successfully on Local PC!")
except Exception as e:
    print(f"❌ SDK Init Fail: {e}")
    sys.exit(1)

# Central Data Storage
master_storage = {
    "NIFTY": {"price": 0, "change": 0, "master_history": []},
    "SENSEX": {"price": 0, "change": 0, "master_history": []},
    "BANKNIFTY": {"price": 0, "change": 0, "master_history": []},
    "INDIAVIX": {"price": 0, "change": 0, "master_history": []}
}

# --- 📈 HISTORICAL ENGINE BLOCK ---
def load_historical_candles(asset_name, timeframe="5m"):
    end_dt = datetime.utcnow()
    days_back = 30 if "d" in timeframe or "w" in timeframe else 5
    start_dt = end_dt - timedelta(days=days_back)
    
    start_str = start_dt.strftime("%Y-%m-%dT00:00:00.000Z")
    end_str = end_dt.strftime("%Y-%m-%dT23:59:59.000Z")
    
    try:
        if asset_name == "INDIAVIX":
            response = market_data.historical_data({
                "exchange": "NSE_VIX", "type": "VIX", "values": ["INDIAVIX"],
                "fields": ["open", "high", "low", "close"],
                "startDate": start_str, "endDate": end_str, "interval": timeframe,
                "intraDay": True, "realTime": False
            })
            raw_data = response.result[0].values[0]["INDIAVIX"]
        else:
            exch = "BSE" if asset_name == "SENSEX" else "NSE"
            response = market_data.historical_data({
                "exchange": exch, "type": "INDEX", "values": [asset_name],
                "fields": ["open", "high", "low", "close"],
                "startDate": start_str, "endDate": end_str, "interval": timeframe,
                "intraDay": True if "m" in timeframe else False, "realTime": False
            })
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
        print(f"✅ Loaded {len(parsed)} historical candles for {asset_name} ({timeframe})")
    except Exception as e:
        print(f"⚠️ History fetch failed for {asset_name}: {e}")

# --- 🔌 API ENDPOINT FOR FRONTEND ---
@app.route('/api/live-data', methods=['GET'])
def get_live_data():
    asset = request.args.get('asset', 'NIFTY')
    tf = request.args.get('tf', '5m')
    
    # 1. Agar history khali hai, to pehle fetch karo
    if not master_storage[asset]["master_history"]:
        load_historical_candles(asset, tf)
        
    # 2. Live data check logic (Sirf tab hit karega jab market open ho)
    try:
        exch_map = "NSE_VIX" if asset == "INDIAVIX" else ("BSE" if asset == "SENSEX" else "NSE")
        live_snap = market_data.current_price(asset, exchange=exch_map)
        if live_snap and live_snap.price:
            master_storage[asset]["price"] = int(live_snap.price)
            master_storage[asset]["change"] = float(live_snap.change) / 100 if hasattr(live_snap, 'change') else 0
    except Exception as e:
        pass # Market closed hone par chupchaap purana data return karega
        
    return jsonify(master_storage[asset])

if __name__ == '__main__':
    # Initial base load for active indices
    load_historical_candles("NIFTY", "5m")
    load_historical_candles("INDIAVIX", "5m")
    app.run(host='0.0.0.0', port=5000, debug=True)
