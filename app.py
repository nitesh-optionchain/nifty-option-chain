from __future__ import annotations

import csv
import glob
import io
import os
import threading
import uuid
from collections import deque
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import pandas as pd
import requests
import streamlit as st

from nubra_python_sdk.start_sdk import InitNubraSdk, NubraEnv
from nubra_python_sdk.ticker import websocketdata

NIFTY_50_CSV_URL = "https://nsearchives.nseindia.com/content/indices/ind_nifty50list.csv"
LOG_TZ = ZoneInfo("Asia/Kolkata")
REFRESH_EVERY = "2s"
DEFAULT_ENV = os.getenv("NUBRA_ENV", "UAT").upper()
AUTH_STORE_DIR = Path(__file__).resolve().parent / ".streamlit_auth"

FALLBACK_CONSTITUENTS: list[tuple[str, str]] = [
    ("ADANIENT", "Adani Enterprises Ltd."),
    ("ADANIPORTS", "Adani Ports and Special Economic Zone Ltd."),
    ("APOLLOHOSP", "Apollo Hospitals Enterprise Ltd."),
    ("ASIANPAINT", "Asian Paints Ltd."),
    ("AXISBANK", "Axis Bank Ltd."),
    ("BAJAJ-AUTO", "Bajaj Auto Ltd."),
    ("BAJFINANCE", "Bajaj Finance Ltd."),
    ("BAJAJFINSV", "Bajaj Finserv Ltd."),
    ("BEL", "Bharat Electronics Ltd."),
    ("BHARTIARTL", "Bharti Airtel Ltd."),
    ("CIPLA", "Cipla Ltd."),
    ("COALINDIA", "Coal India Ltd."),
    ("DRREDDY", "Dr. Reddy's Laboratories Ltd."),
    ("EICHERMOT", "Eicher Motors Ltd."),
    ("ETERNAL", "Eternal Ltd."),
    ("GRASIM", "Grasim Industries Ltd."),
    ("HCLTECH", "HCL Technologies Ltd."),
    ("HDFCBANK", "HDFC Bank Ltd."),
    ("HDFCLIFE", "HDFC Life Insurance Company Ltd."),
    ("HINDALCO", "Hindalco Industries Ltd."),
    ("HINDUNILVR", "Hindustan Unilever Ltd."),
    ("ICICIBANK", "ICICI Bank Ltd."),
    ("ITC", "ITC Ltd."),
    ("INFY", "Infosys Ltd."),
    ("INDIGO", "InterGlobe Aviation Ltd."),
    ("JSWSTEEL", "JSW Steel Ltd."),
    ("JIOFIN", "Jio Financial Services Ltd."),
    ("KOTAKBANK", "Kotak Mahindra Bank Ltd."),
    ("LT", "Larsen & Toubro Ltd."),
    ("M&M", "Mahindra & Mahindra Ltd."),
    ("MARUTI", "Maruti Suzuki India Ltd."),
    ("MAXHEALTH", "Max Healthcare Institute Ltd."),
    ("NTPC", "NTPC Ltd."),
    ("NESTLEIND", "Nestle India Ltd."),
    ("ONGC", "Oil & Natural Gas Corporation Ltd."),
    ("POWERGRID", "Power Grid Corporation of India Ltd."),
    ("RELIANCE", "Reliance Industries Ltd."),
    ("SBILIFE", "SBI Life Insurance Company Ltd."),
    ("SHRIRAMFIN", "Shriram Finance Ltd."),
    ("SBIN", "State Bank of India"),
    ("SUNPHARMA", "Sun Pharmaceutical Industries Ltd."),
    ("TCS", "Tata Consultancy Services Ltd."),
    ("TATACONSUM", "Tata Consumer Products Ltd."),
    ("TMPV", "Tata Motors Passenger Vehicles Ltd."),
    ("TATASTEEL", "Tata Steel Ltd."),
    ("TECHM", "Tech Mahindra Ltd."),
    ("TITAN", "Titan Company Ltd."),
    ("TRENT", "Trent Ltd."),
    ("ULTRACEMCO", "UltraTech Cement Ltd."),
    ("WIPRO", "Wipro Ltd."),
]

