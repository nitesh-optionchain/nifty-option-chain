# sidebar.py
import os
import streamlit as st
from settings import SESSION_FILE, USER_FILE, SETTINGS_FILE
from auth import ADMIN_DB, save_json

def render_sidebar(idx_list, default_idx, saved_idx):
    with st.sidebar:
        st.markdown(f"### 👤 User: **{st.session_state.admin_name}**")
        index_choice = st.selectbox("Select Index", idx_list, index=default_idx)
        if index_choice != saved_idx: 
            save_json(SETTINGS_FILE, {"last_index": index_choice})
        
        if st.button("🔒 LOGOUT"):
            if os.path.exists(SESSION_FILE): os.remove(SESSION_FILE)
            st.session_state.clear()
            st.rerun()

        if st.session_state.is_super_admin:
            with st.expander("👥 User Management"):
                new_uid = st.text_input("Add ID")
                new_uname = st.text_input("Name")
                if st.button("ADD"):
                    if new_uid and new_uname: 
                        ADMIN_DB[new_uid] = new_uname
                        save_json(USER_FILE, ADMIN_DB)
                        st.rerun()
                
                u_options = [f"{v} ({k})" for k, v in ADMIN_DB.items() if k != st.session_state.current_user_id]
                if u_options:
                    u_del = st.selectbox("Remove User", u_options)
                    if st.button("DELETE"):
                        uid_del = u_del.split('(')[-1].replace(')', '')
                        del ADMIN_DB[uid_del]
                        save_json(USER_FILE, ADMIN_DB)
                        st.rerun()
                        
    return index_choice
