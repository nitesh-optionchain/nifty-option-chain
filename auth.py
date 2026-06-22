# auth.py
import os
import json
from datetime import datetime, timedelta
from settings import USER_FILE, DATA_FILE, ADMIN_DB_DEFAULT, SUPER_ADMIN_IDS

def load_json(file_path, default_val):
    if os.path.exists(file_path):
        try:
            with open(file_path, "r") as f: 
                return json.load(f)
        except: 
            pass
    return default_val

def save_json(file_path, data_to_save):
    try:
        with open(file_path, "w") as f: 
            json.dump(data_to_save, f, indent=4)
    except: 
        pass

# Database Initialization
ADMIN_DB = load_json(USER_FILE, ADMIN_DB_DEFAULT)
SUBSCRIPTION_DB = load_json(DATA_FILE, {})

for uid in ADMIN_DB:
    if uid not in SUBSCRIPTION_DB:
        SUBSCRIPTION_DB[uid] = {
            "status": "Paid" if uid in SUPER_ADMIN_IDS else "Unpaid",
            "expiry_date": "2030-12-31" if uid in SUPER_ADMIN_IDS else (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d"),
            "last_transaction_id": "INITIAL_BETA"
        }
save_json(DATA_FILE, SUBSCRIPTION_DB)

# auth.py (Bina change kiya hua extra logic function)
import os
import json
from datetime import datetime, timedelta
from settings import USER_FILE, DATA_FILE, ADMIN_DB_DEFAULT, SUPER_ADMIN_IDS

def load_json(file_path, default_val):
    if os.path.exists(file_path):
        try:
            with open(file_path, "r") as f: 
                return json.load(f)
        except: 
            pass
    return default_val

def save_json(file_path, data_to_save):
    try:
        with open(file_path, "w") as f: 
            json.dump(data_to_save, f, indent=4)
    except: 
        pass

# Database Initialization
ADMIN_DB = load_json(USER_FILE, ADMIN_DB_DEFAULT)
SUBSCRIPTION_DB = load_json(DATA_FILE, {})

for uid in ADMIN_DB:
    if uid not in SUBSCRIPTION_DB:
        SUBSCRIPTION_DB[uid] = {
            "status": "Paid" if uid in SUPER_ADMIN_IDS else "Unpaid",
            "expiry_date": "2030-12-31" if uid in SUPER_ADMIN_IDS else (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d"),
            "last_transaction_id": "INITIAL_BETA"
        }
save_json(DATA_FILE, SUBSCRIPTION_DB)

# 🌟 ADDED HERE - Real-time calculation loop to isolate license validities
def check_user_subscription_status(user_id):
    if user_id in SUPER_ADMIN_IDS:
        return True
    user_data = SUBSCRIPTION_DB.get(user_id, {})
    if user_data.get("status") == "Paid":
        try:
            expiry = datetime.strptime(user_data.get("expiry_date", ""), "%Y-%m-%d")
            if datetime.now() <= expiry:
                return True
        except: pass
    return False