AUTH_KEYS = [
    "auth_stage",
    "auth_phone",
    "auth_temp_token",
    "auth_auth_token",
    "auth_x_device_id",
    "auth_client",
    "auth_error",
    "auth_message",
    "auth_ok",
    "auth_env",
]


def resolve_env_name(env_name: str) -> NubraEnv:
    return NubraEnv.PROD if env_name.upper() == "PROD" else NubraEnv.UAT


def configure_client_environment(client: InitNubraSdk, env: NubraEnv) -> None:
    if env == NubraEnv.DEV:
        client.API_BASE_URL = "https://nubra-dev1.zanskar.xyz/api"
        client.WEBSOCKET_URL = "wss://nubra-dev1.zanskar.xyz/api/ws"
        client.WEBSOCKET_URL_BATCH = "wss://nubra-dev1.zanskar.xyz/apibatch/ws"
    elif env == NubraEnv.STAGING:
        client.API_BASE_URL = "https://nubra-staging.zanskar.xyz/api"
        client.WEBSOCKET_URL = "wss://nubra-staging.zanskar.xyz/api/ws"
        client.WEBSOCKET_URL_BATCH = "wss://nubra-staging.zanskar.xyz/apibatch/ws"
    elif env == NubraEnv.PROD:
        client.API_BASE_URL = "https://api.nubra.io"
        client.WEBSOCKET_URL = "wss://api.nubra.io/ws"
        client.WEBSOCKET_URL_BATCH = "wss://api.nubra.io/apibatch/ws"
    elif env == NubraEnv.UAT:
        client.API_BASE_URL = "https://uatapi.nubra.io"
        client.WEBSOCKET_URL = "wss://uatapi.nubra.io/ws"
        client.WEBSOCKET_URL_BATCH = "wss://uatapi.nubra.io/apibatch/ws"
    else:
        raise ValueError(f"Unsupported environment: {env}")


def default_row(symbol: str, company_name: str) -> dict[str, Any]:
    return {
        "company_name": company_name,
        "symbol": symbol,
        "last_price": None,
        "change_percent": None,
        "prev_close": None,
        "high": None,
        "low": None,
        "volume": None,
        "tick_volume": None,
        "updated_at": None,
    }


def to_display_price(raw_value: Any) -> float | None:
    if raw_value is None:
        return None

    try:
        return round(float(raw_value) / 100.0, 2)
    except (TypeError, ValueError):
        return None


def to_display_timestamp(raw_timestamp: Any) -> str | None:
    if raw_timestamp is None:
        return None

    try:
        ts = int(raw_timestamp)
    except (TypeError, ValueError):
        return None

    for scale in (1, 1_000, 1_000_000, 1_000_000_000):
        try:
            dt = datetime.fromtimestamp(ts / scale, tz=timezone.utc).astimezone(LOG_TZ)
            if 2000 <= dt.year <= 2100:
                return dt.strftime("%Y-%m-%d %H:%M:%S")
        except (OSError, OverflowError, ValueError):
            continue

    return str(ts)


def format_metric_value(value: Any) -> str:
    if value is None:
        return "Waiting..."
    return f"{value:,.2f}"


def format_metric_delta(change_percent: Any) -> str:
    if change_percent is None:
        return "No ticks yet"
    return f"{change_percent:.2f}%"


def mask_phone(phone: str | None) -> str:
    if not phone:
        return ""
    phone = phone.strip()
    if len(phone) <= 4:
        return phone
    return f"{phone[:2]}{'*' * max(0, len(phone) - 4)}{phone[-2:]}"


