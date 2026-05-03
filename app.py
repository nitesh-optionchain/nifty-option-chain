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
        values.append(normalize_price(value) if normalize else float(value))

    if not timestamps:
        return pd.Series(dtype="float64")

    index = pd.to_datetime(timestamps, unit="ns", utc=True).tz_convert(IST)
    return pd.Series(values, index=index, dtype="float64")


def response_to_frames(response: Any) -> dict[str, pd.DataFrame]:
    frames: dict[str, pd.DataFrame] = {}
    if not response or not getattr(response, "result", None):
        return frames

    for chart_group in response.result:
        for instrument_dict in getattr(chart_group, "values", []) or []:
            for symbol, stock_chart in instrument_dict.items():
                frame = pd.DataFrame(
                    {
                        "open": point_series(getattr(stock_chart, "open", None)),
                        "high": point_series(getattr(stock_chart, "high", None)),
                        "low": point_series(getattr(stock_chart, "low", None)),
                        "close": point_series(getattr(stock_chart, "close", None)),
                        "volume_cumulative": point_series(getattr(stock_chart, "cumulative_volume", None), normalize=False),
                    }
                ).dropna(subset=["open", "high", "low", "close"], how="any")

                if frame.empty:
                    continue

                frame = frame.sort_index()
                frame["volume"] = frame["volume_cumulative"].diff().fillna(frame["volume_cumulative"])
                frame["volume"] = frame["volume"].clip(lower=0)
                frames[symbol] = frame.drop(columns=["volume_cumulative"])
    return frames


def utc_iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")


def fetch_historical(
    market_data: Any | None,
    symbol: str,
    interval: str,
    days_back: int,
    exchange: str,
    instrument_type: str = "INDEX",
) -> pd.DataFrame:
    if market_data is None:
        return demo_candles(symbol, interval, days_back)

    end = datetime.now(timezone.utc)
    start = end - timedelta(days=days_back)
    try:
        response = market_data.historical_data(
            {
                "exchange": exchange,
                "type": instrument_type,
                "values": [symbol],
                "fields": ["open", "high", "low", "close", "cumulative_volume"],
                "startDate": utc_iso(start),
                "endDate": utc_iso(end),
                "interval": interval,
                "intraDay": False,
                "realTime": False,
            }
        )
        frames = response_to_frames(response)
        return frames.get(symbol, pd.DataFrame())
    except Exception as exc:
        st.toast(f"{symbol} history unavailable, using demo data.")
        st.session_state["last_data_error"] = str(exc)
        return demo_candles(symbol, interval, days_back)


def aggregate_minutes(frame: pd.DataFrame, minutes: int) -> pd.DataFrame:
    if frame.empty:
        return frame

    aggregated = (
        frame.resample(f"{minutes}min", origin="start_day")
        .agg(
            {
                "open": "first",
                "high": "max",
                "low": "min",
                "close": "last",
                "volume": "sum",
            }
        )
        .dropna(subset=["open", "high", "low", "close"])
    )
    return aggregated


def fetch_intraday_candles(market_data: Any | None, symbol: str, minutes: int, exchange: str) -> pd.DataFrame:
    if minutes in (5, 15):
        return fetch_historical(market_data, symbol, f"{minutes}m", 7, exchange)

    base = fetch_historical(market_data, symbol, "5m", 7, exchange)
    return aggregate_minutes(base, minutes)


def fetch_current_prices(market_data: Any | None) -> dict[str, dict[str, float]]:
    if market_data is None:
        return demo_prices()

    prices: dict[str, dict[str, float]] = {}
    for symbol, meta in INDEX_SYMBOLS.items():
        try:
            snapshot = market_data.current_price(symbol, exchange=meta["exchange"])
            price = normalize_price(getattr(snapshot, "price", None))
            prev_close = normalize_price(getattr(snapshot, "prev_close", None))
            difference = price - prev_close if not np.isnan(price) and not np.isnan(prev_close) else np.nan
            change_pct = difference / prev_close * 100 if not np.isnan(difference) and prev_close else np.nan
            if np.isnan(change_pct):
                change_pct = float(getattr(snapshot, "change", 0) or 0)
            prices[symbol] = {
                "price": price,
                "prev_close": prev_close,
                "difference": difference,
                "change": change_pct,
            }
        except Exception:
            prices[symbol] = demo_prices()[symbol]
    return prices


def fetch_option_chain(market_data: Any | None, symbol: str, exchange: str, expiry: str | None = None) -> pd.DataFrame:
    if market_data is None:
        return demo_option_chain(symbol)

    try:
        if expiry:
            response = market_data.option_chain(symbol, expiry=expiry, exchange=exchange)
        else:
            response = market_data.option_chain(symbol, exchange=exchange)
        chain = response.chain
        return option_chain_to_frame(chain)
    except Exception as exc:
        st.session_state["last_option_error"] = str(exc)
        return demo_option_chain(symbol)


