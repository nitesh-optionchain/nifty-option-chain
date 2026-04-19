#src/nubra_python_sdk/ticker/validation.py
import math
from typing import List, Optional, Dict
from datetime import datetime
from pydantic import BaseModel, field_validator, Field , ConfigDict, model_validator # type: ignore
from enum import Enum, IntEnum
import msgspec # type: ignore
import math
from typing import Optional



# --- Index Data ---
class IndexDataWrapper(msgspec.Struct):
    indexname: str
    exchange: Optional[str] = None
    timestamp: Optional[int] = None
    index_value: Optional[int] = None
    high_index_value : Optional[int] = None
    low_index_value : Optional[int] = None
    volume: Optional[int] = None
    changepercent: Optional[float] = None
    tick_volume: Optional[int] = None
    prev_close: Optional[int] = None
    volume_oi: Optional[int] = None



class Orders(msgspec.Struct):
    price: Optional[int] = None
    quantity: Optional[int] = None
    num_orders: Optional[int] = None


class OrderBookWrapper(msgspec.Struct):
    ref_id: Optional[int]
    timestamp: Optional[int]  # Store raw nanoseconds; convert to datetime lazily
    last_traded_price: Optional[int] = None
    last_traded_quantity: Optional[int] = None
    volume: Optional[int] = None
    bids: list[Orders] = []
    asks: list[Orders] = []


class OptionData(msgspec.Struct):
    """
    Represents data for a single option contract.
    """
    ref_id: Optional[int] = None
    timestamp: Optional[int] = None  # Store as nanoseconds
    strike_price: Optional[int] = None
    lot_size: Optional[int] = None
    last_traded_price: Optional[int] = None
    last_traded_price_change: Optional[float] = None
    iv: Optional[float] = None
    delta: Optional[float] = None
    gamma: Optional[float] = None
    theta: Optional[float] = None
    vega: Optional[float] = None
    volume: Optional[int] = None
    open_interest: Optional[int] = None
    previous_open_interest: Optional[int] = None
    price_pcp: Optional[int] = None



class OptionChainWrapper(msgspec.Struct):
    """
    Wraps CE and PE option data for a given asset and expiry.
    """
    asset: Optional[str] = None
    expiry: Optional[str] = None
    at_the_money_strike: Optional[int] = None
    current_price: Optional[int] = None
    exchange: Optional[str] = None
    ce: list[OptionData] = []
    pe: list[OptionData] = []



class OhlcvDataWrapper(msgspec.Struct):
    indexname: Optional[str]
    exchange: Optional[str]
    interval: Optional[str]
    timestamp: Optional[int]
    open: Optional[int]
    high: Optional[int]
    low: Optional[int]
    close: Optional[int]
    bucket_volume: Optional[int]
    tick_volume: Optional[int]
    cumulative_volume: Optional[int]
    bucket_timestamp : Optional[int]


class BatchWebSocketIndexMessage(msgspec.Struct):
    timestamp: Optional[int] = None
    indexes: list[IndexDataWrapper] = []
    instruments: list[IndexDataWrapper] =[]

class BatchWebSocketOrderbookMessage(msgspec.Struct):
    timestamp: Optional[int] = None
    instruments: list[OrderBookWrapper] = None

class BatchWebSocketGreeksMessage(msgspec.Struct):
    timestamp: Optional[int] = None
    instruments: list[OptionData] = None

class IntervalEnum(str, Enum):
    BucketInterval1S= "1s"
    BucketInterval2S = "2s"
    BucketInterval5S = "5s"
    BucketInterval1M = "1m"
    BucketInterval2M = "2m"
    BucketInterval3M = "3m"
    BucketInterval5M = "5m"
    BucketInterval10m = "10m"
    BucketInterval15m = "15m"
    BucketInterval30m = "30m"
    BucketInterval1H = "1h"
    BucketInterval2H = "2h"
    BucketInterval4H = "4h"
    BucketInterval1D = "1d"

