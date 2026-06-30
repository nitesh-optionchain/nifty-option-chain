# login_ui.py
import re
import os
import time
import urllib.parse
import streamlit as st
from datetime import datetime, timedelta
from settings import SESSION_FILE, DATA_FILE, ADMIN_UPI_ID, MONTHLY_SUBSCRIPTION_FEES, SUPER_ADMIN_IDS
from auth import ADMIN_DB, SUBSCRIPTION_DB, save_json, check_user_subscription_status

def render_login_and_paywall():
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
    st.session_state.is_paid_active = check_user_subscription_status(st.session_state.current_user_id)

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
                
        st.stop() # Stops engine execution completely if paid validation flag is False# login_ui.py