def fetch_nifty50_constituents() -> tuple[list[dict[str, str]], str, str | None]:
    try:
        response = requests.get(
            NIFTY_50_CSV_URL,
            headers={"User-Agent": "Mozilla/5.0"},
            timeout=20,
        )
        response.raise_for_status()
        rows = list(csv.DictReader(io.StringIO(response.text)))
        constituents = [
            {"symbol": row["Symbol"].strip(), "company_name": row["Company Name"].strip()}
            for row in rows
            if row.get("Symbol") and row.get("Company Name")
        ]
        if len(constituents) != 50:
            raise ValueError(f"Expected 50 NIFTY constituents, got {len(constituents)}.")
        return constituents, "Official NSE constituent CSV", None
    except Exception as exc:
        fallback = [
            {"symbol": symbol, "company_name": company_name}
            for symbol, company_name in FALLBACK_CONSTITUENTS
        ]
        return fallback, "Built-in fallback list", f"Official NSE CSV fetch failed: {exc}"


def ensure_auth_store_path() -> str:
    if "auth_store_path" not in st.session_state:
        AUTH_STORE_DIR.mkdir(parents=True, exist_ok=True)
        auth_id = uuid.uuid4().hex
        st.session_state["auth_store_path"] = str(AUTH_STORE_DIR / f"auth_{auth_id}.db")
    return st.session_state["auth_store_path"]


def cleanup_auth_store(path_str: str | None) -> None:
    if not path_str:
        return
    for file_path in glob.glob(f"{path_str}*"):
        try:
            os.remove(file_path)
        except OSError:
            pass


def build_sdk_shell(env_name: str, db_path: str) -> InitNubraSdk:
    env = resolve_env_name(env_name)
    client = InitNubraSdk.__new__(InitNubraSdk)
    configure_client_environment(client, env)
    client.totp_login = False
    client._InitNubraSdk__phone_number = None
    client._InitNubraSdk__mpin = None
    client.exchange_client_code = None
    client.client_code = None
    client.username = None
    client.password = None
    client.insti_login = False
    client.token_data = {}
    client.db_path = db_path
    client.env_path_login = False
    client.HEADERS = {"Content-Type": "application/json"}
    return client