class SubscribeIntervalEnum(str, Enum):
    Interval1s = "1s"
    Interval5S = "5s"
    Interval10S = "10s"
    Interval30S = "30s"
    Interval1M = "1m"
    Interval5M ="5m"
    Interval10M = "10m"

class ExecutionTypeEnum(str, Enum):
    """Enumerates possible execution types for an order."""
    STRATEGY_TYPE_LIMIT= "STRATEGY_TYPE_LIMIT"
    STRATEGY_TYPE_MARKET= "STRATEGY_TYPE_MARKET"
    STRATEGY_TYPE_IOC= "STRATEGY_TYPE_IOC"
    STRATEGY_TYPE_ICEBERG= "STRATEGY_TYPE_ICEBERG"
    STRATEGY_TYPE_STOPLOSS= "STRATEGY_TYPE_STOPLOSS"
    STRATEGY_TYPE_VWAP= "STRATEGY_TYPE_VWAP"
    STRATEGY_TYPE_TWAP= "STRATEGY_TYPE_TWAP"
    STRATEGY_TYPE_CLOSE= "STRATEGY_TYPE_CLOSE"

class DeliveryTypeEnum(str, Enum):
    """Enumerates delivery types for orders."""
    ORDER_DELIVERY_TYPE_IDAY= "ORDER_DELIVERY_TYPE_IDAY"
    ORDER_DELIVERY_TYPE_CNC= "ORDER_DELIVERY_TYPE_CNC"
    ORDER_DELIVERY_TYPE_INVALID = "ORDER_DELIVERY_TYPE_INVALID"

class OrderTypeEnum(str, Enum):
    """Enumerates types of orders."""
    ORDER_TYPE_LIMIT= "ORDER_TYPE_LIMIT"
    ORDER_TYPE_MARKET= "ORDER_TYPE_MARKET"


class OrderSideEnum(str, Enum):
    ORDER_SIDE_BUY= "ORDER_SIDE_BUY"
    ORDER_SIDE_SELL= "ORDER_SIDE_SELL"

class OrderStatusEnum(str, Enum):
  ORDER_STATUS_PENDING= "ORDER_STATUS_PENDING"
  ORDER_STATUS_SENT = "ORDER_STATUS_SENT"
  ORDER_STATUS_OPEN = "ORDER_STATUS_OPEN"
  ORDER_STATUS_REJECTED = "ORDER_STATUS_REJECTED"
  ORDER_STATUS_CANCELLED = "ORDER_STATUS_CANCELLED"
  ORDER_STATUS_FILLED = "ORDER_STATUS_FILLED"
  ORDER_STATUS_EXPIRED = "ORDER_STATUS_EXPIRED"
  ORDER_STATUS_TRIGGERED = "ORDER_STATUS_TRIGGERED"
  ORDER_STATUS_PARTIAL_FILLED = "ORDER_STATUS_PARTIAL_FILLED"

class OrderResponseTypeEnum(str, Enum):
    ORDER_RESPONSE_INVALID = "ORDER_RESPONSE_INVALID"
    ORDER_ACCEPTED = "ORDER_ACCEPTED"
    ORDER_REJECTED = "ORDER_REJECTED"
    ORDER_FILLED = "ORDER_FILLED"
    ORDER_TRIGGERED = "ORDER_TRIGGERED"
    ORDER_CANCELLED = "ORDER_CANCELLED"
    BASKET_FILLED = "BASKET_FILLED"

class OrderRequestTypeEnum(str, Enum):
  ORDER_REQUEST_NEW = "ORDER_REQUEST_NEW"
  ORDER_REQUEST_MOD = "ORDER_REQUEST_MOD"
  ORDER_REQUEST_CANCEL = "ORDER_REQUEST_CANCEL"


class BenchMarkTypeV2(str, Enum):
    BENCHMARK_TYPE_VWAP = "BENCHMARK_TYPE_VWAP"
    BENCHMARK_TYPE_ARRIVAL = "BENCHMARK_TYPE_ARRIVAL"
    BENCHMARK_TYPE_MANUAL = "BENCHMARK_TYPE_MANUAL"


