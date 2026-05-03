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


def is_intraday_interval(interval: str) -> bool:
    return interval.endswith(("s", "m", "h"))


def fetch_historical(
    market_data: Any | None,
    symbol: str,
    interval: str,
    days_back: int,
    exchange: str,
    instrument_type: str = "INDEX",
    intra_day: bool | None = None,
) -> pd.DataFrame:
    if market_data is None:
        return demo_candles(symbol, interval, days_back)

    end = datetime.now(timezone.utc)
    start = end - timedelta(days=days_back)
    intraday = is_intraday_interval(interval) if intra_day is None else intra_day
    request = {
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
    try:
        response = market_data.historical_data(request)
        frames = response_to_frames(response)
        frame = frames.get(symbol, pd.DataFrame())
        if frame.empty and intraday:
            today_start = datetime.now(timezone.utc).replace(hour=3, minute=30, second=0, microsecond=0)
            retry_request = {**request, "startDate": utc_iso(today_start), "intraDay": True}
            response = market_data.historical_data(retry_request)
            frames = response_to_frames(response)
            frame = frames.get(symbol, pd.DataFrame())
        if frame.empty:
            st.session_state["last_data_error"] = f"No OHLC candles returned for {symbol} {interval} from Nubra."
        return frame
    except Exception as exc:
        st.toast(f"{symbol} history unavailable.")
        st.session_state["last_data_error"] = str(exc)
        return pd.DataFrame()


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
        return fetch_historical(market_data, symbol, f"{minutes}m", 7, exchange, intra_day=False)

    base = fetch_historical(market_data, symbol, "5m", 7, exchange, intra_day=False)
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
