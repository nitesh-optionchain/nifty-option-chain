from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st


st.set_page_config(page_title="Smart Wealth AI 5", layout="wide", initial_sidebar_state="expanded")
st.title("Smart Wealth AI 5")


INDEX_SYMBOLS = {
    "NIFTY": {"exchange": "NSE", "type": "INDEX"},
    "SENSEX": {"exchange": "BSE", "type": "INDEX"},
    "BANKNIFTY": {"exchange": "NSE", "type": "INDEX"},
}
SUPER_ADMINS = {"9304768496", "7631409004"}
IST = "Asia/Kolkata"


@dataclass
class DataStatus:
    live: bool
    message: str


def normalize_price(value: Any) -> float:
    if value is None:
        return np.nan
    try:
        price = float(value)
    except (TypeError, ValueError):
        return np.nan
    return price / 100 if abs(price) >= 100000 else price


def utc_iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")


@st.cache_resource(show_spinner=False)
def get_market_data(env_name: str, use_env_creds: bool) -> tuple[Any | None, DataStatus]:
    try:
        from nubra_python_sdk.marketdata.market_data import MarketData
        from nubra_python_sdk.start_sdk import InitNubraSdk, NubraEnv
    except Exception as exc:
        return None, DataStatus(False, f"Nubra SDK import failed: {exc}")

    try:
        nubra = InitNubraSdk(getattr(NubraEnv, env_name), env_creds=use_env_creds)
        return MarketData(nubra), DataStatus(True, f"Connected to Nubra {env_name}")
    except Exception as exc:
        return None, DataStatus(False, f"Nubra login/connect failed: {exc}")


def point_series(points: Any, price: bool = True) -> pd.Series:
    if not points:
        return pd.Series(dtype="float64")
    rows = []
    for point in points:
        ts = getattr(point, "timestamp", None)
        val = getattr(point, "value", None)
        if ts is None or val is None:
            continue
        rows.append((ts, normalize_price(val) if price else float(val)))
    if not rows:
        return pd.Series(dtype="float64")
    index = pd.to_datetime([x[0] for x in rows], unit="ns", utc=True).tz_convert(IST)
    return pd.Series([x[1] for x in rows], index=index, dtype="float64")


def response_to_frames(response: Any) -> dict[str, pd.DataFrame]:
    frames: dict[str, pd.DataFrame] = {}
    for group in getattr(response, "result", []) or []:
        for item in getattr(group, "values", []) or []:
            for symbol, chart in item.items():
                df = pd.DataFrame(
                    {
                        "open": point_series(getattr(chart, "open", None)),
                        "high": point_series(getattr(chart, "high", None)),
                        "low": point_series(getattr(chart, "low", None)),
                        "close": point_series(getattr(chart, "close", None)),
                        "cum_volume": point_series(getattr(chart, "cumulative_volume", None), price=False),
                    }
                ).dropna(subset=["open", "high", "low", "close"])
                if not df.empty:
                    df = df.sort_index()
                    df["volume"] = df["cum_volume"].diff().fillna(df["cum_volume"]).clip(lower=0)
                    frames[symbol] = df.drop(columns=["cum_volume"])
    return frames


def fetch_history(
    md: Any | None,
    symbol: str,