class MetaInfo(BaseModel):
    trailing_sl_limit_price: Optional[int] = None
    trailing_sl_trigger_price: Optional[int] = None
    parent_order_id: Optional[int] = None
    response_id : Optional[int] = None


#Validation for Single order
class AlgoParamsV2(BaseModel):
    min_prate: Optional[int] = None
    max_prate: Optional[int] = None
    algo_duration: Optional[int] = None
    benchmark_type: Optional[BenchMarkTypeV2]= None
    benchmark_price: Optional[int] = None
    cleanup_price: Optional[int] = None
    trigger_price: Optional[int] = None
    leg_size : Optional[int] = None
    algo_id : Optional[str] = None
    count_otm_volume: Optional[bool] = None
    cleanup_max_prate: Optional[float] = None
    start_time: Optional[int] = None
    end_time: Optional[int] = None
    trailing_sl_delta: Optional[int] = None
    min_prate_float: Optional[float] = None
    max_prate_float: Optional[float] = None
    
    
    model_config = ConfigDict(
        from_attributes=True,     
        populate_by_name=True, 
        ser_json_exclude_none= True,
        ser_dict_exclude_none= True   
    )


class OrderInfoWrapper(BaseModel):
    exchange: Optional[str] = Field(default= None, alias= "exch")
    exchange_order_id : Optional[int]= None
    order_id: Optional[int]= None
    ref_id: Optional[int]= None
    side: OrderSideEnum
    trade_qty: Optional[int] = None
    trade_price: Optional[int] = None
    order_type: Optional[str] = None
    order_type_v2: Optional[str] = None
    strategy_type: str
    order_status : OrderStatusEnum
    order_qty : Optional[int]= None
    order_price : Optional[int]= None
    display_name : Optional[str]= None
    last_modified: Optional[int]= Field(default= None, alias= "ack_time")   #change it to last_modified
    update_msg: Optional[str]= None
    response_type : str
    filled_qty : Optional[int]= None
    avg_price : Optional[int]= None
    trigger_price : Optional[int]= None
    price_type: Optional[str] = None
    validity_type: Optional[str] = None
    leg_size: Optional[int] = None
    algo_duration: Optional[int] = None
    max_prate: Optional[int] = None
    algo_params: Optional[AlgoParamsV2] = None
    asset_type: Optional[str] = None
    is_sor: Optional[bool] = None
    tag: Optional[str] = None
    request_type: Optional[OrderRequestTypeEnum] = None
    order_expiry_date: Optional[int] = None
    meta_info: Optional[MetaInfo] = None

    model_config = ConfigDict(   
        from_attributes=True,    
        populate_by_name=True, 
        ser_json_exclude_none= True,
        ser_dict_exclude_none= True   
    )    


class BasketWrapper(BaseModel):
    basket_id : int
    last_modified : int
    response_type: str



class AckInfoWrapper(BaseModel):
    exchange: Optional[str] = Field(default=None, alias= "exch")
    exchange_order_id : Optional[int]= None
    order_id: Optional[int]= None
    ref_id: Optional[int]= None
    side: OrderSideEnum
    trade_qty: Optional[int] = None
    trade_price: Optional[int] = None 
    order_type: Optional[str] = None # not prescent 
    order_type_v2: Optional[str] = None  # not prescent 
    strategy_type: str # not prescent 
    order_status : OrderStatusEnum # not prescent, execution_status
    order_qty : Optional[int]= None  # not prescent, qty
    filled_qty : Optional[int]= None
    avg_price : Optional[int]= None # not prescent 
    order_price : Optional[int]= None    
    display_name : Optional[str]= None
    last_modified: Optional[int]= Field(default= None, alias= "ack_time")  #change it to last_modified, last_modified time
    update_msg: Optional[str]= None
    response_type : str
    price_type: Optional[str] = None
    validity_type: Optional[str] = None # not prescent 
    leg_size: Optional[int] = None # not prescent 
    algo_duration: Optional[int] = None # not prescent 
    max_prate: Optional[int] = None # not prescent 
    algo_params: Optional[AlgoParamsV2] = None
    asset_type: Optional[str] = None
    is_sor: Optional[bool] = None
    tag: Optional[str]= None
    request_type: Optional[OrderRequestTypeEnum] = None
    order_expiry_date: Optional[int] = None
    meta_info: Optional[MetaInfo] = None

    model_config = ConfigDict(
        from_attributes=True,    
        populate_by_name=True, 
        ser_json_exclude_none= True,
        ser_dict_exclude_none= True   
    ) 