def option_chain_to_frame(chain: Any) -> pd.DataFrame:
    calls = {normalize_price(getattr(opt, "strike_price", np.nan)): opt for opt in getattr(chain, "ce", []) or []}
    puts = {normalize_price(getattr(opt, "strike_price", np.nan)): opt for opt in getattr(chain, "pe", []) or []}
    strikes = sorted(set(calls) | set(puts))
    underlying = normalize_price(getattr(chain, "current_price", None))
    atm = normalize_price(getattr(chain, "at_the_money_strike", None))
    rows = []

    for strike in strikes:
        ce = calls.get(strike)
        pe = puts.get(strike)
        ce_ltp = normalize_price(getattr(ce, "last_traded_price", None)) if ce else np.nan
        pe_ltp = normalize_price(getattr(pe, "last_traded_price", None)) if pe else np.nan
        ce_volume = float(getattr(ce, "volume", 0) or 0) if ce else 0
        pe_volume = float(getattr(pe, "volume", 0) or 0) if pe else 0
        ce_oi = float(getattr(ce, "open_interest", 0) or 0) if ce else 0
        pe_oi = float(getattr(pe, "open_interest", 0) or 0) if pe else 0
        ce_oi_chg = float(getattr(ce, "open_interest_change", 0) or 0) if ce else 0
        pe_oi_chg = float(getattr(pe, "open_interest_change", 0) or 0) if pe else 0

        rows.append(
            {
                "strike": strike,
                "distance": abs(strike - underlying) if not np.isnan(underlying) else np.nan,
                "ce_ltp": ce_ltp,
                "ce_be": strike + ce_ltp if not np.isnan(ce_ltp) else np.nan,
                "ce_iv": float(getattr(ce, "iv", np.nan) or np.nan) if ce else np.nan,
                "ce_delta": float(getattr(ce, "delta", np.nan) or np.nan) if ce else np.nan,
                "ce_volume": ce_volume,
                "ce_oi": ce_oi,
                "ce_oi_chg": ce_oi_chg,
                "pe_ltp": pe_ltp,
                "pe_be": strike - pe_ltp if not np.isnan(pe_ltp) else np.nan,
                "pe_iv": float(getattr(pe, "iv", np.nan) or np.nan) if pe else np.nan,
                "pe_delta": float(getattr(pe, "delta", np.nan) or np.nan) if pe else np.nan,
                "pe_volume": pe_volume,
                "pe_oi": pe_oi,
                "pe_oi_chg": pe_oi_chg,
                "underlying": underlying,
                "atm": atm,
            }
        )

    frame = pd.DataFrame(rows)
    if frame.empty:
        return frame

    frame = frame.sort_values("distance").head(18).sort_values("strike")
    for side in ("ce", "pe"):
        max_volume = frame[f"{side}_volume"].max()
        max_oi = frame[f"{side}_oi"].max()
        max_oi_chg = frame[f"{side}_oi_chg"].abs().max()
        frame[f"{side}_volume_pct"] = np.where(max_volume > 0, frame[f"{side}_volume"] / max_volume * 100, 0)
        frame[f"{side}_oi_pct"] = np.where(max_oi > 0, frame[f"{side}_oi"] / max_oi * 100, 0)
        frame[f"{side}_oi_chg_pct"] = np.where(
            max_oi_chg > 0,
            frame[f"{side}_oi_chg"].abs() / max_oi_chg * 100,
            0,
        )
        frame[f"{side}_previous_oi"] = frame[f"{side}_oi"] - frame[f"{side}_oi_chg"]
        frame[f"{side}_oi_display"] = frame.apply(
            lambda row, prefix=side: f"{row[f'{prefix}_oi']:,.0f} ({row[f'{prefix}_oi_pct']:.1f}%)",
            axis=1,
        )
        frame[f"{side}_oi_chg_display"] = frame.apply(
            lambda row, prefix=side: (
                f"{row[f'{prefix}_oi_chg']:+,.0f} / Prev {row[f'{prefix}_previous_oi']:,.0f}"
                f" ({row[f'{prefix}_oi_chg_pct']:.1f}%)"
            ),
            axis=1,
        )
        frame[f"{side}_volume_display"] = frame.apply(
            lambda row, prefix=side: f"{row[f'{prefix}_volume']:,.0f} ({row[f'{prefix}_volume_pct']:.1f}%)",
            axis=1,
        )
    for side in ("ce", "pe"):
        median_volume = frame[f"{side}_volume"].replace(0, np.nan).median()
        median_volume = 1 if np.isnan(median_volume) or median_volume <= 0 else median_volume
        frame[f"{side}_false_volume"] = np.where(
            (frame[f"{side}_volume"] > median_volume * 2.2)
            & (frame[f"{side}_oi_chg"].abs() < frame[f"{side}_oi"].abs() * 0.015),
            "Watch",
            "Clear",
        )
    return frame