class LiveNiftyFeed:
    def __init__(self, client: InitNubraSdk, env_name: str) -> None:
        self.client = client
        self.env_name = env_name.upper()
        self.lock = threading.RLock()
        self.logs: deque[str] = deque(maxlen=200)
        self.constituents, self.constituent_source, self.constituent_warning = fetch_nifty50_constituents()
        self.stock_symbols = [item["symbol"] for item in self.constituents]
        self.stock_rows = {
            item["symbol"]: default_row(item["symbol"], item["company_name"])
            for item in self.constituents
        }
        self.nifty_row = default_row("NIFTY", "Nifty 50 Index")
        self.status = "Preparing websocket..."
        self.connected = False
        self.last_error: str | None = None
        self.last_tick_at: str | None = None
        self.update_count = 0
        self.socket: websocketdata.NubraDataSocket | None = None
        self._startup()

    def _log(self, message: str) -> None:
        stamp = datetime.now(LOG_TZ).strftime("%Y-%m-%d %H:%M:%S")
        with self.lock:
            self.logs.appendleft(f"[{stamp}] {message}")

    def _set_status(self, message: str) -> None:
        with self.lock:
            self.status = message
        self._log(message)

    def _startup(self) -> None:
        try:
            self._set_status("Opening live websocket feed...")
            self.socket = websocketdata.NubraDataSocket(
                client=self.client,
                on_index_data=self._on_index_data,
                on_connect=self._on_connect,
                on_close=self._on_close,
                on_error=self._on_error,
            )
            self.socket.connect()
            self._set_status("WebSocket thread started. Subscribing to NIFTY and NIFTY 50 symbols...")
            self.socket.subscribe(["NIFTY", *self.stock_symbols], data_type="index", exchange="NSE")
            self._log(f"Subscribed to {1 + len(self.stock_symbols)} live symbols on the index stream.")
        except Exception as exc:
            self.last_error = f"Feed startup failed: {exc}"
            self.connected = False
            self._set_status("Feed startup failed.")
            self._log(self.last_error)

    def _on_connect(self, message: str) -> None:
        with self.lock:
            self.connected = True
            self.status = message
        self._log(message)

    def _on_close(self, reason: str) -> None:
        with self.lock:
            self.connected = False
            self.status = f"Closed: {reason}"
        self._log(f"WebSocket closed: {reason}")

    def _on_error(self, error_message: str) -> None:
        with self.lock:
            self.last_error = error_message
            if not self.connected:
                self.status = "Feed error"
        self._log(f"Feed error: {error_message}")

    def _message_to_row(self, message: Any) -> dict[str, Any]:
        return {
            "symbol": getattr(message, "indexname", None),
            "last_price": to_display_price(getattr(message, "index_value", None)),
            "change_percent": getattr(message, "changepercent", None),
            "prev_close": to_display_price(getattr(message, "prev_close", None)),
            "high": to_display_price(getattr(message, "high_index_value", None)),
            "low": to_display_price(getattr(message, "low_index_value", None)),
            "volume": getattr(message, "volume", None),
            "tick_volume": getattr(message, "tick_volume", None),
            "updated_at": to_display_timestamp(getattr(message, "timestamp", None)),
        }

    def _merge_update(self, target: dict[str, Any], update: dict[str, Any]) -> None:
        for key, value in update.items():
            if key == "symbol":
                continue
            if value is not None:
                target[key] = value

    def _on_index_data(self, message: Any) -> None:
        try:
            update = self._message_to_row(message)
            symbol = (update.get("symbol") or "").strip()
            if not symbol:
                return

            with self.lock:
                if symbol == "NIFTY":
                    self._merge_update(self.nifty_row, update)
                elif symbol in self.stock_rows:
                    self._merge_update(self.stock_rows[symbol], update)
                else:
                    return

                self.last_tick_at = update.get("updated_at") or datetime.now(LOG_TZ).strftime("%Y-%m-%d %H:%M:%S")
                self.update_count += 1
        except Exception as exc:
            self._on_error(f"Client callback failed for live tick: {exc}")

    def snapshot(self) -> dict[str, Any]:
        with self.lock:
            stocks = [dict(self.stock_rows[symbol]) for symbol in self.stock_symbols]
            nifty = dict(self.nifty_row)
            return {
                "env_name": self.env_name,
                "status": self.status,
                "connected": self.connected,
                "last_error": self.last_error,
                "last_tick_at": self.last_tick_at,
                "update_count": self.update_count,
                "nifty": nifty,
                "stocks": stocks,
                "logs": list(self.logs),
                "constituent_source": self.constituent_source,
                "constituent_warning": self.constituent_warning,
            }

    def close(self) -> None:
        try:
            if self.socket is not None:
                self.socket.close()
        except Exception as exc:
            self._log(f"Error while closing socket: {exc}")
        finally:
            with self.lock:
                self.connected = False
                self.status = "Stopped"


def close_live_feed() -> None:
    current_feed = st.session_state.get("live_nifty_feed")
    if current_feed is not None:
        current_feed.close()
    st.session_state.pop("live_nifty_feed", None)
    st.session_state.pop("live_nifty_feed_client_key", None)
    st.session_state.pop("live_nifty_feed_env", None)


def reset_auth_state(env_name: str, message: str | None = None) -> None:
    close_live_feed()
    auth_store_path = st.session_state.get("auth_store_path")
    cleanup_auth_store(auth_store_path)
    for key in AUTH_KEYS:
        st.session_state.pop(key, None)
    st.session_state["auth_stage"] = "phone"
    st.session_state["auth_phone"] = ""
    st.session_state["auth_temp_token"] = None
    st.session_state["auth_auth_token"] = None
    st.session_state["auth_x_device_id"] = None
    st.session_state["auth_client"] = None
    st.session_state["auth_error"] = None
    st.session_state["auth_message"] = message
    st.session_state["auth_ok"] = False
    st.session_state["auth_env"] = env_name