class OrderParam(BaseModel):
    order_price: Optional[int] = None
    avg_fill_price: Optional[int] = None
    filled_qty: Optional[int] = None
    zanskar_id: Optional[int] = None
    ref_id: Optional[int] = None
    stock_name: Optional[str] = None
    asset_type: Optional[str] = None
    derivative_type: Optional[str] = None
    algo_params: Optional[AlgoParamsV2] = None
    exchange_order_id: Optional[int] = None
    trade_qty: Optional[int] = None
    trade_price: Optional[int] = Field(default=None, alias=["trade_pice", "trade_price"])
    validity_type: Optional[str] = Field(default=None, alias=["validity_type", "vlidity_type"])
    asset: Optional[str] = None
    lot_size: Optional[int] = None
    order_expiry_date: Optional[int] = None
    expiry: Optional[int] = None
    option_type: Optional[str] = None
    strike_price : Optional[int] = None
    side: Optional[str] = None
    display_name: Optional[str] = None
    qty: Optional[int] = None
    meta_info : Optional[MetaInfo] = None
 
    model_config= ConfigDict(
        from_attributes= True,
        populate_by_name= True,
        ser_json_exclude_none= True,
        ser_dict_exclude_none= True   
    )

class BasktParams(BaseModel):
    basket_strategy : Optional[str] = None
    entry_price: Optional[int] = None
    exit_price: Optional[int] = None
    stoploss_price: Optional[int] = None
    momentum_trigger_price: Optional[int] = None
    start_tie: Optional[int] = None
    end_time: Optional[int] = None
    order_params: Optional[List[OrderParam]] = []
    basket_type_name: Optional[str] = None
    algo_params: Optional[AlgoParamsV2] = None
    filled_entry_price: Optional[int] = None
    filled_exit_price: Optional[int] = None

    model_config= ConfigDict(
        from_attributes= True,
        populate_by_name= True,
        ser_json_exclude_none= True,
        ser_dict_exclude_none= True   
    )

class ExecutionInfoWrapper(BaseModel):
    order_id: Optional[int] = None
    basket_id: Optional[int] = None    
    response_type: Optional[str] = None
    delivery_type: Optional[str] = None
    execution_type: Optional[str] = None
    side : Optional[str] = None
    price_type : Optional[str] = None
    qty: Optional[int] = None
    execution_status: Optional[str] = None
    last_mdified_time : Optional[int] = None
    creation_time: Optional[int] = None
    display_name: Optional[str] = None
    order_params: Optional[OrderParam] = None
    basket_params: Optional[BasktParams] = None
    ltp: Optional[int] = None
    update_msg: Optional[str] = None
    exchange: Optional[str] = Field(default=None, alias=["exch", "exchange"])
    is_sor: Optional[bool] = None
    tag: Optional[str] = None
    request_type: Optional[OrderRequestTypeEnum] = None

    @model_validator(mode="before")
    @classmethod
    def map_id(cls, data):
        raw_id = data.get("id")

        if data.get("execution_type") == "EXECUTION_TYPE_FLEXI" or data.get("basket_params"):
            data["basket_id"] = raw_id
            if data.get("order_params") != None:
                data["order_params"] = None
        else:
            if data.get("basket_params") != None:
                data["basket_params"] = None
            data["order_id"] = raw_id

        data.pop("id", None)
        return data



    model_config = ConfigDict(
        from_attributes=True,    
        populate_by_name=True, 
        ser_json_exclude_none= True,
        ser_dict_exclude_none= True   
    ) 

