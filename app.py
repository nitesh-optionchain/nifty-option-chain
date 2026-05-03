from __future__ import annotations
import json
import math
import os
import re
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
import streamlit.components.v1 as components
st.set_page_config(
    page_title="Smart Wealth AI 5",
    page_icon=None,
    layout="wide",
    initial_sidebar_state="collapsed",
)
INDEX_SYMBOLS = {
    "NIFTY": {"exchange": "NSE", "type": "INDEX"},
    "SENSEX": {"exchange": "BSE", "type": "INDEX"},
    "BANKNIFTY": {"exchange": "NSE", "type": "INDEX"},
}
TIMEFRAME_MINUTES = [5, 10, 15, 25]
PRICE_COLUMNS = ["open", "high", "low", "close"]
IST = "Asia/Kolkata"
SUPER_ADMIN_MOBILES = {"9304768496", "7631409004"}
USER_STORE = Path(__file__).with_name("dashboard_users.json")
@dataclass
class DataStatus:
    live: bool
    message: str
def clean_mobile(value: str) -> str:
    return re.sub(r"\D", "", value or "")[-10:]
def load_users() -> dict[str, Any]:
    default = {"viewers": [], "admins": []}
    if not USER_STORE.exists():
        return default
    try:
        loaded = json.loads(USER_STORE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default
    return {
        "viewers": sorted({clean_mobile(m) for m in loaded.get("viewers", []) if clean_mobile(m)}),
        "admins": sorted({clean_mobile(m) for m in loaded.get("admins", []) if clean_mobile(m)}),
    }
def save_users(users: dict[str, Any]) -> None:
    cleaned = {
        "viewers": sorted({clean_mobile(m) for m in users.get("viewers", []) if clean_mobile(m)}),
        "admins": sorted({clean_mobile(m) for m in users.get("admins", []) if clean_mobile(m)}),
    }
    USER_STORE.write_text(json.dumps(cleaned, indent=2), encoding="utf-8")
def mobile_role(mobile: str, users: dict[str, Any]) -> str | None:
    if mobile in SUPER_ADMIN_MOBILES:
        return "super_admin"
    if mobile in set(users.get("admins", [])):
        return "admin"
    if mobile in set(users.get("viewers", [])):
        return "viewer"
    return None
def require_login() -> dict[str, str] | None:
    users = load_users()
    saved_mobile = clean_mobile(st.session_state.get("auth_mobile", ""))
    saved_role = mobile_role(saved_mobile, users) if saved_mobile else None
    if saved_mobile and saved_role:
        return {"mobile": saved_mobile, "role": saved_role}
    st.title("Smart Wealth AI 5")
    st.info("Login is required before dashboard data is shown.")
    st.sidebar.title("Login")
    st.sidebar.info("Enter super admin or viewer mobile number on the main page.")
    left, center, right = st.columns([0.32, 0.36, 0.32])
    with center:
        st.subheader("Dashboard Login")
        st.caption("Enter registered mobile number to open the dashboard.")
        mobile = st.text_input("Mobile number", max_chars=14, placeholder="10 digit mobile")
        if st.button("Login", use_container_width=True):
            cleaned = clean_mobile(mobile)
            role = mobile_role(cleaned, users)
            if role:
                st.session_state["auth_mobile"] = cleaned
                st.rerun()
            else:
                st.error("This mobile number is not allowed. Ask admin to add viewer.")
        st.caption("Super admin: 9304768496, 7631409004")
    return None
def user_admin_panel(auth: dict[str, str]) -> None:
    users = load_users()
    st.sidebar.divider()
    st.sidebar.caption(f"Logged in: {auth['mobile']} ({auth['role']})")
    if st.sidebar.button("Logout", use_container_width=True):
        st.session_state.pop("auth_mobile", None)
        st.rerun()
    if auth["role"] not in {"admin", "super_admin"}:
        return
    with st.sidebar.expander("User Access", expanded=False):
        add_mobile = clean_mobile(st.text_input("Viewer mobile", key="add_viewer_mobile", placeholder="10 digit mobile"))
        if st.button("Add viewer", use_container_width=True):
            if len(add_mobile) != 10:
                st.warning("Enter valid 10 digit mobile number.")
            else:
                viewers = set(users.get("viewers", []))
                viewers.add(add_mobile)
                users["viewers"] = sorted(viewers)
                save_users(users)
                st.success(f"Viewer added: {add_mobile}")
                st.rerun()
        removable = sorted(set(users.get("viewers", [])) | set(users.get("admins", [])))
        if removable:
            remove_mobile = st.selectbox("Delete viewer/admin", removable)
            if st.button("Delete selected", use_container_width=True):
                users["viewers"] = [m for m in users.get("viewers", []) if m != remove_mobile]
                users["admins"] = [m for m in users.get("admins", []) if m != remove_mobile]
                save_users(users)
                st.success(f"Removed: {remove_mobile}")
                st.rerun()
        else:
            st.caption("No added viewers yet.")
def setup_page() -> None:
    st.markdown(
        """
        <style>
        .block-container { padding-top: 1.1rem; }
        .metric-tile {
            border: 1px solid #d8dee8;
            border-radius: 8px;
            padding: 12px 14px;
            background: #ffffff;
        }
        .metric-label {
            color: #52606d;
            font-size: 0.76rem;
            text-transform: uppercase;
            letter-spacing: 0;
        }
        .metric-value {
            color: #182230;
            font-size: 1.4rem;
            line-height: 1.45;
            font-weight: 700;
        }
        .metric-delta-pos { color: #0f7b4b; font-weight: 650; }
        .metric-delta-neg { color: #b42318; font-weight: 650; }
        .signal-long {
            border-left: 5px solid #0f7b4b;
            background: #eefaf4;
            border-radius: 8px;
            padding: 14px;
        }
        .signal-short {
            border-left: 5px solid #b42318;
            background: #fff2f0;
            border-radius: 8px;
            padding: 14px;
        }
        .signal-wait {
            border-left: 5px solid #b7791f;
            background: #fff8e6;
            border-radius: 8px;
            padding: 14px;
        }
        .small-muted { color: #667085; font-size: 0.86rem; }
        .login-shell {
            max-width: 420px;
            margin: 10vh auto 0 auto;
            border: 1px solid #d8dee8;
            border-radius: 8px;
            padding: 22px;
            background: #ffffff;
        }
        div[data-testid="stButton"] button {
            border-radius: 8px;
            border: 1px solid #98a2b3;
            background: #ffffff;
            color: #182230;
            font-weight: 650;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
@st.cache_resource(show_spinner=False)
def get_market_data_client(env_name: str, use_env_creds: bool) -> tuple[Any | None, DataStatus]:
    try:
        from nubra_python_sdk.marketdata.market_data import MarketData
        from nubra_python_sdk.start_sdk import InitNubraSdk, NubraEnv
    except Exception as exc:
        return None, DataStatus(False, f"Nubra SDK not available: {exc}")
    try:
        env = getattr(NubraEnv, env_name)
        nubra = InitNubraSdk(env, env_creds=use_env_creds)
        return MarketData(nubra), DataStatus(True, f"Connected to Nubra {env_name}")
    except Exception as exc:
        return None, DataStatus(False, f"Nubra login unavailable, using demo data: {exc}")
def normalize_price(value: Any) -> float:
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return np.nan
    try:
        price = float(value)
    except (TypeError, ValueError):
        return np.nan
    if abs(price) >= 100000:
        return price / 100.0
    return price
def point_series(points: Any, normalize: bool = True) -> pd.Series:
    if not points:
        return pd.Series(dtype="float64")
    timestamps = []
    values = []
    for point in points:
        timestamp = getattr(point, "timestamp", None)
        value = getattr(point, "value", None)
        if timestamp is None or value is None:
            continue
        timestamps.append(timestamp)
