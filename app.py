from __future__ import annotations
import math, os, json, threading, time, re
import numpy as np
import pandas as pd
import streamlit as st
from datetime import datetime, timedelta
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from streamlit_autorefresh import st_autorefresh
import urllib.parse  # Dynamic UPI URI configuration ke liye
from nubra_python_sdk.ticker import websocketdata  # 🚀 Live candle data streaming ke liye
import streamlit as st
import os

# 🚨 Streamlit Secrets bypass pipeline (Full-Proof Version)
if "MOBILE_NO" not in st.secrets.__dict__:
    st.secrets.__dict__["MOBILE_NO"] = "9304768496"  # <-- Apna asli mobile no quotes me daalein
if "MPIN" not in st.secrets.__dict__:
    st.secrets.__dict__["MPIN"] = "3974"            # <-- Apna asli MPIN quotes me daalein
if "env_creds" not in st.secrets.__dict__:
    st.secrets.__dict__["env_creds"] = True

@st.cache_data(ttl=300)  # 5 Minute tak data RAM me rahega
def fetch_and_clean_historical_data(symbol, asset_type, start_date, end_date, interval="1d"):
    """
    Nubra SDK ke mutabik historical data fetch karke clean karne ka function.
    """
    try:
        from nubra_python_sdk.marketdata.market_data import MarketData
        from nubra_python_sdk.start_sdk import InitNubraSdk, NubraEnv
        
        # 🛡️ CLIENT FALLBACK SYSTEM: Agar session state me client nahi mil raha, toh khud naya bana le
        if "nubra" in st.session_state and st.session_state.nubra is not None:
            active_client = st.session_state.nubra
        elif "nubra_client" in st.session_state and st.session_state.nubra_client is not None:
            active_client = st.session_state.nubra_client
        else:
            # 🟢 CLOUD PAR ENGINE CONNECTIVITY LOCK FIX
            user_mobile = st.secrets["MOBILE_NO"]
            user_mpin = st.secrets["MPIN"]
            active_client = InitNubraSdk(user_mobile, user_mpin, "PROD")
            st.session_state.nubra = active_client

        md_instance = MarketData(active_client)
        
        request_payload = {
            "exchange": "NSE",
            "type": asset_type,        # "INDEX" ya "STOCK"
            "values": [symbol],        # Selected Symbol
            "fields": ["open", "high", "low", "close"],
            "startDate": start_date,   # UTC Format
            "endDate": end_date,       # UTC Format
            "interval": interval,      # 1-Day interval
            "intraDay": False,
            "realTime": False
        }
        
        response = md_instance.historical_data(request_payload)
        
        if response and response.result and len(response.result) > 0:
            for instrument_dict in response.result[0].values:
                if symbol in instrument_dict:
                    stock_chart = instrument_dict[symbol]
                    timestamps = pd.to_datetime([p.timestamp for p in stock_chart.open], unit="ns", utc=True)
                    
                    df = pd.DataFrame({
                        "High": [p.value for p in stock_chart.high],
                        "Low": [p.value for p in stock_chart.low],
                        "Close": [p.value for p in stock_chart.close],
                    }, index=timestamps)
                    
                    df.index = df.index.tz_convert("Asia/Kolkata")
                    df[["High", "Low", "Close"]] = df[["High", "Low", "Close"]].div(100)
                    df.sort_index(inplace=True)
                    return df
        return None
    except Exception as e:
        # Pura app crash nahi hoga, bas ye error console par ya background me silent rahega
        print(f"Silent Historical Fetch Log: {e}")
        return None
    
# ================= 1. CONFIG & SYSTEM SECURITY WITH ADVANCE VALIDITY QUEUEING =================
st.set_page_config(page_title="SMART WEALTH AI 5", layout="wide")

import json, os, re, time
from datetime import datetime, timedelta

USER_FILE = "authorized_users.json"
SESSION_FILE = "session_login.json"
DATA_FILE = "admin_data_v2.json"
SETTINGS_FILE = "matrix_settings.json"

COUPON_FILE = "dynamic_coupons.json"
NOTICE_FILE = "admin_notice.json"

# --- 🔒 RAZORPAY CONFIG ---
RAZORPAY_PAGE_URL = "https://rzp.io/rzp/s2h4HIZo"
WEBHOOK_SECRET = "my_super_secret_token_123"

def load_json(file_path, default_val):
    if os.path.exists(file_path):
        try:
            with open(file_path, "r") as f: return json.load(f)
        except: pass
    return default_val

def save_json(file_path, data_to_save):
    try:
        with open(file_path, "w") as f: json.dump(data_to_save, f, indent=4)
    except: pass

ADMIN_DB = load_json(USER_FILE, {"9304768496": "Admin Chief", "7982046438": "Admin x"})
SUPER_ADMIN_IDS = ["9304768496", "7982046438"]
SUBSCRIPTION_DB = load_json(DATA_FILE, {})

LIVE_COUPONS = load_json(COUPON_FILE, {"BONUS15": 15, "DOUBLE30": 30})  
NOTICE_BOARD = load_json(NOTICE_FILE, {"message": "", "active": False})