def ensure_auth_state(env_name: str) -> None:
    ensure_auth_store_path()
    if "auth_stage" not in st.session_state:
        reset_auth_state(env_name)
        return
    if st.session_state.get("auth_env") != env_name:
        reset_auth_state(env_name, "Environment changed. Please authenticate again.")


def get_or_create_feed(client: InitNubraSdk, env_name: str) -> LiveNiftyFeed:
    current_feed = st.session_state.get("live_nifty_feed")
    current_client_key = st.session_state.get("live_nifty_feed_client_key")
    current_env = st.session_state.get("live_nifty_feed_env")
    new_client_key = id(client)

    if current_feed is None or current_env != env_name or current_client_key != new_client_key:
        close_live_feed()
        st.session_state["live_nifty_feed"] = LiveNiftyFeed(client, env_name)
        st.session_state["live_nifty_feed_client_key"] = new_client_key
        st.session_state["live_nifty_feed_env"] = env_name

    return st.session_state["live_nifty_feed"]


def perform_logout(env_name: str) -> None:
    close_live_feed()
    client = st.session_state.get("auth_client")
    auth_store_path = st.session_state.get("auth_store_path")
    logout_error: str | None = None

    if client is not None:
        try:
            client.logout()
        except Exception as exc:
            logout_error = str(exc)

    cleanup_auth_store(auth_store_path)
    reset_auth_state(env_name, "Logged out from the SDK session.")
    if logout_error:
        st.session_state["auth_error"] = f"Logout completed locally, but SDK logout returned: {logout_error}"


def start_phone_auth(env_name: str, phone: str) -> None:
    phone = phone.strip()
    if not phone:
        raise ValueError("Enter a phone number.")

    auth_store_path = ensure_auth_store_path()
    cleanup_auth_store(auth_store_path)
    client = build_sdk_shell(env_name, auth_store_path)
    x_device_id = client._InitNubraSdk__ensure_device_id()
    temp_token = client._InitNubraSdk__send_otp(phone)

    st.session_state["auth_client"] = client
    st.session_state["auth_phone"] = phone
    st.session_state["auth_x_device_id"] = x_device_id
    st.session_state["auth_temp_token"] = temp_token
    st.session_state["auth_stage"] = "otp"
    st.session_state["auth_error"] = None
    st.session_state["auth_message"] = f"OTP sent to {mask_phone(phone)}."


def resend_otp() -> None:
    client: InitNubraSdk | None = st.session_state.get("auth_client")
    phone = st.session_state.get("auth_phone")
    if client is None or not phone:
        raise ValueError("Phone step is missing. Start again.")

    temp_token = client._InitNubraSdk__send_otp(phone)
    st.session_state["auth_temp_token"] = temp_token
    st.session_state["auth_error"] = None
    st.session_state["auth_message"] = f"OTP resent to {mask_phone(phone)}."


def verify_otp_step(otp: str) -> None:
    client: InitNubraSdk | None = st.session_state.get("auth_client")
    phone = st.session_state.get("auth_phone")
    temp_token = st.session_state.get("auth_temp_token")
    x_device_id = st.session_state.get("auth_x_device_id")
    if client is None or not phone or not temp_token or not x_device_id:
        raise ValueError("OTP session is missing. Start again.")

    auth_token = client._InitNubraSdk__verify_otp(phone, otp.strip(), temp_token, x_device_id)
    st.session_state["auth_auth_token"] = auth_token
    st.session_state["auth_stage"] = "mpin"
    st.session_state["auth_error"] = None
    st.session_state["auth_message"] = "OTP verified. Enter your MPIN to complete login."