def add_indicators(frame: pd.DataFrame) -> pd.DataFrame:
    if frame.empty:
        return frame

    df = frame.copy()
    df["rsi"] = rsi(df["close"], 14)
    df["atr"] = atr(df, 10)
    st_line, st_dir = supertrend(df, period=10, multiplier=3.0)
    df["supertrend"] = st_line
    df["trend"] = st_dir
    df["body_pct"] = (df["close"] - df["open"]).abs() / (df["high"] - df["low"]).replace(0, np.nan)
    df["range_vs_atr"] = (df["high"] - df["low"]) / df["atr"].replace(0, np.nan)
    df["boring_candle"] = (df["body_pct"] <= 0.22) & (df["range_vs_atr"] <= 0.75)
    df["volume_avg"] = df["volume"].rolling(20, min_periods=5).mean()
    df["volume_spike"] = df["volume"] > df["volume_avg"] * 1.8
    return df


def rsi(series: pd.Series, period: int = 14) -> pd.Series:
    delta = series.diff()
    gain = delta.clip(lower=0).ewm(alpha=1 / period, adjust=False).mean()
    loss = -delta.clip(upper=0).ewm(alpha=1 / period, adjust=False).mean()
    rs = gain / loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))


def atr(frame: pd.DataFrame, period: int = 14) -> pd.Series:
    high_low = frame["high"] - frame["low"]
    high_close = (frame["high"] - frame["close"].shift()).abs()
    low_close = (frame["low"] - frame["close"].shift()).abs()
    true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    return true_range.ewm(alpha=1 / period, adjust=False).mean()


def supertrend(frame: pd.DataFrame, period: int = 10, multiplier: float = 3.0) -> tuple[pd.Series, pd.Series]:
    df = frame.copy()
    average_true_range = atr(df, period)
    hl2 = (df["high"] + df["low"]) / 2
    upper_band = hl2 + multiplier * average_true_range
    lower_band = hl2 - multiplier * average_true_range
    final_upper = upper_band.copy()
    final_lower = lower_band.copy()
    trend = pd.Series(1, index=df.index, dtype="int64")
    line = pd.Series(index=df.index, dtype="float64")

    for i in range(1, len(df)):
        current = df.index[i]
        previous = df.index[i - 1]
        if upper_band.loc[current] < final_upper.loc[previous] or df["close"].loc[previous] > final_upper.loc[previous]:
            final_upper.loc[current] = upper_band.loc[current]
        else:
            final_upper.loc[current] = final_upper.loc[previous]

        if lower_band.loc[current] > final_lower.loc[previous] or df["close"].loc[previous] < final_lower.loc[previous]:
            final_lower.loc[current] = lower_band.loc[current]
        else:
            final_lower.loc[current] = final_lower.loc[previous]

        if trend.loc[previous] == -1 and df["close"].loc[current] > final_upper.loc[current]:
            trend.loc[current] = 1
        elif trend.loc[previous] == 1 and df["close"].loc[current] < final_lower.loc[current]:
            trend.loc[current] = -1
        else:
            trend.loc[current] = trend.loc[previous]

        line.loc[current] = final_lower.loc[current] if trend.loc[current] == 1 else final_upper.loc[current]

    line.iloc[0] = lower_band.iloc[0]
    return line, trend


def support_resistance(frame: pd.DataFrame) -> dict[str, float]:
    daily = frame.dropna(subset=["open", "high", "low", "close"])
    if daily.empty:
        return {}

    today = pd.Timestamp.now(tz=IST).date()
    complete_days = daily[daily.index.date < today]
    previous = complete_days.iloc[-1] if not complete_days.empty else daily.iloc[-1]
    pivot = (previous["high"] + previous["low"] + previous["close"]) / 3
    return {
        "prev_open": previous["open"],
        "prev_high": previous["high"],
        "prev_low": previous["low"],
        "prev_close": previous["close"],
        "pivot": pivot,
        "r1": (2 * pivot) - previous["low"],
        "s1": (2 * pivot) - previous["high"],
        "r2": pivot + (previous["high"] - previous["low"]),
        "s2": pivot - (previous["high"] - previous["low"]),
    }


