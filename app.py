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