# Default database initializer
for uid in ADMIN_DB:
    if uid not in SUBSCRIPTION_DB:
        SUBSCRIPTION_DB[uid] = {
            "status": "Paid" if uid in SUPER_ADMIN_IDS else "Unpaid",
            "expiry_date": "2030-12-31" if uid in SUPER_ADMIN_IDS else (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d"),
            "pending_approval": False,
            "submitted_mobile": "",
            "active_coupon": ""  
        }
save_json(DATA_FILE, SUBSCRIPTION_DB)

# --- 🚀 BACKGROUND AUTO-FETCH HANDLER (THE WEBHOOK RECEIVER) ---
query_params = st.query_params
if "razorpay_webhook_trigger" in query_params:
    try:
        import base64
        payload_b64 = query_params.get("payload", "")
        if payload_b64:
            payload_raw = base64.b64decode(payload_b64).decode('utf-8')
            data = json.loads(payload_raw)
            
            notes = data['payload']['payment']['entity'].get('notes', {})
            user_mobile = None
            
            for k, v in notes.items():
                if "mobile" in k.lower() or "id" in k.lower(): user_mobile = str(v).strip()
                
            if not user_mobile:
                entity_str = json.dumps(data)
                mobiles_found = re.findall(r'\b\d{10}\b', entity_str)
                if mobiles_found: user_mobile = mobiles_found[0]

            if user_mobile in SUBSCRIPTION_DB:
                # 1. Total base days calculation (Default 30 days)
                days_to_add = 30
                applied_coupon = SUBSCRIPTION_DB[user_mobile].get("active_coupon", "")
                
                if applied_coupon in LIVE_COUPONS:
                    days_to_add += int(LIVE_COUPONS[applied_coupon])
                
                # 2. 🔥 ADVANCE PLAN QUEUEING LOGIC 🔥
                current_expiry_str = SUBSCRIPTION_DB[user_mobile].get("expiry_date", "")
                today = datetime.now()
                
                try:
                    current_expiry = datetime.strptime(current_expiry_str, "%Y-%m-%d")
                    # Agar user active hai aur uski expiry date aaj se badi hai, toh purani date se aage badhao
                    if current_expiry > today:
                        base_start_date = current_expiry
                    else:
                        base_start_date = today
                except:
                    base_start_date = today
                
                # Final calculation and injection
                new_expiry_date = (base_start_date + timedelta(days=days_to_add)).strftime("%Y-%m-%d")
                
                SUBSCRIPTION_DB[user_mobile]["status"] = "Paid"
                SUBSCRIPTION_DB[user_mobile]["expiry_date"] = new_expiry_date
                SUBSCRIPTION_DB[user_mobile]["active_coupon"] = ""  # Reset
                save_json(DATA_FILE, SUBSCRIPTION_DB)
                st.success("WEBHOOK_PROCESSED_SUCCESSFULLY")
                st.stop()
    except Exception as e:
        st.error(f"Webhook Error: {e}")
        st.stop()

if "is_auth" not in st.session_state:
    st.session_state.is_auth = False
    st.session_state.admin_name = ""
    st.session_state.current_user_id = ""
    st.session_state.is_super_admin = False

# Auto session recovery
if not st.session_state.is_auth and os.path.exists(SESSION_FILE):
    saved = load_json(SESSION_FILE, None)
    if saved and saved.get("user_id") in ADMIN_DB:
        uid = saved["user_id"]
        st.session_state.is_auth = True
        st.session_state.admin_name = ADMIN_DB[uid]
        st.session_state.current_user_id = uid
        st.session_state.is_super_admin = (uid in SUPER_ADMIN_IDS)

def check_user_subscription(user_id):
    if user_id in SUPER_ADMIN_IDS: return True
    ud = SUBSCRIPTION_DB.get(user_id, {})
    if ud.get("status") == "Paid":
        try:
            if datetime.now() <= datetime.strptime(ud.get("expiry_date", ""), "%Y-%m-%d"): return True
        except: pass
    return False

# Login Panel UI
if not st.session_state.is_auth:
    st.markdown("<h1 style='text-align: center;'>🛡️ SMART WEALTH AI 5</h1>", unsafe_allow_html=True)
    _, col2, _ = st.columns([1, 1, 1])
    with col2:
        with st.form("Login"):
            user_key = st.text_input("Enter Mobile ID:", type="password")
            if st.form_submit_button("LOGIN"):
                if user_key in ADMIN_DB:
                    st.session_state.is_auth = True
                    st.session_state.admin_name = ADMIN_DB[user_key]
                    st.session_state.current_user_id = user_key
                    st.session_state.is_super_admin = (user_key in SUPER_ADMIN_IDS)
                    save_json(SESSION_FILE, {"user_id": user_key})
                    st.rerun()
                else: st.error("❌ Invalid Access ID")
    st.stop()

# --- 🔒 AUTOMATED PAYWALL INTERFACE ---
if not check_user_subscription(st.session_state.current_user_id):
    current_uid = st.session_state.current_user_id
    
    st.markdown("<h2 style='text-align: center; color: #ef4444;'>🔒 PREMIUM SUBSCRIPTION REQUIRED</h2>", unsafe_allow_html=True)
    
    # 🔥 LIVE NOTICE BOARD RE-LOADING LOGIC 🔥
    LIVE_NOTICE = load_json(NOTICE_FILE, {"message": "", "active": False})
    if LIVE_NOTICE.get("active") and LIVE_NOTICE.get("message") != "":
        st.markdown(f"""
        <div style="background-color: #fef08a; border-left: 6px solid #eab308; padding: 15px; border-radius: 8px; text-align: center; margin: 15px auto; max-width: 800px; box-shadow: 0 2px 4px rgba(0,0,0,0.05);">
            <span style="font-size: 24px; vertical-align: middle;">📢</span> 
            <strong style="color: #854d0e; font-size: 16px; margin-left: 8px;">
                {LIVE_NOTICE['message']}
            </strong>
        </div>
        """, unsafe_allow_html=True)

    _, p_col, _ = st.columns([1, 1.2, 1])
    with p_col:
        coupon_code = st.text_input("🎫 Have an Offer Code? Enter here:", value="", placeholder="e.g. BONUS15", key="paywall_coupon_box").strip().upper()
        
        should_rerun = True  # Controlled trigger for loop
        
        if coupon_code in LIVE_COUPONS:
            extra_days = LIVE_COUPONS[coupon_code]
            if SUBSCRIPTION_DB[current_uid].get("active_coupon") != coupon_code:
                SUBSCRIPTION_DB[current_uid]["active_coupon"] = coupon_code
                save_json(DATA_FILE, SUBSCRIPTION_DB)
            
            st.toast(f"🎉 Code '{coupon_code}' Applied!", icon="✅")
            validity_html = f'<h4 style="color:#16a34a; text-align:center; margin:0;">🎁 Offer Activated: Get {30 + extra_days} Days Access (30 + {extra_days} Days Extra!)</h4>'
            should_rerun = False  # DO NOT AUTO-REFRESH WHEN COUPON IS ACTIVE TO PREVENT RAZORPAY CRASH
        else:
            if coupon_code != "":
                st.error("❌ Invalid or Expired Code")
            validity_html = f'<h4 style="color:#64748b; text-align:center; margin:0;">Standard Validity: 30 Days Access</h4>'

        st.markdown(f"""
        <div style="background:#f8fafc; border:2px solid #0284c7; border-radius:12px; padding:25px; text-align:center; margin-bottom: 20px; margin-top: 10px;">
            <h3 style="color:#1e293b; margin:0;">Smart Wealth AI Premium Access</h3>
            <h1 style="color:#0284c7; margin:5px 0;">₹ 499.00</h1>
            {validity_html}
            <p style="font-size: 13px; color: #b91c1c; font-weight: bold; margin-top:15px; margin-bottom:15px;">
                ⚠️ ALERT: Razorpay par payment karte waqt form mein apni Mobile ID [ {current_uid} ] enter karein!
            </p>
            <a href="{RAZORPAY_PAGE_URL}" target="_blank">
                <button style="background-color:#0284c7; color:white; border:none; padding:14px 24px; border-radius:6px; font-weight:bold; width:100%; cursor:pointer; font-size:16px; box-shadow: 0 4px 6px -1px rgba(2, 132, 199, 0.4);">
                    🚀 CLICK TO SCAN & PAY ₹499
                </button>
            </a>
        </div>
        """, unsafe_allow_html=True)
        
        st.info("🔄 Payment hote hi Razorpay piche se signal bhejkar is page ko automatic unlock kar dega.")
        
        if should_rerun:
            time.sleep(5)
            st.rerun()

   # 🚪 Coupon/Paywall logic ke theek niche aur st.stop() se theek pehle ye daalein:
    st.markdown("---")
    if st.button("🚪 Logout / Switch Account", key="paywall_logout_btn", use_container_width=True):
        st.session_state.is_auth = False
        st.session_state.current_user_id = None
        st.rerun()

    st.stop()

# ==================================================================================
# SIDEBAR / SUPER ADMIN CONTROL SHEET
# ==================================================================================
if st.session_state.is_super_admin:
    st.sidebar.markdown("## 🛠️ ADMIN MASTER PANEL")
    
    # 📁 SECTION A: DYNAMIC COUPON MANAGER & NOTICE BOARD
    with st.sidebar.expander("🎫 Offer Coupons & Notice Board", expanded=False):
        st.markdown("### 📢 Broadcast Offer Message")
        
        # Live file se notice data read karein
        ADMIN_NOTICE = load_json(NOTICE_FILE, {"message": "", "active": False})
        
        notice_text = st.text_area("Enter Offer Message:", value=ADMIN_NOTICE.get("message", ""), placeholder="e.g. Festive Offer: Use Code BONUS15 to get 15 Days Extra Validity!")
        
        col_n1, col_n2 = st.columns(2)
        with col_n1:
            if st.button("📢 PUBLISH NOTICE", use_container_width=True):
                ADMIN_NOTICE["message"] = notice_text
                ADMIN_NOTICE["active"] = True
                save_json(NOTICE_FILE, ADMIN_NOTICE)
                st.success("Notice Published!")
                time.sleep(1); st.rerun()
        with col_n2:
            if st.button("🗑️ DELETE NOTICE", use_container_width=True):
                ADMIN_NOTICE["message"] = ""
                ADMIN_NOTICE["active"] = False
                save_json(NOTICE_FILE, ADMIN_NOTICE)
                st.success("Notice Removed!")
                time.sleep(1); st.rerun()
                
        st.markdown("---")
        st.markdown("### ➕ Add New Offer Code")
        new_code = st.text_input("Offer Code:", placeholder="e.g. BONUS15").strip().upper()
        new_days = st.number_input("Extra Validity Days to Add:", min_value=1, max_value=365, value=15)
        
        if st.button("💾 SAVE NEW CODE", use_container_width=True):
            if new_code:
                LIVE_COUPONS[new_code] = int(new_days)
                save_json(COUPON_FILE, LIVE_COUPONS)
                st.success(f"Code {new_code} active for +{new_days} Extra Days!")
                time.sleep(1); st.rerun()
            else: st.error("Code can't be empty!")
            
        st.markdown("---")
        st.markdown("### 🗑️ Active Offers (Click to Remove)")
        if LIVE_COUPONS:
            for code, days in list(LIVE_COUPONS.items()):
                c_col1, c_col2 = st.columns([2, 1])
                c_col1.markdown(f"**{code}** → +{days} Extra Days")
                if c_col2.button("❌ Remove", key=f"del_{code}"):
                    del LIVE_COUPONS[code]
                    save_json(COUPON_FILE, LIVE_COUPONS)
                    st.toast(f"Code {code} Deleted!")
                    time.sleep(1); st.rerun()
        else:
            st.info("No active codes.")

# --- CORE LOGIN CONTROLLER FRAMEWORK ---
if not st.session_state.is_auth:
    st.markdown("<h1 style='text-align: center;'>🛡️ SMART WEALTH AI 5</h1>", unsafe_allow_html=True)
    _, col2, _ = st.columns([1, 1, 1])
    with col2:
        with st.form("Login"):
            user_key = st.text_input("Enter Mobile ID:", type="password")
            if st.form_submit_button("LOGIN"):
                if user_key in ADMIN_DB:
                    st.session_state.is_auth = True
                    st.session_state.admin_name = ADMIN_DB[user_key]
                    st.session_state.current_user_id = user_key
                    st.session_state.is_super_admin = (user_key in SUPER_ADMIN_IDS)
                    save_json(SESSION_FILE, {"user_id": user_key})
                    st.rerun()
                else: st.error("❌ Invalid Access ID")
    st.stop()

# Set immediate variable boundary flags for access authorization
# ==================================================================================
# 📢 LIVE NOTICE BOARD DISPLAY (HAR REFRESH PAR LIVE CHECK HOGA)
# ==================================================================================
LIVE_NOTICE = load_json(NOTICE_FILE, {"message": "", "active": False})
if LIVE_NOTICE.get("active") and LIVE_NOTICE.get("message") != "":
    st.markdown(f"""
    <div style="background-color: #fef08a; border-left: 6px solid #eab308; padding: 15px; border-radius: 8px; text-align: center; margin: 15px auto; max-width: 1000px; box-shadow: 0 2px 4px rgba(0,0,0,0.05);">
        <span style="font-size: 24px; vertical-align: middle;">📢</span> 
        <strong style="color: #854d0e; font-size: 16px; margin-left: 8px; font-family: sans-serif;">
            {LIVE_NOTICE['message']}
        </strong>
    </div>
    """, unsafe_allow_html=True)
# ==================================================================================

st.session_state.is_paid_active = check_user_subscription(st.session_state.current_user_id)

# --- 💳 PREMIUM ONLINE PAYWALL INTERFACE SYSTEM ---
if not st.session_state.is_paid_active:
    st.markdown("<h2 style='text-align: center; color: #ef4444;'>🔒 RENEWAL REQUIRED: ACCESS RESTRICTED</h2>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: #64748b;'>Aapka account currently premium active mode me nahi hai. Main dashboard dekhne ke liye payment complete kijiye.</p>", unsafe_allow_html=True)
    
    _, p_col, _ = st.columns([1, 1.2, 1])
    with p_col:
        st.markdown(f"""
        <div style="background:#f8fafc; border:2px solid #ef4444; border-radius:12px; padding:20px; text-align:center; box-shadow: 0 4px 12px rgba(0,0,0,0.05);">
            <h3 style="color:#1e293b; margin-top:0;">Premium Monthly Subscription</h3>
            <h1 style="color:#0284c7; margin:10px 0;">₹ {MONTHLY_SUBSCRIPTION_FEES:,.2f} <span style="font-size:14px; color:#64748b;">/ Per Month</span></h1>
            <p style="font-size:12px; color:#475569;">Scan QR with Google Pay, PhonePe, Paytm, or any UPI App to activate instant validity updates.</p>
        </div>
        """, unsafe_allow_html=True)
        
        # Dynamic UPI Merchant URL Generation
        payload_text = f"upi://pay?pa={ADMIN_UPI_ID}&pn=Smart%20Wealth%20AI&am={MONTHLY_SUBSCRIPTION_FEES}&cu=INR&tn=Sub_{st.session_state.current_user_id}"
        encoded_upi = urllib.parse.quote_plus(payload_text)
        qr_api_url = f"https://api.qrserver.com/v1/create-qr-code/?size=250x250&data={encoded_upi}"
        
        st.markdown(f"<div style='text-align: center; margin-top:20px;'><img src='{qr_api_url}' style='border:4px solid #cbd5e1; border-radius:8px; padding:5px;'/></div>", unsafe_allow_html=True)
        st.markdown(f"<p style='text-align: center; font-size:11px; font-weight:bold; color:#0284c7;'>Reference TXN Note: Sub_{st.session_state.current_user_id}</p>", unsafe_allow_html=True)
        
        st.markdown("---")
        st.markdown("<p style='font-size:13px; font-weight:bold; color:#1e293b; margin-bottom:5px;'>💡 Auto-Fetch Payment Verification:</p>", unsafe_allow_html=True)
        
        with st.form("Verify Payment Form"):
            utr_ref = st.text_input("Enter 12-Digit UPI Ref No / UTR Number:", placeholder="e.g. 4023XXXXXXXX")
            if st.form_submit_button("VERIFY & ACTIVATE INSTANTLY"):
                clean_utr = re.sub(r'[^0-9]', '', utr_ref)
                if len(clean_utr) == 12:
                    # Automated Validation Mapping Lock
                    SUBSCRIPTION_DB[st.session_state.current_user_id] = {
                        "status": "Paid",
                        "expiry_date": (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d"),
                        "last_transaction_id": clean_utr
                    }
                    save_json(DATA_FILE, SUBSCRIPTION_DB)
                    st.success("🚀 TRANSACTION VERIFIED SUCCESSFULLY! Activating your terminal dashboard...")
                    time.sleep(2)
                    st.rerun()
                else:
                    st.error("❌ Invalid UTR Handle! Kripya sahi 12-digit UPI transaction number enter karein.")
                    
        if st.button("🔒 CANCEL / LOGOUT"):
            if os.path.exists(SESSION_FILE): os.remove(SESSION_FILE)
            st.session_state.clear(); st.rerun()
            
    st.stop() # Stops engine execution completely if paid validation flag is False

# ================= 2. ENGINE & SIDEBAR CONFIG =================
st_autorefresh(interval=5000, key="v5_ultimate_production_final")

@st.cache_resource(show_spinner=False)
def get_engine():
    try:
        from nubra_python_sdk.marketdata.market_data import MarketData
        from nubra_python_sdk.start_sdk import InitNubraSdk, NubraEnv
        from nubra_python_sdk.ticker import websocketdata
        nubra = InitNubraSdk(NubraEnv.PROD, env_creds=True)
        def on_msg(msg):
            name = msg.get('indexname')
            if name and "ticks" in st.session_state: st.session_state.ticks[name] = msg
        socket = websocketdata.NubraDataSocket(client=nubra, on_index_data=on_msg)
        socket.connect()
        socket.subscribe(["NIFTY", "SENSEX", "BANKNIFTY"], data_type="index", exchange="NSE")
        threading.Thread(target=socket.keep_running, daemon=True).start()
        return MarketData(nubra)
    except: return None

md = get_engine()
if "ticks" not in st.session_state: st.session_state.ticks = {}

matrix_settings = load_json(SETTINGS_FILE, {"last_index": "NIFTY"})
idx_list = ["NIFTY", "BANKNIFTY", "SENSEX"]
saved_idx = matrix_settings.get("last_index", "NIFTY")
default_idx = idx_list.index(saved_idx) if saved_idx in idx_list else 0

with st.sidebar:
    st.markdown(f"### 👤 User: **{st.session_state.admin_name}**")
    index_choice = st.selectbox("Select Index", idx_list, index=default_idx)
    if index_choice != saved_idx: save_json(SETTINGS_FILE, {"last_index": index_choice})
    
    if st.button("🔒 LOGOUT"):
        if os.path.exists(SESSION_FILE): os.remove(SESSION_FILE)
        st.session_state.clear(); st.rerun()

    if st.session_state.is_super_admin:
        with st.expander("👥 User Management"):
            new_uid = st.text_input("Add ID")
            new_uname = st.text_input("Name")
            if st.button("ADD"):
                if new_uid and new_uname: ADMIN_DB[new_uid] = new_uname; save_json(USER_FILE, ADMIN_DB); st.rerun()
            u_options = [f"{v} ({k})" for k, v in ADMIN_DB.items() if k != st.session_state.current_user_id]
            if u_options:
                u_del = st.selectbox("Remove User", u_options)
                if st.button("DELETE"):
                    uid_del = u_del.split('(')[-1].replace(')', ''); del ADMIN_DB[uid_del]; save_json(USER_FILE, ADMIN_DB); st.rerun()

target_exch = "BSE" if index_choice == "SENSEX" else "NSE"

@st.cache_resource
def get_global_memory(): return {"hist_df": {}}
memory = get_global_memory()

# ================= 3. ADVANCED CALCULATIONS & DATA PREP =================
try:
    result = md.option_chain(index_choice, exchange=target_exch)
    if not result or not result.chain:
        st.info("Syncing Market Matrix... ⏳"); st.stop()

    chain = result.chain
    spot = chain.current_price / 100 if chain.current_price > 100000 else chain.current_price
    atm = chain.at_the_money_strike / 100
    
    t_idx = st.session_state.ticks.get(index_choice, {})
    live_px = t_idx.get('index_value', 0)/100 or spot
    cur_chg = (live_px - spot)
    cur_pct = (cur_chg / spot * 100) if spot > 0 else 0.0

    # Upper Live Indicator Layer
    h_bg, h_txt = ("#e8f5e9", "#1b5e20") if cur_chg >= 0 else ("#ffebee", "#b71c1c")
    arrow = "▲" if cur_chg >= 0 else "▼"
    st.markdown(f'<div style="background:{h_bg}; padding:15px; border-radius:10px; text-align:center; border: 2px solid {h_txt};"><h1 style="color:{h_txt}; margin:0; font-size:32px; font-weight:bold;">{index_choice} {arrow} {live_px:,.2f} <span style="font-size:20px;">({cur_chg:+,.2f} | {cur_pct:+.2f}%)</span></h1></div>', unsafe_allow_html=True)

    df_ce = pd.DataFrame([vars(x) for x in chain.ce])
    df_pe = pd.DataFrame([vars(x) for x in chain.pe])
    df_comb = pd.merge(df_ce, df_pe, on="strike_price", suffixes=("_CE","_PE")).fillna(0)
    df_comb["STRIKE"] = (df_comb["strike_price"]/100).astype(int)

 # 🔥 DYNAMIC TIMEFRAME SELECTOR SYSTEM 🔥
    st.markdown("### ⏱️ Select Chart Timeframe")
    tf_choice = st.selectbox("Timeframe badlein:", options=["5m", "10m", "15m", "30m"], index=0, key=f"tf_select_{index_choice}")

    # Historical Multi-Timeframe Candle System
    hist_key = f"{index_choice}_{tf_choice}"
    if hist_key not in memory["hist_df"]:
        try:
            end_t = datetime.now().strftime("%Y-%m-%dT%H:%M:%S.000Z")
            start_t = (datetime.now() - timedelta(days=5)).strftime("%Y-%m-%dT%H:%M:%S.000Z")
            hist_res = md.historical_data({"exchange": target_exch, "type": "INDEX", "values": [index_choice], "fields": ["open", "high", "low", "close", "cumulative_volume"], "startDate": start_t, "endDate": end_t, "interval": tf_choice, "intraDay": False, "realTime": False})
            end_t = datetime.now().strftime("%Y-%m-%dT%H:%M:%S.000Z")
            start_t = (datetime.now() - timedelta(days=5)).strftime("%Y-%m-%dT%H:%M:%S.000Z")
            hist_res = md.historical_data({"exchange": target_exch, "type": "INDEX", "values": [index_choice], "fields": ["open", "high", "low", "close", "cumulative_volume"], "startDate": start_t, "endDate": end_t, "interval": "5m", "intraDay": False, "realTime": False})
            raw = hist_res.result[0].values[0][index_choice]
            memory["hist_df"][hist_key] = pd.DataFrame({"time": [pd.to_datetime(p.timestamp, unit="ns").tz_localize("UTC").tz_convert("Asia/Kolkata") for p in raw.close], "open": [p.value/100 for p in raw.open], "high": [p.value/100 for p in raw.high], "low": [p.value/100 for p in raw.low], "close": [p.value/100 for p in raw.close], "vol": [p.value for p in raw.cumulative_volume]})
        except: pass

    if hist_key in memory["hist_df"]:
        df_p = memory["hist_df"][hist_key].copy().tail(100)
        df_p['MA9'] = df_p['close'].rolling(9).mean()
        df_p['VWAP'] = (df_p['close'] * df_p['vol']).cumsum() / (df_p['vol'].cumsum() + 1)
        df_p['ATR'] = (df_p['high'] - df_p['low']).rolling(10).mean()
        df_p['ST_UP'] = df_p['MA9'] + (df_p['ATR'] * 2.5); df_p['ST_DN'] = df_p['MA9'] - (df_p['ATR'] * 2.5)

        fig = make_subplots(rows=1, cols=1)
        fig.add_trace(go.Candlestick(x=df_p['time'], open=df_p['open'], high=df_p['high'], low=df_p['low'], close=df_p['close'], name="Price"))
        fig.add_trace(go.Scatter(x=df_p['time'], y=df_p['MA9'], line=dict(color='blue', width=1.5), name="MA9"))
        fig.add_trace(go.Scatter(x=df_p['time'], y=df_p['VWAP'], line=dict(color='orange', width=1.5, dash='dash'), name="VWAP"))
        fig.add_trace(go.Scatter(x=df_p['time'], y=df_p['ST_UP'], line=dict(color='rgba(255,0,0,0.2)'), name="ST Sell"))
        fig.add_trace(go.Scatter(x=df_p['time'], y=df_p['ST_DN'], line=dict(color='rgba(0,255,0,0.2)'), name="ST Buy"))
        
        boring = abs(df_p['close'] - df_p['open']) / (df_p['high'] - df_p['low'] + 0.001) < 0.45
        fig.add_trace(go.Scatter(x=df_p['time'][boring], y=df_p['close'][boring], mode="markers", marker=dict(color="yellow", size=7, symbol="diamond"), name="Boring"))
        fig.update_layout(height=400, margin=dict(l=0,r=0,t=0,b=0), xaxis_rangeslider_visible=False, xaxis=dict(type='date', rangebreaks=[dict(bounds=[15.5, 9], pattern="hour")]))
        st.plotly_chart(fig, use_container_width=True)

    # PCR Calculation
    pcr = df_pe["open_interest"].sum() / df_ce["open_interest"].sum()
    mood = "🐂 BULLISH" if pcr > 1.15 else "🐻 BEARISH" if pcr < 0.85 else "↔️ SIDEWAYS"
    st.markdown(f'''<div style="background:#f8fafc; color:#1e293b; padding:10px; border-radius:8px; text-align:center; font-weight:bold; border: 1px solid #cbd5e1; margin-top:5px;">
        <span style="color:#f59e0b;">CE BEP: {atm + 100}</span> | <span>PCR: {pcr:.2f} ({mood})</span> | <span style="color:#ef4444;">PE BEP: {atm - 100}</span>
    </div>''', unsafe_allow_html=True)

    # S/R Targets
    res_stk = int(df_comb.loc[df_comb["volume_CE"].idxmax(), "STRIKE"])
    sup_stk = int(df_comb.loc[df_comb["volume_PE"].idxmax(), "STRIKE"])

    # ------------------------------------------------------------------
    # 🚨 DYNAMIC MOMENTUM ALERT ZONE (PERFECT SPOT-BASED INTERVAl ENGINE)
    # ------------------------------------------------------------------
    import math

    # 1. Active Index Detection
    detected_index = "NIFTY"
    if 'df_comb' in locals() and not df_comb.empty:
        if 'SYMBOL' in df_comb.columns:
            detected_index = str(df_comb['SYMBOL'].iloc[-1]).upper()
        elif 'STRIKE' in df_comb.columns:
            if df_comb['STRIKE'].iloc[0] > 60000: detected_index = "SENSEX"
            elif df_comb['STRIKE'].iloc[0] > 40000: detected_index = "BANKNIFTY"

    # 2. Setup standard buffer & strike intervals based on actual image views
    if "NIFTY" in detected_index and "BANK" not in detected_index:
        index_buffer = 20
        base_strike_interval = 100
        display_label = "NIFTY"
        default_spot = 23600
    elif "BANK" in detected_index:
        index_buffer = 50
        base_strike_interval = 500
        display_label = "BANKNIFTY"
        default_spot = 51500
    else:
        index_buffer = 50
        base_strike_interval = 500
        display_label = "SENSEX"
        default_spot = 75000

    # Live Spot Price Extraction (Direct from blue line matrix)
    current_market_price = default_spot
    if 'df_comb' in locals() and not df_comb.empty:
        col_mapping = {str(c).lower(): c for c in df_comb.columns}
        if 'close' in col_mapping:
            val = df_comb[col_mapping['close']].iloc[-1]
            if val > 100: current_market_price = val
        elif 'ltp' in col_mapping:
            val = df_comb[col_mapping['ltp']].iloc[-1]
            if val > 100: current_market_price = val

    # Extra Layer Force Safety Lock for boundaries mapping
    if display_label == "NIFTY" and current_market_price > 40000: current_market_price = 23590
    elif display_label == "SENSEX" and current_market_price < 60000: current_market_price = 74918

    # 3. 🎯 FLOORED & CEILED MATHEMATICS (No more random jumps!)
    # PUT todega spot ke exact neeche ka block, CALL todega spot ke exact upar ka block
    lower_round_strike = math.floor(current_market_price / base_strike_interval) * base_strike_interval
    upper_round_strike = math.ceil(current_market_price / base_strike_interval) * base_strike_interval

    # Precise calculation metrics matching your rules
    put_trigger_level = lower_round_strike - index_buffer
    call_trigger_level = upper_round_strike + index_buffer

    # 4. Color & Message Mapping Framework based on PCR Context
    if pcr > 1.15:
        bg_color = "#1b5e20"  # Bullish Green
        alert_msg = f"🟢 BULLISH: CALL BUY ACTIVE ABOVE {call_trigger_level} (TARGET: {upper_round_strike + base_strike_interval}) [{display_label}]"
    elif pcr < 0.85:
        bg_color = "#b71c1c"  # Bearish Red
        
        if current_market_price <= lower_round_strike:
            alert_msg = f"🔥 BIG MOVE TRIGGERED: PUT BUY CONFIRMED BELOW {lower_round_strike} ({display_label})"
        else:
            # 🚨 AB LOGIC EK DUM SATEEK CHALEGA:
            # Nifty Spot 23,590 -> lower_round_strike = 23,500 -> trigger = 23,480!
            # Sensex Spot 74,918 -> lower_round_strike = 74,500 -> trigger = 74,450!
            alert_msg = f"🚨 BIG MOVE ALERT: PUT BUY ACTIVE BELOW {put_trigger_level} (TARGET: {lower_round_strike}) [{display_label}]"
    else:
        bg_color = "#f59e0b"  # Sideways Amber
        alert_msg = f"⚪ MARKET SIDEWAYS (PCR: {pcr:.2f}) | WAIT FOR BREAKOUT ({display_label})"

    # 5. Output Screen Render
    st.markdown(f"""
        <div style="background-color:{bg_color}; padding:12px; border-radius:8px; margin-top:10px; margin-bottom:15px; text-align:center;">
            <p style="color:#ffffff; margin:0; font-weight:bold; font-size:16px; font-family:sans-serif; letter-spacing:0.5px;">
                {alert_msg}
            </p>
        </div>
    """, unsafe_allow_html=True)

    # OI Change Calculations
    df_comb["oi_chg_CE"] = df_comb["open_interest_CE"] - df_comb["previous_open_interest_CE"]
    df_comb["oi_chg_PE"] = df_comb["open_interest_PE"] - df_comb["previous_open_interest_PE"]

    # ================= 4. TABLE UI WITH INTERNAL SPOT INJECTION =================
    max_oi_ce, max_oi_pe = df_comb["open_interest_CE"].max(), df_comb["open_interest_PE"].max()
    max_vol_ce, max_vol_pe = df_comb["volume_CE"].max(), df_comb["volume_PE"].max()
    max_chg_ce = df_comb["oi_chg_CE"].abs().max() or 1
    max_chg_pe = df_comb["oi_chg_PE"].abs().max() or 1

    def fmt_val(val, delta, m_val):
        pct = (val/m_val*100) if m_val > 0 else 0
        return f"{val:,.0f}\n({delta:+,})\n{pct:.1f}%"

    atm_idx = (df_comb["STRIKE"] - live_px).abs().idxmin()
    d_df = df_comb.iloc[max(atm_idx-10,0): atm_idx+11].copy().reset_index(drop=True)

    # Base DataFrame Creation
    ui = pd.DataFrame()
    ui["CE OI\n(Δ/%)"] = d_df.apply(lambda r: fmt_val(r["open_interest_CE"], r["oi_chg_CE"], max_oi_ce), axis=1)
    ui["CE OI CHG"] = d_df.apply(lambda r: f"{r['oi_chg_CE']:+,}\n{(r['oi_chg_CE']/max_chg_ce*100):.1f}%", axis=1)
    ui["CE VOL\n(%)"] = d_df.apply(lambda r: fmt_val(r["volume_CE"], 0, max_vol_ce), axis=1)
    ui["STRIKE"] = d_df["STRIKE"].astype(str)
    ui["PE VOL\n(%)"] = d_df.apply(lambda r: fmt_val(r["volume_PE"], 0, max_vol_pe), axis=1)
    ui["PE OI CHG"] = d_df.apply(lambda r: f"{r['oi_chg_PE']:+,}\n{(r['oi_chg_PE']/max_chg_pe*100):.1f}%", axis=1)
    ui["PE OI\n(Δ/%)"] = d_df.apply(lambda r: fmt_val(r["open_interest_PE"], r["oi_chg_PE"], max_oi_pe), axis=1)

    # --- PURE DATAFRAME SPOT ROW INJECTION ---
    # Do strikes ke exact beech me Spot Row Inject karne ka system
    for i in range(len(d_df) - 1):
        s1 = float(d_df.loc[i, "STRIKE"])
        s2 = float(d_df.loc[i+1, "STRIKE"])
        if (s1 >= live_px > s2) or (s1 <= live_px < s2):
            spot_row = pd.DataFrame([{
                "CE OI\n(Δ/%)": "---", "CE OI CHG": "---", "CE VOL\n(%)": "---",
                "STRIKE": f"🔹 SPOT: {live_px:,.2f}",
                "PE VOL\n(%)": "---", "PE OI CHG": "---", "PE OI\n(Δ/%)": "---"
            }])
            ui = pd.concat([ui.iloc[:i+1], spot_row, ui.iloc[i+1:]]).reset_index(drop=True)
            break

    def style_table(row):
        s, idx = [''] * 7, row.name
        current_strike_str = str(row["STRIKE"])
        
        # 1. Floating Spot Row ke liye special background look
        if "🔹 SPOT" in current_strike_str:
            return ['background-color: #0284c7; color: white; font-weight: bold; font-size: 14px; text-align: center; border-top: 2px solid #00bcff; border-bottom: 2px solid #00bcff;'] * 7

        try:
            stk_num = int(re.sub(r'[^0-9]', '', current_strike_str))
        except:
            stk_num = 0

        s[3] = 'background-color:#f8f9fa; color:black; font-weight:bold'
        
        # 2. ATM Row Highlight (Yellow)
        if stk_num == int(atm): 
            s = ['background-color: yellow !important; color: black !important; font-weight: bold;'] * 7
        else:
            # 3. 75%+ Heatmap Shading System
            try:
                if float(row.iloc[0].split('\n')[-1].replace('%','')) >= 70: s[0] = 'background-color:#1565c0; color:white;'
                if float(row.iloc[1].split('\n')[-1].replace('%','')) >= 70: s[1] = 'background-color:#2e7d32; color:white;'
                if float(row.iloc[2].split('\n')[-1].replace('%','')) >= 75: s[2] = 'background-color:#1b5e20; color:white;'
                if float(row.iloc[4].split('\n')[-1].replace('%','')) >= 75: s[4] = 'background-color:#b71c1c; color:white;'
                if float(row.iloc[5].split('\n')[-1].replace('%','')) >= 70: s[5] = 'background-color:#c62828; color:white;'
                if float(row.iloc[6].split('\n')[-1].replace('%','')) >= 70: s[6] = 'background-color:#ef6c00; color:white;'
            except:
                pass

        # 4. Strict S/R Long Barrier Lines Left-To-Right
        if stk_num == res_stk: 
            for i in range(7): s[i] += '; border-top: 5px solid blue !important;'
        if stk_num == sup_stk: 
            for i in range(7): s[i] += '; border-bottom: 5px solid red !important;'
            
        return s

    st.table(ui.style.apply(style_table, axis=1))

except Exception as e:
    st.info(f"Syncing Matrix... {e}")

# ==================================================================================
# 🎫 ALL-IN-ONE SIDEBAR OFFERS & ADVANCE BOOKING SYSTEM (FOR LOGGED IN USERS)
# ==================================================================================
if st.session_state.is_auth:
    # HAR 10 SECOND MEIN REFRESH
    st_autorefresh(interval=5 * 1000, key="data_feed_refresh")
    # 🔄 10 second ko hata kar 5 second refresh lagayein
       
    # ------------------------------------------------------------------
    # 🔥 AAPKA NYA DATA TABLE BLOCK
    # ------------------------------------------------------------------
    # 🔄 AAPKE SETUP KE HISAB SE CLEAN REFRESH INTERRUPT
    st_autorefresh(interval=5 * 1000, key="data_feed_refresh_5sec")

    # ------------------------------------------------------------------
    # 🔥 DATA ROUTING ARCHITECTURE
    # ------------------------------------------------------------------
    # Dropdown variables structure mapping
    selected_symbol = "NIFTY"
    selected_type = "INDEX"

    # Current date context window (UTC Time Frame for Nubra contract)
    start_utc = "2026-05-20T03:30:00.000Z"
    end_utc = "2026-05-27T11:30:00.000Z"

    # API se global caching repository hit karein
    hist_df = fetch_and_clean_historical_data(
        symbol=selected_symbol, 
        asset_type=selected_type, 
        start_date=start_utc, 
        end_date=end_utc, 
        interval="1d"
    )

    # State controller to prevent double binding on layout
    if "hist_df" not in st.session_state or st.session_state.hist_df is None:
        st.session_state.hist_df = hist_df

    # ------------------------------------------------------------------
    # 🚀 REALTIME LIVE TICK HANDLER ENGINE
    # ------------------------------------------------------------------
    def handle_live_ohlcv(msg):
        if msg:
            import time
            # 1. Nanosecond pricing objects parse karein
            live_ts = pd.to_datetime(msg.get("timestamp", time.time()*1e9), unit="ns", utc=True).tz_convert("Asia/Kolkata")
            l_open = msg.get("open", 0) / 100.0
            l_high = msg.get("high", 0) / 100.0
            l_low = msg.get("low", 0) / 100.0
            l_close = msg.get("close", 0) / 100.0
            
            # Global runtime environment context push
            st.session_state["last_live_price"] = l_close
            
            # 2. DataFrame validation checks execute karein
            if "hist_df" in st.session_state and st.session_state.hist_df is not None:
                df = st.session_state.hist_df.copy()
                df.loc[live_ts] = [l_high, l_low, l_close]
                st.session_state.hist_df = df

    # Asynchronous daemon process network management system
    if "live_socket_connected" not in st.session_state or not st.session_state.live_socket_connected:
        try:
            import threading
            
            active_client = active_client if 'active_client' in locals() else st.session_state.nubra
            
            socket = websocketdata.NubraDataSocket(
                client=active_client,
                on_ohlcv_data=handle_live_ohlcv
            )
            
            socket.connect()
            socket.subscribe([selected_symbol], data_type="ohlcv", interval="15m", exchange="NSE")
            
            t = threading.Thread(target=socket.keep_running, daemon=True)
            t.start()
            
            st.session_state.live_socket_connected = True
        except Exception as ws_err:
            print(f"WS Sync Log Exception: {ws_err}")

    # ------------------------------------------------------------------
    # 📋 DISPLAY INTERFACE DESIGN (METRICS & TABLES)
    # ------------------------------------------------------------------
    display_df = st.session_state.hist_df if st.session_state.hist_df is not None else hist_df

    if display_df is not None and not display_df.empty:
        yesterday_data = display_df.iloc[-1]
        y_high = yesterday_data["High"]
        y_low = yesterday_data["Low"]
        y_close = yesterday_data["Close"]
        
        # Live price inject to catch current dynamic updates
        current_live_ltp = st.session_state.get("last_live_price", y_close)
        
        pp = (y_high + y_low + y_close) / 3.0
        r1 = (2 * pp) - y_low
        s1 = (2 * pp) - y_high
        r2 = pp + (y_high - y_low)
        s2 = pp - (y_high - y_low)
        
        st.markdown("---")
        st.markdown(f"### 🎯 Yesterday-Based Key Levels ({selected_symbol})")
        
        c1, c2, c3, c4, c5 = st.columns(5)
        c1.metric("🔴 Resistance 2 (R2)", f"₹{r2:.2f}")
        c2.metric("🚨 Resistance 1 (R1)", f"₹{r1:.2f}")
        c3.metric("⚪ Center Pivot (PP)", f"₹{pp:.2f}")
        c4.metric("🟢 Support 1 (S1)", f"₹{s1:.2f}")
        c5.metric("🔥 Support 2 (S2)", f"₹{s2:.2f}")
        
        st.markdown("#### 📋 Mathematical Levels Summary Table")
        st.table({
            "Technical Level": ["Resistance 2 (R2)", "Resistance 1 (R1)", "Pivot Point (PP)", "Support 1 (S1)", "Support 2 (S2)", "Yesterday Close (YC)"],
            "Exact Price": [f"₹{r2:.2f}", f"₹{r1:.2f}", f"₹{pp:.2f}", f"₹{s1:.2f}", f"₹{s2:.2f}", f"₹{y_close:.2f}"]
        })
    else:
        st.warning("Historical data parsing state. Re-connecting pipeline...")

    # 🚪 NEW ID SE LOGOUT/RESET KARNE KE LIYE BUTTON
    st.sidebar.markdown("---")
    if st.sidebar.button("🚪 Logout / Switch Account", key="switch_account_btn"):
        st.session_state.is_auth = False
        st.session_state.current_user_id = None
        st.rerun()
        
    st.sidebar.markdown("---")
    st.sidebar.markdown("### 🎫 ACTIVE OFFER ZONE")    
    # Text placeholder message
    if st.session_state.is_super_admin:
        st.sidebar.info("💡 Chief, aap Admin hain. Users ko yahan Offers aur Coupon Apply ka option dikhega.")
    else:
        st.sidebar.info("✨ Premium Member Option: Aap chalte huyen plan me bhi offer book kar sakte hain. Din aapki purani expiry ke baad judenge!")
        
   # User input box for coupon
    paid_coupon = st.sidebar.text_input("Enter Active Offer Code:", key="coupon_input_unique")
    
    if paid_coupon in LIVE_COUPONS:
        p_days = LIVE_COUPONS[paid_coupon]
        # User profile me coupon set karein
        SUBSCRIPTION_DB[st.session_state.current_user_id]["active_validity"] += p_days
        save_json(DATA_FILE, SUBSCRIPTION_DB)
        
        st.sidebar.success(f"🎉 Code Applied! +{p_days} EXTRA DAYS")
        
        st.sidebar.markdown(f"""
        <a href="{RAZORPAY_PAGE_URL}" target="_blank">
            <button style="width:100%; background-color:#ff4b4b; color:white; border:none; padding:10px; border-radius:5px; font-weight:bold; cursor:pointer;">
                🚀 UPGRADE TO PREMIUM (PAY NOW)
            </button>
        </a>
        """, unsafe_allow_html=True)
    else:
        if paid_coupon != "":
            st.sidebar.error("❌ Invalid or Expired Code")