def rsi_timeframes(market_data: Any | None, symbol: str, exchange: str) -> pd.DataFrame:
    rows = []
    for label, interval, days in [
        ("Daily", "1d", 220),
        ("Weekly", "1w", 900),
        ("Monthly", "1mt", 2200),
    ]:
        frame = fetch_historical(market_data, symbol, interval, days, exchange)
        value = rsi(frame["close"], 14).dropna().iloc[-1] if len(frame) > 20 else np.nan
        rows.append({"timeframe": label, "rsi": value, "bias": rsi_bias(value)})
    return pd.DataFrame(rows)


def rsi_bias(value: float) -> str:
    if np.isnan(value):
        return "NA"
    if value >= 60:
        return "Bullish"
    if value <= 40:
        return "Bearish"
    return "Neutral"


def scalping_signal(df: pd.DataFrame, levels: dict[str, float]) -> dict[str, str]:
    if df.empty:
        return {"class": "signal-wait", "title": "WAIT", "detail": "No candle data available."}

    last = df.iloc[-1]
    near_support = bool(levels) and last["close"] <= levels.get("s1", -np.inf) * 1.002
    near_resistance = bool(levels) and last["close"] >= levels.get("r1", np.inf) * 0.998

    if last["trend"] == 1 and last["rsi"] >= 54 and not bool(last["boring_candle"]) and not near_resistance:
        return {
            "class": "signal-long",
            "title": "LONG SCALP",
            "detail": "Supertrend is positive, RSI has strength, and price is not pressing into R1.",
        }
    if last["trend"] == -1 and last["rsi"] <= 46 and not bool(last["boring_candle"]) and not near_support:
        return {
            "class": "signal-short",
            "title": "SHORT SCALP",
            "detail": "Supertrend is negative, RSI is weak, and price is not sitting on S1.",
        }
    if bool(last["boring_candle"]):
        return {
            "class": "signal-wait",
            "title": "BORING CANDLE",
            "detail": "Latest candle has a small body and compressed range; wait for breakout confirmation.",
        }
    return {
        "class": "signal-wait",
        "title": "WAIT",
        "detail": "Signal is mixed near support/resistance or RSI is neutral.",
    }


def candle_chart(
    frame: pd.DataFrame,
    symbol: str,
    levels: dict[str, float] | None = None,
    option_table: pd.DataFrame | None = None,
    show_boring: bool = True,
    show_volume: bool = True,
) -> go.Figure:
    fig = go.Figure()
    if frame.empty or not set(PRICE_COLUMNS).issubset(frame.columns):
        fig.update_layout(
            height=470,
            template="plotly_white",
            annotations=[
                dict(
                    text="No candle data available",
                    x=0.5,
                    y=0.5,
                    xref="paper",
                    yref="paper",
                    showarrow=False,
                )
            ],
        )
        return fig
    fig.add_trace(
        go.Candlestick(
            x=frame.index,
            open=frame["open"],
            high=frame["high"],
            low=frame["low"],
            close=frame["close"],
            name=symbol,
            increasing_line_color="#0f7b4b",
            decreasing_line_color="#b42318",
        )
    )
    if "supertrend" in frame:
        fig.add_trace(
            go.Scatter(
                x=frame.index,
                y=frame["supertrend"],
                mode="lines",
                name="Supertrend",
                line=dict(color="#4b5563", width=1.6),
            )
        )
    if levels:
        for name, price, color in [
            ("R2", levels.get("r2"), "#5f0f18"),
            ("R1", levels.get("r1"), "#7f1d1d"),
            ("S1", levels.get("s1"), "#123c9c"),
            ("S2", levels.get("s2"), "#082f70"),
        ]:
            if price is not None and not np.isnan(price):
                fig.add_hline(
                    y=price,
                    line_width=6,
                    line_color=color,
                    annotation_text=name,
                    annotation_position="right",
                )
    if option_table is not None and not option_table.empty:
        table = prepare_option_display(option_table)
        atm_rows = table[table["is_atm"]]
        atm_row = atm_rows.iloc[0] if not atm_rows.empty else table.sort_values("distance").iloc[0]
        if not np.isnan(atm_row["ce_be"]):
            fig.add_hline(
                y=atm_row["ce_be"],
                line_width=5,
                line_color="#0b7a3b",
                annotation_text="CE BE",
                annotation_position="left",
            )
        if not np.isnan(atm_row["pe_be"]):
            fig.add_hline(
                y=atm_row["pe_be"],
                line_width=5,
                line_color="#c026d3",
                annotation_text="PE BE",
                annotation_position="left",
            )
    if show_boring and "boring_candle" in frame:
        boring = frame[frame["boring_candle"].fillna(False)]
        if not boring.empty:
            fig.add_trace(
                go.Scatter(
                    x=boring.index,
                    y=boring["high"],
                    mode="markers",
                    name="Boring Candle",
                    marker=dict(symbol="circle", size=8, color="#7c3aed"),
                )
            )
    if show_volume and "volume_spike" in frame:
        spikes = frame[frame["volume_spike"].fillna(False)]
        if not spikes.empty:
            fig.add_trace(
                go.Scatter(
                    x=spikes.index,
                    y=spikes["low"],
                    mode="markers",
                    name="Volume Spike",
                    marker=dict(symbol="triangle-up", size=10, color="#f97316"),
                )
            )
    fig.update_layout(
        height=470,
        margin=dict(l=8, r=8, t=28, b=8),
        xaxis_rangeslider_visible=False,
        template="plotly_white",
        legend_orientation="h",
        legend_y=1.04,
    )
    return fig


