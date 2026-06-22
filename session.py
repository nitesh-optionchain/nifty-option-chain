# session.py
import os
import streamlit as st
from settings import SESSION_FILE, SUPER_ADMIN_IDS
from auth import load_json, ADMIN_DB

def init_session_state():
    if "is_auth" not in st.session_state:
        st.session_state.is_auth = False
        st.session_state.admin_name = ""
        st.session_state.current_user_id = ""
        st.session_state.is_super_admin = False
        st.session_state.is_paid_active = False

    # Session Auto-Recovery Logic
    if not st.session_state.is_auth and os.path.exists(SESSION_FILE):
        saved = load_json(SESSION_FILE, None)
        if saved and saved.get("user_id") in ADMIN_DB:
            uid = saved["user_id"]
            st.session_state.is_auth = True
            st.session_state.admin_name = ADMIN_DB[uid]
            st.session_state.current_user_id = uid
            st.session_state.is_super_admin = (uid in SUPER_ADMIN_IDS)