class ExchangeType(str, Enum):
  EXCH_NSE = "EXCH_NSE"
  EXCH_BSE = "EXCH_BSE"

class OrderDeliveryType (str, Enum):
  ORDER_DELIVERY_TYPE_CNC = "ORDER_DELIVERY_TYPE_CNC"
  ORDER_DELIVERY_TYPE_IDAY = "ORDER_DELIVERY_TYPE_IDAY"

class OrderSide (str, Enum):
  ORDER_SIDE_BUY = "ORDER_SIDE_BUY"
  ORDER_SIDE_SELL = "ORDER_SIDE_SELL"

class Holding(msgspec.Struct):
    ref_id: Optional[int] = None
    zanskar_name: Optional[str] = None
    display_name: Optional[str] = None
    derivative_type: Optional[str] = None
    strike_price: Optional[int] = None
    lot_size: Optional[int] = None
    exchange: Optional[ExchangeType] = None
    asset: Optional[str] = None
    symbol: Optional[str] = None
    qty: Optional[int] = None
    pledged_qty: Optional[int] = None
    t1_qty: Optional[int] = None
    avg_price: Optional[int] = None
    prev_close: Optional[int] = None
    ltp: Optional[int] = None
    ltp_chg: Optional[float] = None
    invested_value: Optional[int] = None
    current_value: Optional[int] = None
    net_pnl: Optional[int] = None
    net_pnl_chg: Optional[float] = None
    day_pnl: Optional[int] = None
    haircut: Optional[float] = None
    margin_benefit: Optional[int] = None
    available_to_pledge: Optional[int] = None
    supported_exchanges: Optional[Dict[str, int]] = None

class HoldingStats(msgspec.Struct):
    invested_amount: Optional[int] = None
    current_value: Optional[int] = None
    total_pnl: Optional[int] = None
    total_pnl_chg: Optional[float] = None
    day_pnl : Optional[int] = None
    day_pnl_chg: Optional[float] = None

class HoldingsResponse(msgspec.Struct):
    client_code: Optional[str] = None
    holding_stats: Optional[HoldingStats] = None
    holdings: Optional[List[Holding]] = None

class PositionStruct(msgspec.Struct):
    ref_id: Optional[int] = None
    zanskar_name: Optional[str] = None
    display_name: Optional[str] = None
    derivative_type: Optional[str] = None
    strike_price: Optional[int] = None
    lot_size: Optional[int] = None
    exchange: Optional[ExchangeType] = None
    asset: Optional[str] = None
    symbol: Optional[str] = None
    order_delivery_type: Optional[OrderDeliveryType] = None
    order_side: Optional[OrderSide] = None
    qty: Optional[int] = None
    ltp: Optional[int] = None
    avg_price: Optional[int] = None
    avg_buy_price: Optional[int] = None
    avg_sell_price: Optional[int] = None
    pnl: Optional[int] = None
    pnl_chg: Optional[float] = None

class PositionStats(msgspec.Struct):
    realised_pnl: Optional[int] = None
    unrealised_pnl: Optional[int] = None
    total_pnl: Optional[int] = None
    total_pnl_chg: Optional[float] = None

class PositionsResponse(msgspec.Struct):
    client_code: Optional[str] = None
    position_stats: Optional[PositionStats] = None
    stock_positions: Optional[List[PositionStruct]] = None
    fut_positions: Optional[List[PositionStruct]] = None
    opt_positions: Optional[List[PositionStruct]] = None
    close_positions: Optional[List[PositionStruct]] = None

class PortfolioResponse(msgspec.Struct):
    position_response: Optional[PositionsResponse] = None
    holding_response: Optional[HoldingsResponse] = None