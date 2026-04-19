#src/nubra_python_sdk/marketdata/validation.py
from pydantic import BaseModel # type: ignore
from typing import List, Optional
from enum import Enum
from datetime import datetime
from typing import List, Dict
from pydantic import BaseModel, Field, RootModel, model_validator, field_validator, ConfigDict, FieldValidationInfo# type: ignore
import pytz # type: ignore

class ExchangeEnum(str, Enum):
    """Enumerates supported exchanges."""
    NSE = "NSE"
    BSE = "BSE"

class SecurityTypeEnum(str, Enum):
    """Enumerates security types."""
    STOCK = "STOCK"
    INDEX= "INDEX"
    OPT= "OPT"
    FUT= "FUT"
    CHAIN= "CHAIN"



class Timeseries(BaseModel):
    """
    Represents a request payload for historical time series data.
    
    Attributes:
        exchange (ExchangeEnum): Market exchange (NSE, BSE).
        type (SecurityTypeEnum): Type of the security (e.g. STOCK, INDEX).
        values (List[str]): List of security symbols or instruments.
        fields (List[str]): Metrics to fetch (e.g., open, close).
        startDate (str): Start date in YYYY-MM-DD format.
        endDate (str): End date in YYYY-MM-DD format.
        interval (str): Interval (e.g., "1d", "5m").
        intraDay (bool): Whether to fetch intraday data.
        realTime (bool): Whether to fetch real-time data.
    """
    exchange: ExchangeEnum
    type: SecurityTypeEnum
    values: List[str]
    fields: List[str]
    startDate: str
    endDate: str
    interval: str
    intraDay: bool
    realTime: bool





class DerivativeTypeEnum(str, Enum):
    """Enumerates derivative types (currently only OPT supported)."""
    OPT="OPT"




class TimeSeriesPoint(BaseModel):
    """
    Represents a single time-series datapoint.
    """
    timestamp: Optional[int] = Field(default= None, alias="ts") # converted from UNIX timestamp to pyhton datetime object
    value: int = Field(default= None, alias="v")

    model_config = ConfigDict(
        from_attributes=True,     
        populate_by_name=True, 
        ser_json_exclude_none= True,
        ser_dict_exclude_none= True       
    )



class TickPoint(BaseModel):
    """
    Represents a single tick datapoint.
    """
    timestamp: Optional[int] = Field(default= None, alias="ts") # converted from UNIX timestamp to python datetime object
    value: Optional[float] = Field(default= None, alias="v")

    model_config = ConfigDict(
        from_attributes=True,     
        populate_by_name=True, 
        ser_json_exclude_none= True,
        ser_dict_exclude_none= True       
    )


class StockChart(BaseModel):
    """
    Holds different time-series fields for a security.

    Attributes:
        open, high, low, close, cumulative_volume (List[TimeSeriesPoint]):
            Lists of data points for each metric.
    """
    open: Optional[List[TimeSeriesPoint]] = Field(default_factory=list)
    high: Optional[List[TimeSeriesPoint]] = Field(default_factory=list)
    low: Optional[List[TimeSeriesPoint]] = Field(default_factory=list)
    close: Optional[List[TimeSeriesPoint]] = Field(default_factory=list)
    tick_volume: Optional[List[TimeSeriesPoint]] = Field(default_factory=list)
    theta: Optional[List[TickPoint]] = Field(default_factory=list)
    delta: Optional[List[TickPoint]] = Field(default_factory=list)
    gamma: Optional[List[TickPoint]] = Field(default_factory= list)
    vega: Optional[List[TickPoint]] = Field(default_factory= list)
    iv_bid: Optional[List[TickPoint]] = Field(default_factory= list)
    iv_ask: Optional[List[TickPoint]] = Field(default_factory= list)
    iv_mid: Optional[List[TickPoint]] = Field(default_factory= list)
    cumulative_volume: Optional[List[TimeSeriesPoint]] = Field(default_factory=list)
    cumulative_volume_delta: Optional[List[TickPoint]] = Field(default_factory= list)
    cumulative_volume_premium: Optional[List[TimeSeriesPoint]] = Field(default_factory= list)
    cumulative_oi: Optional[List[TimeSeriesPoint]] = Field(default_factory= list)
    cumulative_call_oi: Optional[List[TimeSeriesPoint]] = Field(default_factory= list)
    cumulative_put_oi : Optional[List[TimeSeriesPoint]] = Field(default_factory= list)
    cumulative_fut_oi: Optional[List[TimeSeriesPoint]] = Field(default_factory= list)
    l1bid: Optional[List[TimeSeriesPoint]] = Field(default_factory= list)
    l1ask: Optional[List[TimeSeriesPoint]] = Field(default_factory= list)

class ChartData(BaseModel):
    """
    Wraps chart data per instrument.

    Attributes:
        exchange (str): Exchange of the instrument.
        type (str): Security type.
        values (List[Dict[str, StockChart]]): Symbol-to-chart mapping.
    """
    exchange: str
    type: str
    values: List[Dict[str, StockChart]]  

class MarketChartsResponse(BaseModel):
    """
    Represents the full response for a time series request.

    Attributes:
        market_time (str): Time of data snapshot.
        message (str): Status message.
        result (List[ChartData]): List of chart data entries.
    """
    market_time: Optional[str]= None
    message: str
    result: Optional[List[ChartData]] = None

