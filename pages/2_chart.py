import os
import time
import threading
from flask import Flask, send_from_directory, jsonify, request

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
app = Flask(__name__, static_folder=BASE_DIR, static_url_path='')

from nubra_python_sdk.start_sdk import InitNubraSdk, NubraEnv
from nubra_python_sdk.marketdata.market_data import MarketData

# Dual Asset Database Memory Structure
master_storage = {
    "NIFTY": {"price": 2444990, "status": "FROZEN", "master_history": []},
    "SENSEX": {"price": 8035000, "status": "FROZEN", "master_history": []} # Sensex default placeholder base
}

def get_nubra_session():
    try:
        return InitNubraSdk(NubraEnv.PROD, env_creds=True)
    except:
        return None

nubra_client = get_nubra_session()
market_engine = MarketData(nubra_client) if nubra_client else None

def fetch_data_stream_loop():
    global master_storage
    print("Dual Asset Master Pipeline Active (NIFTY & SENSEX)...")
    
    while True:
        try:
            if market_engine:
                # 1. Fetch NIFTY Data
                nifty_snap = market_engine.current_price("NIFTY", exchange="NSE")
                if nifty_snap and nifty_snap.price:
                    real_nifty = float(nifty_snap.price) / 100
                    master_storage["NIFTY"]["price"] = int(nifty_snap.price)
                    master_storage["NIFTY"]["status"] = "FROZEN"
                    master_storage["NIFTY"]["master_history"].append({
                        "open": real_nifty, "high": real_nifty, "low": real_nifty, "close": real_nifty
                    })
                    if len(master_storage["NIFTY"]["master_history"]) > 1000:
                        master_storage["NIFTY"]["master_history"].pop(0)

                # 2. Fetch SENSEX Data (BSE Exchange)
                sensex_snap = market_engine.current_price("SENSEX", exchange="BSE")
                if sensex_snap and sensex_snap.price:
                    real_sensex = float(sensex_snap.price) / 100
                    master_storage["SENSEX"]["price"] = int(sensex_snap.price)
                    master_storage["SENSEX"]["status"] = "FROZEN"
                    master_storage["SENSEX"]["master_history"].append({
                        "open": real_sensex, "high": real_sensex, "low": real_sensex, "close": real_sensex
                    })
                    if len(master_storage["SENSEX"]["master_history"]) > 1000:
                        master_storage["SENSEX"]["master_history"].pop(0)
                        
        except Exception as error:
            print(f"Data Pipe Warning: {error}")
        time.sleep(1)

# API accepts both Asset & Timeframe dynamically
@app.route('/api/live-data')
def get_live_data():
    global master_storage
    
    requested_asset = request.args.get('asset', 'NIFTY')
    if requested_asset not in master_storage:
        requested_asset = 'NIFTY'
        
    target_data = master_storage[requested_asset]
    
    payload = {
        "price": target_data["price"],
        "status": target_data["status"],
        "master_history": target_data["master_history"]
    }
    return jsonify(payload)

@app.route('/')
def serve_index():
    return send_from_directory(BASE_DIR, 'index.html')

if __name__ == '__main__':
    data_thread = threading.Thread(target=fetch_data_stream_loop, daemon=True)
    data_thread.start()
    app.run(port=3000, debug=True, use_reloader=False)