def format_oi_change_display(row: pd.Series, prefix: str) -> str:
    previous_change = row.get(f"{prefix}_prev_oi_chg", np.nan)
    previous_text = "-" if pd.isna(previous_change) else f"{previous_change:+,.0f}"
    return f"{row[f'{prefix}_oi_chg']:+,.0f} / Prev Chg {previous_text} ({row[f'{prefix}_oi_chg_pct']:.1f}%)"


def prepare_option_display(frame: pd.DataFrame) -> pd.DataFrame:
    table = frame.copy()
    for side in ("ce", "pe"):
        max_volume = table[f"{side}_volume"].max()
        max_oi = table[f"{side}_oi"].max()
        max_oi_chg = table[f"{side}_oi_chg"].abs().max()
        table[f"{side}_volume_pct"] = np.where(max_volume > 0, table[f"{side}_volume"] / max_volume * 100, 0)
        table[f"{side}_oi_pct"] = np.where(max_oi > 0, table[f"{side}_oi"] / max_oi * 100, 0)
        table[f"{side}_oi_chg_pct"] = np.where(
            max_oi_chg > 0,
            table[f"{side}_oi_chg"].abs() / max_oi_chg * 100,
            0,
        )
        table[f"{side}_previous_oi"] = table[f"{side}_oi"] - table[f"{side}_oi_chg"]
        if f"{side}_prev_oi_chg" not in table:
            table[f"{side}_prev_oi_chg"] = np.nan
        table[f"{side}_volume_display"] = table.apply(
            lambda row, prefix=side: f"{row[f'{prefix}_volume']:,.0f} ({row[f'{prefix}_volume_pct']:.1f}%)",
            axis=1,
        )
        table[f"{side}_oi_display"] = table.apply(
            lambda row, prefix=side: f"{row[f'{prefix}_oi']:,.0f} ({row[f'{prefix}_oi_pct']:.1f}%)",
            axis=1,
        )
        table[f"{side}_oi_chg_display"] = table.apply(
            lambda row, prefix=side: format_oi_change_display(row, prefix),
            axis=1,
        )
    if "atm" not in table or table["atm"].isna().all():
        nearest_atm = table.sort_values("distance").iloc[0]["strike"]
        table["atm"] = nearest_atm
    table["atm_strike"] = table["strike"]
    table["is_atm"] = table["strike"].round(2) == table["atm"].round(2)
    return table


