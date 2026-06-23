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

   # app.py (PART 1 - Imports & Mobile CSS Injection)
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

# 📱 CUSTOM CSS FOR GLOBAL MOBILE TABLE OVERLAP FIX
st.markdown("""
    <style>
        /* Forces the container width to be fully responsive on smartphones */
        .block-container {
            max-width: 100% !important;
            padding-left: 0.5rem !important;
            padding-right: 0.5rem !important;
        }
        
        /* Targets the dataframe/table wrappers to activate smooth horizontal scrolling */
        .stDataFrame, div[data-testid="stTable"], div.element-container, .css-5rimss {
            width: 100% !important;
            overflow-x: auto !important;
            display: block !important;
        }
        
        /* Prevents multi-column text strings from smashing or breaking rows */
        table {
            width: 100% !important;
            min-width: 800px !important; /* Locks a minimum clean grid resolution on small viewports */
            border-collapse: collapse !important;
        }
        
        th, td {
            white-space: nowrap !important; /* Crucial: Prevents metrics text values from dropping or overlapping */
            padding: 8px 10px !important;
            font-size: 12px !important;
        }
        
        /* Webkit scrollbar optimizations for dynamic visibility */
        ::-webkit-scrollbar {
            height: 6px !important;
        }
        ::-webkit-scrollbar-thumb {
            background: #2563eb !important;
            border-radius: 4px !important;
        }
    </style>
""", unsafe_allow_html=True)

# --- DYNAMIC REFRESH LOOP TRIGGER ---
st_autorefresh(interval=REFRESH_INTERVAL_MS, key="v5_ultimate_production_final")

# --- INITIALIZE SESSION STATE & AUTO-RECOVERY ---
init_session_state()

# --- TRIGGER ACCESS VALIDATOR & PAYWALL ---
render_login_and_paywall()
