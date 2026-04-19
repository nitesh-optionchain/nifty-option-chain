#src/nubra_python_sdk/marketdata/market_data.py
import logging

from typing import Union, List, Optional
from pydantic import ValidationError # type: ignore
from nubra_python_sdk.start_sdk import InitNubraSdk
from nubra_python_sdk.interceptor.htttpclient import BaseHttpClient
from nubra_python_sdk.interceptor.errors import NubraValidationError
from nubra_python_sdk.marketdata.validation import (
    Timeseries,
    MarketChartsResponse,
    OrderBookWrapper,
    OptionChainWrapper,
    CurrentPrice, 
    ExchangeEnum
    )
logger= logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())
print = lambda *args, **kwargs: None


class MarketData(InitNubraSdk):
    """
    Fetches real-time, historical, and options market data from Nubra.
    """

    def __init__(self, client: InitNubraSdk):
        """
        Initializes the MarketData instance using the provided Nubra SDK client.

        Args:
            client (InitNubraSdk): An authenticated instance of InitNubraSdk.
        """
        self.api_base_url = client.API_BASE_URL
        self.db_path= client.db_path
        self.totp_login = client.totp_login
        self.token_data = client.token_data
        self.db_path = client.db_path
        self.env_path_login = client.env_path_login
        self.client = BaseHttpClient(self)

    def _url(self, path):
        """
        Constructs the full API URL for a given endpoint path.

        Args:
            path (str): Relative API path.

        Returns:
            str: Full API URL.
        """
        return f"{self.api_base_url}/{path}"

    def quote(self, ref_id: int, levels: int):
        """
        Fetches real-time order book data for a given instrument.

        Args:
            ref_id (int): Reference ID of the instrument.
            levels (int): Depth levels of the order book to fetch.

        Returns:
            OrderBookWrapper: Parsed order book data model.

        Raises:
            NubraValidationError: If response fails Pydantic validation.
        """
        ref_id= str(ref_id)
        path = f"orderbooks/{ref_id}"
        if levels:
            levels=f"{levels}"
            path += f"?levels={levels}"
        try:
            response = self.client.request("get", self._url(path))
            return OrderBookWrapper(**response.json())
        except ValidationError as ve:
            raise NubraValidationError(ve.errors())

    def historical_data(self, request: Union[List[dict], dict]):
        """
        Fetches historical timeseries market data for given instruments and time range.

        This method retrieves OHLCV (Open, High, Low, Close, Volume) or custom field-level 
        data for one or more instruments across a specified date range and interval.

        Args:
            request (Union[List[dict], dict]): 
                A `Timeseries` model, list of models, or equivalent dictionary/dictionaries 
                representing the timeseries query. Each request should include:
                
                - `exchange` (str): Exchange name (e.g., "NSE", "BSE"). // enum exchanges
                - `type` (str): Instrument type (e.g., "STOCK", "INDEX").// enum types of data points
                - `values` (List[str]): List of instrument symbols.
                - `fields` (List[str]): Fields to retrieve (e.g., "open", "high", "low", "close", "volume").
                - `startDate` (str): ISO datetime string for start (UTC).
                - `endDate` (str): ISO datetime string for end (UTC).
                - `interval` (str): Interval granularity (e.g., "1d", "5m").// 1d, 1w, 1m, 1h, 1s, 1mth (month), 1y
                - `intraDay` (bool): // if true, then startDate and endDate will be ignored and current date will be picked
                - `realTime` (bool): // TBD

        Returns:
            MarketChartsResponse: A Pydantic model containing structured historical 
            market data, grouped by instrument and field.

        Raises:
            NubraValidationError: If the response JSON is invalid or does not conform to 
            the `MarketChartsResponse` schema.

        Example:
            >>> historical_data({
            ...     "exchange": "NSE",
            ...     "type": "STOCK",
            ...     "values": ["ASIANPAINT", "TATAMOTORS"],
            ...     "fields": ["close", "high", "low", "open", "cumulative_volume"],
            ...     "startDate": "2025-04-19T11:01:57.000Z",
            ...     "endDate": "2025-04-24T06:13:57.000Z",
            ...     "interval": "1d",
            ...     "intraDay": False, 
            ...     "realTime": False
            ... })
        """

        if isinstance(request, dict):
            try:
                request = [Timeseries(**request)]
            except ValidationError as ve:
                return NubraValidationError(ve.errors())
        elif isinstance(request, list) and request and isinstance(request[0], dict):
            try:
                request = [Timeseries(**item) for item in request]
            except ValidationError as ve:
                return {"message": ve.errors()}

        payload = {
            "query": [ts.model_dump(by_alias=True) for ts in request]
        }
        try:
            response = self.client.request("post", self._url("charts/timeseries"), json=payload)
            return MarketChartsResponse(**response.json())
        except ValidationError as ve:
            raise NubraValidationError(ve.errors())

    def current_price(self, instrument: str, exchange: Optional[ExchangeEnum] = None):
        """
        Fetches the current price data for a specific options instrument.

        Args:
            instrument (str): The symbol of the options instrument (e.g., 'NIFTY', 'BANKNIFTY').

        Returns:
            CurrentPrice: Parsed current option price data.

        Raises:
            NubraValidationError: If response fails Pydantic validation.
        """
        instrument = instrument.upper()
        if exchange == ExchangeEnum.NSE or exchange is None:
            path = f"optionchains/{instrument}/price"
        if exchange == ExchangeEnum.BSE:
            path = f"optionchains/{instrument}/price?exchange=BSE"

        try:
            response = self.client.request("get", self._url(path))
            return CurrentPrice(**response.json())
        except ValidationError as ve:
            raise NubraValidationError(ve.errors())

    def option_chain(self, instrument: str, expiry: Optional[str] = "", exchange: Optional[ExchangeEnum] = None):
        """
        Fetches the full option chain for a given instrument and optional expiry date.

        Args:
            instrument (str): The symbol of the options instrument (e.g., 'NIFTY', 'BANKNIFTY').
            expiry (Optional[str]): Expiry date in 'YYYYMMDD' format. If omitted, latest expiry is used.

        Returns:
            OptionChainWrapper: Parsed option chain data.

        Raises:
            NubraValidationError: If response fails Pydantic validation.

            ValueError: If expiry format is invalid.
        """
        instrument = instrument.upper()
        if exchange == ExchangeEnum.NSE or exchange is None:
            path = f"optionchains/{instrument}"
            if expiry:
                path += f"?expiry={expiry}"

        if exchange == ExchangeEnum.BSE:
            path = f"optionchains/{instrument}?exchange=BSE"
            if expiry:
                path+= f"&expiry={expiry}"
        try:
            response = self.client.request("get", self._url(path))
            return OptionChainWrapper(**response.json())
        except ValidationError as ve:
            raise NubraValidationError(ve.errors())