def style_option_table(frame: pd.DataFrame) -> Any:
    table = prepare_option_display(frame)
    visible_cols = [
        "ce_oi_chg_display",
        "ce_oi_display",
        "ce_volume_display",
        "ce_be",
        "ce_false_volume",
        "atm_strike",
        "pe_false_volume",
        "pe_be",
        "pe_volume_display",
        "pe_oi_display",
        "pe_oi_chg_display",
    ]
    table = table[
        visible_cols
        + [
            "is_atm",
            "ce_volume",
            "pe_volume",
            "ce_volume_pct",
            "pe_volume_pct",
            "ce_oi",
            "pe_oi",
            "ce_oi_chg",
            "pe_oi_chg",
            "ce_oi_chg_pct",
            "pe_oi_chg_pct",
            "ce_prev_oi_chg",
            "pe_prev_oi_chg",
        ]
    ].copy()
    headers = {
        "ce_oi_chg_display": "CE OI Chg (%)",
        "ce_oi_display": "CE Current OI (%)",
        "ce_volume_display": "CE Volume (%)",
        "ce_be": "CE Break Even",
        "ce_false_volume": "CE Fake Vol",
        "atm_strike": "ATM Strike",
        "pe_false_volume": "PE Fake Vol",
        "pe_be": "PE Break Even",
        "pe_volume_display": "PE Volume (%)",
        "pe_oi_display": "PE Current OI (%)",
        "pe_oi_chg_display": "PE OI Chg (%)",
    }
    reverse_headers = {label: key for key, label in headers.items()}

    max_ce_volume = table["ce_volume"].max()
    max_pe_volume = table["pe_volume"].max()
    max_ce_oi = table["ce_oi"].max()
    max_pe_oi = table["pe_oi"].max()
    max_ce_oi_chg = table["ce_oi_chg"].abs().max()
    max_pe_oi_chg = table["pe_oi_chg"].abs().max()

    def row_style(row: pd.Series) -> list[str]:
        source = table.loc[row.name]
        styles = []
        for label in row.index:
            col = reverse_headers[label]
            style = ""
            if col == "atm_strike":
                style = "background-color: #edf0f5; font-weight: 700"
                if bool(source["is_atm"]):
                    style = "background-color: #f4b400; color: #1f2937; font-weight: 800"
            elif col == "ce_volume_display" and source["ce_volume"] == max_ce_volume:
                style = "background-color: #006b3c; color: white; font-weight: 800"
            elif col == "pe_volume_display" and source["pe_volume"] == max_pe_volume:
                style = "background-color: #9f1239; color: white; font-weight: 800"
            elif col == "ce_volume_display" and source["ce_volume_pct"] >= 75:
                style = "background-color: #bbf7d0; color: #064e3b; font-weight: 700"
            elif col == "pe_volume_display" and source["pe_volume_pct"] >= 75:
                style = "background-color: #fecdd3; color: #881337; font-weight: 700"
            elif col == "ce_oi_display" and source["ce_oi"] == max_ce_oi:
                style = "background-color: #f97316; color: white; font-weight: 800"
            elif col == "pe_oi_display" and source["pe_oi"] == max_pe_oi:
                style = "background-color: #f97316; color: white; font-weight: 800"
            elif col == "ce_oi_chg_display" and abs(source["ce_oi_chg"]) == max_ce_oi_chg:
                style = "background-color: #f97316; color: white; font-weight: 800"
            elif col == "pe_oi_chg_display" and abs(source["pe_oi_chg"]) == max_pe_oi_chg:
                style = "background-color: #f97316; color: white; font-weight: 800"
            elif col == "ce_oi_chg_display" and source["ce_oi_chg_pct"] >= 75:
                style = "background-color: #fed7aa; color: #7c2d12; font-weight: 800"
            elif col == "pe_oi_chg_display" and source["pe_oi_chg_pct"] >= 75:
                style = "background-color: #fed7aa; color: #7c2d12; font-weight: 800"
            elif col == "ce_be":
                style = "background-color: #dff7ea; color: #064e3b; font-weight: 700"
            elif col == "pe_be":
                style = "background-color: #ffe4e6; color: #881337; font-weight: 700"
            elif "false_volume" in col:
                style = "background-color: #f3e8ff; color: #4c1d95"
                if source[col] == "Watch":
                    style = "background-color: #eadcff; color: #4c1d95; font-weight: 800"
            styles.append(style)
        return styles

    display = table[visible_cols].rename(columns=headers)
    return display.style.apply(row_style, axis=1).format(
        {
            "ATM Strike": "{:.0f}",
            "CE Break Even": "{:.2f}",
            "PE Break Even": "{:.2f}",
        },
        na_rep="-",
    )