def verify_mpin_step(mpin: str) -> None:
    client: InitNubraSdk | None = st.session_state.get("auth_client")
    auth_token = st.session_state.get("auth_auth_token")
    if client is None or not auth_token:
        raise ValueError("Auth token is missing. Verify OTP again.")

    client._InitNubraSdk__mpin = mpin
    verified = client._InitNubraSdk__verify__mpin(auth_token, mpin.strip())
    if not verified:
        raise ValueError("MPIN verification failed.")

    client._InitNubraSdk__get_user_info()
    st.session_state["auth_stage"] = "authenticated"
    st.session_state["auth_ok"] = True
    st.session_state["auth_error"] = None
    st.session_state["auth_message"] = "Authentication successful. Connecting the live feed now."


def build_stock_dataframe(stocks: list[dict[str, Any]]) -> pd.DataFrame:
    frame = pd.DataFrame(stocks)
    return frame[
        [
            "company_name",
            "symbol",
            "last_price",
            "change_percent",
            "high",
            "low",
            "prev_close",
            "volume",
            "tick_volume",
            "updated_at",
        ]
    ]


def render_auth_panel(env_name: str) -> None:
    stage = st.session_state.get("auth_stage", "phone")
    message = st.session_state.get("auth_message")
    error = st.session_state.get("auth_error")

    st.subheader("Authenticate With Nubra SDK")
    st.caption("Step 1: phone number. Step 2: OTP verification. Step 3: MPIN verification. The live websocket feed starts after login succeeds.")

    if message:
        st.success(message)
    if error:
        st.error(error)

    if stage == "phone":
        with st.form("phone_auth_form"):
            phone = st.text_input(
                "Phone number",
                value=st.session_state.get("auth_phone", ""),
                placeholder="Enter your registered phone number",
            )
            submitted = st.form_submit_button("Send OTP", use_container_width=True)
        if submitted:
            try:
                start_phone_auth(env_name, phone)
                st.rerun()
            except Exception as exc:
                st.session_state["auth_error"] = str(exc)
                st.session_state["auth_message"] = None
                st.rerun()

    elif stage == "otp":
        st.info(f"OTP was sent to {mask_phone(st.session_state.get('auth_phone'))}.")
        with st.form("otp_auth_form"):
            otp = st.text_input("OTP", placeholder="Enter the OTP you received")
            submitted = st.form_submit_button("Verify OTP", use_container_width=True)
        otp_cols = st.columns(2)
        if otp_cols[0].button("Resend OTP", use_container_width=True):
            try:
                resend_otp()
                st.rerun()
            except Exception as exc:
                st.session_state["auth_error"] = str(exc)
                st.session_state["auth_message"] = None
                st.rerun()
        if otp_cols[1].button("Start Over", use_container_width=True):
            reset_auth_state(env_name, "Authentication restarted.")
            st.rerun()
        if submitted:
            try:
                verify_otp_step(otp)
                st.rerun()
            except Exception as exc:
                st.session_state["auth_error"] = str(exc)
                st.session_state["auth_message"] = None
                st.rerun()

    elif stage == "mpin":
        st.info(f"OTP verified for {mask_phone(st.session_state.get('auth_phone'))}.")
        with st.form("mpin_auth_form"):
            mpin = st.text_input("MPIN", type="password", placeholder="Enter your MPIN")
            submitted = st.form_submit_button("Verify MPIN And Connect Feed", use_container_width=True)
        mpin_cols = st.columns(2)
        if mpin_cols[0].button("Back To OTP", use_container_width=True):
            st.session_state["auth_stage"] = "otp"
            st.session_state["auth_error"] = None
            st.session_state["auth_message"] = "Enter OTP again or resend it."
            st.rerun()
        if mpin_cols[1].button("Start Over", use_container_width=True):
            reset_auth_state(env_name, "Authentication restarted.")
            st.rerun()
        if submitted:
            try:
                verify_mpin_step(mpin)
                st.rerun()
            except Exception as exc:
                st.session_state["auth_error"] = str(exc)
                st.session_state["auth_message"] = None
                st.rerun()


st.set_page_config(page_title="NIFTY Live Dashboard", layout="wide")

