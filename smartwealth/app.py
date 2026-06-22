# app.py
import streamlit as st
from streamlit_autorefresh import st_autorefresh

# 1. Import Settings & Configurations
from settings import REFRESH_INTERVAL_MS, SETTINGS_FILE
from auth import load_json

# 2. Import Core Systems & UI Layouts
from session import init_session_state
from login_ui import render_login_and_paywall
from engine import get_engine
from sidebar import render_sidebar
from live_tracker import get_global_memory, process_live_market_dashboard
from momentum_engine import run_momentum_tracker
from tables_ui import render_option_chain_table

# --- DYNAMIC REFRESH LOOP TRIGGER ---
st_autorefresh(interval=REFRESH_INTERVAL_MS, key="v5_ultimate_production_final")

# --- INITIALIZE SESSION STATE & AUTO-RECOVERY ---
init_session_state()

# --- TRIGGER ACCESS VALIDATOR & PAYWALL ---
render_login_and_paywall()

# ====================================================================
# 🔥 PAGE WRAPPERS & ROUTING LAYER (STREAMLIT MULTI-PAGE NAVIGATION)
# ====================================================================

def run_option_chain_page():
    # Master dashboard wrapper for original option chain grid
    md = get_engine()
    if "ticks" not in st.session_state: 
        st.session_state.ticks = {}

    matrix_settings = load_json(SETTINGS_FILE, {"last_index": "NIFTY"})
    idx_list = ["NIFTY", "BANKNIFTY", "SENSEX"]
    saved_idx = matrix_settings.get("last_index", "NIFTY")
    default_idx = idx_list.index(saved_idx) if saved_idx in idx_list else 0

    # Dynamic sidebar layout parameters mapping
    with st.sidebar:
        st.markdown("---")
        index_choice = render_sidebar(idx_list, default_idx, saved_idx)
        st.markdown("---")
        
    target_exch = "BSE" if index_choice == "SENSEX" else "NSE"

    memory = get_global_memory()
    df_comb, spot, atm, live_px = process_live_market_dashboard(md, index_choice, target_exch, memory)

    # Momentum analysis data processing
    d_df, max_oi_ce, max_oi_pe, max_vol_ce, max_vol_pe, max_chg_ce, max_chg_pe, res_stk, sup_stk, fmt_val = run_momentum_tracker(
        df_comb, index_choice, atm, live_px
    )

    # Main Option Chain Table Layout
    render_option_chain_table(
        d_df, max_oi_ce, max_oi_pe, max_chg_ce, max_chg_pe, max_vol_ce, max_vol_pe, live_px, atm, res_stk, sup_stk, fmt_val
    )

    # 🎯 BOTH LOWER TABLES REMOVED FOREVER (render_dual_zone_framework function call deleted)

# 🗺️ DYNAMIC NAVIGATION SYSTEM CONFIGURATION
page_1 = st.Page(run_option_chain_page, title="📊 Option Chain Data Terminal", icon="🎯", default=True)
page_2 = st.Page("pages/2_chart.py", title="📈 Advanced Live Chart", icon="📉")

# Mount components inside active loop routing network
pg = st.navigation({"Smart Wealth Navigation": [page_1, page_2]})

# Execute navigation router pipeline execution
pg.run()