def metric_tile(label: str, value: float, change: float | None = None, difference: float | None = None) -> None:
    delta_value = 0 if pd.isna(change) else change
    delta_class = "metric-delta-pos" if delta_value >= 0 else "metric-delta-neg"
    diff_text = "" if pd.isna(difference) else f"{difference:+,.2f}"
    pct_text = "" if pd.isna(change) else f"{change:+.2f}%"
    change_text = f"<span class='{delta_class}'>{diff_text} | {pct_text}</span>" if diff_text or pct_text else ""
    st.markdown(
        f"""
        <div class="metric-tile">
          <div class="metric-label">{label}</div>
          <div class="metric-value">{value:,.2f}</div>
          <div>{change_text}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def attach_previous_oi_change(frame: pd.DataFrame, symbol: str, expiry: str | None) -> pd.DataFrame:
    if frame.empty:
        return frame

    key = f"previous_option_chain::{symbol}::{expiry or 'nearest'}"
    previous = st.session_state.get(key, {})
    enriched = frame.copy()
    for side in ("ce", "pe"):
        enriched[f"{side}_prev_oi_chg"] = enriched["strike"].map(
            lambda strike, prefix=side: previous.get(str(float(strike)), {}).get(f"{prefix}_oi_chg", np.nan)
        )

    st.session_state[key] = {
        str(float(row["strike"])): {"ce_oi_chg": float(row["ce_oi_chg"]), "pe_oi_chg": float(row["pe_oi_chg"])}
        for _, row in enriched.iterrows()
    }
    return enriched


def demo_prices() -> dict[str, dict[str, float]]:
    return {
        "NIFTY": {"price": 22870.65, "prev_close": 22795.20, "difference": 75.45, "change": 0.33},
        "SENSEX": {"price": 75242.90, "prev_close": 75011.40, "difference": 231.50, "change": 0.31},
        "BANKNIFTY": {"price": 48620.75, "prev_close": 48830.10, "difference": -209.35, "change": -0.43},
    }


def demo_candles(symbol: str, interval: str, days_back: int) -> pd.DataFrame:
    minutes = 390 if interval in {"1m", "2m", "3m", "5m", "15m", "30m"} else 1
    periods = min(260, max(80, days_back * max(1, minutes // 5)))
    freq = "5min" if interval.endswith("m") else "1D"
    rng = pd.date_range(end=pd.Timestamp.now(tz=IST).floor("5min"), periods=periods, freq=freq)
    seed = sum(ord(ch) for ch in symbol + interval)
    random = np.random.default_rng(seed)
    base = {"NIFTY": 22850, "SENSEX": 75200, "BANKNIFTY": 48600}.get(symbol, 22000)
    steps = random.normal(0, base * 0.0008, size=periods).cumsum()
    close = base + steps
    open_ = np.r_[close[0], close[:-1]] + random.normal(0, base * 0.00025, size=periods)
    spread = np.abs(random.normal(base * 0.001, base * 0.00035, size=periods))
    high = np.maximum(open_, close) + spread
    low = np.minimum(open_, close) - spread
    volume = random.integers(5000, 65000, size=periods)
    return pd.DataFrame({"open": open_, "high": high, "low": low, "close": close, "volume": volume}, index=rng)


def demo_option_chain(symbol: str) -> pd.DataFrame:
    price = demo_prices().get(symbol, demo_prices()["NIFTY"])["price"]
    step = 50 if symbol == "NIFTY" else 100
    atm = round(price / step) * step
    strikes = np.arange(atm - step * 9, atm + step * 10, step)
    rows = []
    for strike in strikes:
        distance = abs(strike - price)
        ce_ltp = max(8, (price - strike) + 120 - distance * 0.1)
        pe_ltp = max(8, (strike - price) + 120 - distance * 0.1)
        rows.append(
            {
                "strike": float(strike),
                "distance": distance,
                "ce_ltp": ce_ltp,
                "ce_be": strike + ce_ltp,
                "ce_iv": 14.5,
                "ce_delta": 0.5,
                "ce_volume": int(max(100, 45000 - distance * 30)),
                "ce_oi": int(max(100, 250000 - distance * 100)),
                "ce_oi_chg": int(2500 - distance),
                "pe_ltp": pe_ltp,
                "pe_be": strike - pe_ltp,
                "pe_iv": 15.1,
                "pe_delta": -0.5,
                "pe_volume": int(max(100, 42000 - distance * 28)),
                "pe_oi": int(max(100, 240000 - distance * 95)),
                "pe_oi_chg": int(2200 - distance),
                "underlying": price,
                "atm": atm,
            }
        )
    frame = pd.DataFrame(rows)
    frame["ce_false_volume"] = np.where(frame.index % 7 == 0, "Watch", "Clear")
    frame["pe_false_volume"] = np.where(frame.index % 6 == 0, "Watch", "Clear")
    return frame.sort_values("distance").head(18).sort_values("strike")


def main() -> None:
    setup_page()

    if "show_rsi" not in st.session_state:
        st.session_state["show_rsi"] = False

    env_name = st.sidebar.selectbox("Nubra environment", ["PROD", "UAT"], index=0)
    use_live_data = st.sidebar.checkbox("Use live Nubra data", value=True)
    use_env_creds = st.sidebar.checkbox("Use .env credentials", value=True)
    auto_refresh = st.sidebar.checkbox("Auto refresh", value=False)
    refresh_seconds = st.sidebar.number_input("Refresh seconds", min_value=15, max_value=300, value=45, step=15)
    expiry = st.sidebar.text_input("Expiry YYYYMMDD", value="", placeholder="Nearest if blank")

    header_left, header_button = st.columns([0.78, 0.22])
    with header_left:
        st.title("Smart Wealth AI 5")
    with header_button:
        if st.button("Daily / Weekly / Monthly RSI", use_container_width=True):
            st.session_state["show_rsi"] = not st.session_state["show_rsi"]

    if auto_refresh:
        if hasattr(st, "autorefresh"):
            st.autorefresh(interval=int(refresh_seconds * 1000), key="market_refresh")
        else:
            components.html(
                f"<script>setTimeout(() => window.parent.location.reload(), {int(refresh_seconds * 1000)});</script>",
                height=0,
            )

    if use_live_data:
        with st.spinner("Connecting Nubra live data..."):
            market_data, status = get_market_data_client(env_name, use_env_creds)
    else:
        market_data, status = None, DataStatus(False, "Demo mode. Turn on 'Use live Nubra data' in sidebar for live market data.")
    prices = fetch_current_prices(market_data)

    cols = st.columns(3)
    for col, symbol in zip(cols, INDEX_SYMBOLS):
        with col:
            metric_tile(
                symbol,
                prices[symbol]["price"],
                prices[symbol].get("change"),
                prices[symbol].get("difference"),
            )

    st.caption(status.message)

    selected_symbol, selected_minutes = st.columns([0.62, 0.38])
    with selected_symbol:
        symbol = st.selectbox("Index", list(INDEX_SYMBOLS.keys()), index=0)
    with selected_minutes:
        if hasattr(st, "segmented_control"):
            minutes = st.segmented_control("Candle", TIMEFRAME_MINUTES, default=5, format_func=lambda value: f"{value} min")
        else:
            minutes = st.radio("Candle", TIMEFRAME_MINUTES, index=0, horizontal=True, format_func=lambda value: f"{value} min")

    exchange = INDEX_SYMBOLS[symbol]["exchange"]
    candles = add_indicators(fetch_intraday_candles(market_data, symbol, int(minutes), exchange))
    daily = fetch_historical(market_data, symbol, "1d", 45, exchange)
    levels = support_resistance(daily)
    signal = scalping_signal(candles, levels)
    option_table = fetch_option_chain(market_data, symbol, exchange, expiry.strip() or None)
    option_table = attach_previous_oi_change(option_table, symbol, expiry.strip() or None)

    if st.session_state["show_rsi"]:
        st.subheader("RSI")
        rsi_frame = rsi_timeframes(market_data, symbol, exchange)
        st.dataframe(rsi_frame, hide_index=True, use_container_width=True)

    signal_col, levels_col = st.columns([0.45, 0.55])
    with signal_col:
        st.markdown(
            f"""
            <div class="{signal['class']}">
                <div class="metric-label">Scalping Signal</div>
                <div class="metric-value">{signal['title']}</div>
                <div class="small-muted">{signal['detail']}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        if not candles.empty:
            latest = candles.iloc[-1]
            st.dataframe(
                pd.DataFrame(
                    [
                        {
                            "last": latest["close"],
                            "rsi": latest["rsi"],
                            "supertrend": latest["supertrend"],
                            "boring_candle": bool(latest["boring_candle"]),
                            "volume_spike": bool(latest["volume_spike"]),
                        }
                    ]
                ).style.format({"last": "{:.2f}", "rsi": "{:.2f}", "supertrend": "{:.2f}"}),
                hide_index=True,
                use_container_width=True,
            )

    with levels_col:
        st.subheader("Previous Market Open and Daily Levels")
        if levels:
            levels_frame = pd.DataFrame([levels]).rename(
                columns={
                    "prev_open": "Prev Open",
                    "prev_high": "Prev High",
                    "prev_low": "Prev Low",
                    "prev_close": "Prev Close",
                    "pivot": "Pivot",
                    "r1": "R1",
                    "s1": "S1",
                    "r2": "R2",
                    "s2": "S2",
                }
            )
            st.dataframe(levels_frame.style.format("{:.2f}"), hide_index=True, use_container_width=True)
        else:
            st.info("Daily levels unavailable.")

    marker_cols = st.columns([0.22, 0.22, 0.56])
    with marker_cols[0]:
        show_boring = st.checkbox("Boring candle marker", value=True)
    with marker_cols[1]:
        show_volume = st.checkbox("Volume spike marker", value=True)

    st.plotly_chart(
        candle_chart(
            candles.tail(110),
            symbol,
            levels=levels,
            option_table=option_table,
            show_boring=show_boring,
            show_volume=show_volume,
        ),
        use_container_width=True,
    )

    st.subheader("Option Chain")
    if option_table.empty:
        st.info("Option-chain data unavailable.")
    else:
        st.dataframe(style_option_table(option_table), hide_index=True, use_container_width=True, height=520)

    if st.session_state.get("last_data_error"):
        with st.expander("Last market-data message"):
            st.write(st.session_state["last_data_error"])
    if st.session_state.get("last_option_error"):
        with st.expander("Last option-chain message"):
            st.write(st.session_state["last_option_error"])


try:
    main()
except Exception as exc:
    st.title("Smart Wealth AI 5")
    st.error("Dashboard stopped before loading.")
    st.exception(exc)