st.title("NIFTY + NIFTY 50 Live Dashboard")
st.caption("Streamlit dashboard using the Nubra Python SDK websocket feed.")

selected_env = st.sidebar.selectbox(
    "SDK environment",
    options=["UAT", "PROD"],
    index=0 if DEFAULT_ENV != "PROD" else 1,
    help="Use UAT for testing or PROD for your live account/feed.",
)

ensure_auth_state(selected_env)

if st.session_state.get("auth_ok"):
    st.sidebar.success(f"Authenticated: {mask_phone(st.session_state.get('auth_phone'))}")
    if st.sidebar.button("Logout", use_container_width=True):
        perform_logout(selected_env)
        st.rerun()
else:
    st.sidebar.info("Authenticate to start the live feed.")

if not st.session_state.get("auth_ok"):
    render_auth_panel(selected_env)
    st.stop()

client: InitNubraSdk = st.session_state["auth_client"]
feed = get_or_create_feed(client, selected_env)

if st.sidebar.button("Reconnect feed", use_container_width=True):
    close_live_feed()
    st.rerun()

snapshot = feed.snapshot()
st.sidebar.write(f"Constituents source: {snapshot['constituent_source']}")
st.sidebar.write(f"Refresh interval: {REFRESH_EVERY}")


@st.fragment(run_every=REFRESH_EVERY)
def render_live_dashboard() -> None:
    live_snapshot = feed.snapshot()

    status_col, tick_col, updates_col, stocks_col = st.columns(4)
    status_col.metric("Connection", "Connected" if live_snapshot["connected"] else "Not connected")
    tick_col.metric("Last tick", live_snapshot["last_tick_at"] or "Waiting...")
    updates_col.metric("Ticks received", f"{live_snapshot['update_count']:,}")
    live_count = sum(1 for row in live_snapshot["stocks"] if row["last_price"] is not None)
    stocks_col.metric("Stocks updated", f"{live_count}/50")
    st.caption(f"Status: {live_snapshot['status']}")

    if live_snapshot["constituent_warning"]:
        st.warning(live_snapshot["constituent_warning"])

    if live_snapshot["last_error"]:
        st.error(live_snapshot["last_error"])

    nifty = live_snapshot["nifty"]
    nifty_cols = st.columns(4)
    nifty_cols[0].metric("NIFTY", format_metric_value(nifty["last_price"]), format_metric_delta(nifty["change_percent"]))
    nifty_cols[1].metric("Prev Close", format_metric_value(nifty["prev_close"]))
    nifty_cols[2].metric("Day High", format_metric_value(nifty["high"]))
    nifty_cols[3].metric("Day Low", format_metric_value(nifty["low"]))

    if live_count == 0:
        st.info("The dashboard is waiting for the first live websocket ticks.")

    frame = build_stock_dataframe(live_snapshot["stocks"])
    st.dataframe(
        frame,
        use_container_width=True,
        hide_index=True,
        column_config={
            "company_name": st.column_config.TextColumn("Company", width="large"),
            "symbol": st.column_config.TextColumn("Symbol", width="small"),
            "last_price": st.column_config.NumberColumn("Live Price", format="%.2f"),
            "change_percent": st.column_config.NumberColumn("Change %", format="%.2f%%"),
            "high": st.column_config.NumberColumn("High", format="%.2f"),
            "low": st.column_config.NumberColumn("Low", format="%.2f"),
            "prev_close": st.column_config.NumberColumn("Prev Close", format="%.2f"),
            "volume": st.column_config.NumberColumn("Volume", format="%d"),
            "tick_volume": st.column_config.NumberColumn("Tick Volume", format="%d"),
            "updated_at": st.column_config.TextColumn("Updated At", width="medium"),
        },
    )

    with st.expander("Feed log", expanded=False):
        st.code("\n".join(live_snapshot["logs"][:30]) or "No log entries yet.")


render_live_dashboard()