#For quotes
class OrderLevel(BaseModel):
    """
    Represents a single bid/ask level in an order book.

    Attributes:
        price (float): Price in paise.
        quantity (int): Quantity.
        num_orders (int): Number of orders at this level.
    """
    price: Optional[int]= Field(default= None, alias="p") # price in paise (e.g., 193580 -> ₹1935.80)
    quantity: Optional[int]= Field(default= None, alias= "q") # quantity
    num_orders: Optional[int]= Field(default= None, alias= "o") # number of orders

    model_config = ConfigDict(
        from_attributes=True,     
        populate_by_name=True, 
        ser_json_exclude_none= True,
        ser_dict_exclude_none= True       
    )



class OrderBook(BaseModel):
    """
    Full order book snapshot for a specific instrument.

    Attributes:
        ref_id (int): Reference ID.
        timestamp (datetime): timestamp.
        bid (List[OrderLevel]): Bid-side levels.
        ask (List[OrderLevel]): Ask-side levels.
        last_traded_price (float): Last traded price (in paise).
        ltq (int): Last traded quantity.
        volume (int): Total traded volume.
    """
    ref_id: Optional[int] = None
    timestamp: Optional[int] = Field(default=None, alias="ts") # timestamp
    bid: Optional[List[OrderLevel]]= None 
    ask: Optional[List[OrderLevel]]= None
    last_traded_price: int= Field(default= None, alias= "ltp")  # last traded price convert it to rupees
    last_traded_quantity: int= Field(default= None, alias= "ltq") # last traded quantity
    volume: Optional[int]= None
    
    model_config = ConfigDict(
        from_attributes=True,     
        populate_by_name=True, 
        ser_json_exclude_none= True,
        ser_dict_exclude_none= True       
    )





class OrderBookWrapper(BaseModel):
    """
    Wrapper for order book response.

    Attributes:
        orderBook (OrderBook): The order book data.
    """
    orderBook: OrderBook



# Option Chain Models

class OptionData(BaseModel):
    """
    Represents individual call/put option data.

    Attributes:
        ref_id (int): Reference ID.
        timestamp (datetime): timestamp_epoch
        strike_price (int): Strike price.
        ls (int): Lot size.
        ltp (int): Last traded price (in paise).
        ltpchg (Optional[float]): Price change.
        iv (Optional[float]): Implied volatility.
        delta, gamma, theta, vega (Optional[float]): Greeks.
        oi (int): Open interest.
        volume (int): Traded volume.
    """
    ref_id: int
    timestamp: Optional[int]= Field(default= None,alias= "ts")
    strike_price: int= Field(default= None, alias= "sp")        # strike price #convert to Rs
    lot_size: Optional[int]= Field(default= None, alias= "ls")     # lot size
    last_traded_price: Optional[int]= Field(default= None, alias= "ltp")      # last traded price
    last_traded_price_change: Optional[float]= Field(default= None, alias= "ltpchg")
    iv: Optional[float] = None
    delta: Optional[float] = None
    gamma: Optional[float] = None
    theta: Optional[float] = None
    vega: Optional[float] = None
    open_interest: Optional[int]= Field(default= None, alias= "oi") # open interest
    previous_open_interest: Optional[int]= Field(default= None, alias= "prev_oi") 
    volume: Optional[int]= None

    model_config = ConfigDict(
        from_attributes=True,     
        populate_by_name=True, 
        ser_json_exclude_none= True,
        ser_dict_exclude_none= True       
    )



class OptionChain(BaseModel):
    """
    Represents a full option chain for a given symbol and expiry.

    Attributes:
        asset (str): Underlying asset symbol.
        expiry (str): Expiry date (YYYYMMDD).
        ce (List[OptionData]): Call options.
        pe (List[OptionData]): Put options.
        atm (int): At-the-money strike.
        cp (int): Current price.
        all_expiries (List[str]): Available expiry dates.
    """
    asset: str
    expiry: str
    ce: List[OptionData]
    pe: List[OptionData]
    at_the_money_strike: Optional[int]= Field(default= None, alias="atm")       # at-the-money strike
    current_price: Optional[int] = Field(default= None, alias= "cp")           # current price
    all_expiries: List[str]

    model_config = ConfigDict(
        from_attributes=True,     
        populate_by_name=True, 
        ser_json_exclude_none= True,
        ser_dict_exclude_none= True       
    )


class OptionChainWrapper(BaseModel):
    """
    Wrapper for the option chain API response.

    Attributes:
        chain (OptionChain): Full option chain data.
        message (str): Status message.
    """
    chain: OptionChain
    message: str
    exchange: Optional[str]= None

    model_config = ConfigDict(
        from_attributes=True,     
        populate_by_name=True, 
        ser_json_exclude_none= True,
        ser_dict_exclude_none= True       
    )

    model_config = ConfigDict(
        from_attributes=True,     
        populate_by_name=True, 
        ser_json_exclude_none= True,
        ser_dict_exclude_none= True       
    )



# Current Option Price
class CurrentPrice(BaseModel):
    """
    Represents the current price snapshot of an option.

    Attributes:
        change (float): Change in price.
        message (str): Response message.
        prev_close (float): Previous close price.
        price (float): Current price.
    """
    change: Optional[float]= None
    message: str
    exchange: Optional[str] = None
    prev_close: Optional[int]= None
    price: Optional[int]= None

    model_config = ConfigDict(
        from_attributes=True,     
        populate_by_name=True, 
        ser_json_exclude_none= True,
        ser_dict_exclude_none= True       
    )







