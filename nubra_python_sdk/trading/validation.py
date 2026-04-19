
#src/nubra_python_sdk/trading/validation.py
from pydantic import BaseModel, RootModel, field_validator, Field, ConfigDict, model_validator # type: ignore
from datetime import datetime
from typing import List, Optional, Dict
from decimal import Decimal, ROUND_HALF_UP
from pydantic import FieldValidationInfo

from nubra_python_sdk.trading.trading_enum import(
    RequestTypeEnum, 
    OrderTypeEnum, 
    OrderStatusEnum, 
    OrderSideEnum, 
    DeliveryTypeEnum, 
    ExecutionTypeEnum, 
    OrderTypeEnumV2, 
    PriceTypeEnumV2, 
    BenchMarkTypeV2, 
    ValidityTypeEnumV2, 
    ExchangeEnum, 
    BasketStatusEnum, 
    BasketStrategyEnum,
    ExecutionStatusEnum,
    ExecutionTypeEnum,
    OptionTypeEnum
)



#src/nubra_python_sdk/trading/security.py
class StockItem(BaseModel):
    ref_id: int
    quantity: int

class EdisMetaData(BaseModel):
    DPId: Optional[int]= None
    Version: Optional[str]= None
    ReqId: Optional[str]= None
    TransDtls: Optional[str]= None

class EdisResponse(BaseModel):
    data: EdisMetaData
    message: str
    redirect_url: Optional[str]= None



class StockData(BaseModel):
    ref_id: int
    quantity: int
    display_name: str
    exchange: str

class StockHoldings(BaseModel):
    holdings: Optional[List[StockData]] = Field(default_factory=list)

class StockNonEdis(BaseModel):
    data: StockHoldings
    message: str


class EdisHoldingsData(BaseModel):
    stocks: Optional[List[StockItem]] = Field(default_factory=list)


class EdisHoldingRefIDS(BaseModel):
    data: EdisHoldingsData
    message: str


class EdisHolding(BaseModel):
    stock_quantity_map: Dict[str, int]

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        ser_json_exclude_none=True,
        ser_dict_exclude_none=True
    )

class EdisHoldingsResponse(BaseModel):
    data: EdisHolding
    message: str

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        ser_json_exclude_none=True,
        ser_dict_exclude_none=True
    )



#src/nubra_python_sdk/trading/trading_data.py

#get order
class RefData(BaseModel):
    """
    Metadata associated with a reference ID in an order.
    
    Attributes:
        ref_id: Reference ID.
        nubra_id: Internal mapped ID.
        option_type: Type of the option (e.g., CE, PE).
        token: Unique token for the instrument.
        stock_name: Name of the stock or asset.
        nubra_name: Internal mapped name .
        lot_size: Lot size for the instrument.
        asset: Asset class (e.g., EQUITY, DERIVATIVE).
        exchange: Exchange name (e.g., NSE, BSE).
        derivative_type: Futures/Options/Other derivative types.
    """
    ref_id: int
    option_type: Optional[str]
    token: Optional[int]= None
    stock_name: str
    nubra_name: str= Field(alias= "zanskar_name")
    lot_size: Optional[int]= None
    asset: str
    exchange: str
    derivative_type: Optional[str]= None

    model_config= ConfigDict(
        from_attributes= True,
        populate_by_name= True,
        ser_json_exclude_none= True,
        ser_dict_exclude_none= True   
    )


#Make margin request
class ItemRequest(BaseModel):
    ref_id: int
    request_type: RequestTypeEnum
    order_type: OrderTypeEnum
    order_delivery_type: DeliveryTypeEnum
    order_qty: int
    order_price: Optional[int]= None
    order_side: OrderSideEnum
    execution_type: ExecutionTypeEnum

    model_config = ConfigDict(
        from_attributes=True,     
        populate_by_name=True, 
        ser_json_exclude_none= True,
        ser_dict_exclude_none= True       
    )

class MarginRequest(BaseModel):
    with_portfolio: bool
    with_legs: Optional[bool]= None
    order_req: List[ItemRequest]

    model_config = ConfigDict(
        from_attributes=True,     
        populate_by_name=True, 
        ser_json_exclude_none= True,
        ser_dict_exclude_none= True       
    )

    
class LegMargin(BaseModel):
    ref_id: Optional[int]
    span: Optional[int]= None
    exposure: Optional[int]= None
    total_margin: Optional[int]= None
    delivery_margin: Optional[int]= None
    opt_prem: Optional[int]= None
    var: Optional[int]= None
    net_span: Optional[int]= None
    total_derivative_margin: Optional[int]= None
    total_equity_margin: Optional[int]= None
    margin_benefit: Optional[int]= None
        
    model_config = ConfigDict(
        from_attributes=True,     
        populate_by_name=True, 
        ser_json_exclude_none= True,
        ser_dict_exclude_none= True       
    )


class MarginResponse(BaseModel):
    span: Optional[int]= None
    exposure: Optional[int]= None
    total_margin : Optional[int]= None
    delivery_margin: Optional[int]= None
    opt_prem: Optional[int]= None
    var: Optional[int]= None
    net_span: Optional[int]= None
    total_derivative_margin: Optional[int]= None
    total_equity_margin: Optional[int]= None
    margin_benefit: Optional[int]= None
    leg_margin: Optional[List[LegMargin]] = Field(default_factory=list)
    edis_auth_done: Optional[bool]= None
    max_quantity: Optional[int]= None
    message: Optional[str] = None
    max_quantity: Optional[int] = None

        
    @field_validator("leg_margin", mode="before")
    @classmethod
    def _none_to_list(cls, v):
        # when the server returns null
        return [] if v is None else v

    model_config = ConfigDict(
        from_attributes=True,     
        populate_by_name=True, 
        ser_json_exclude_none= True,
        ser_dict_exclude_none= True       
    )




#>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>----------------------------------------V2-Version ---------------------------------------->>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>



#Validation for Single order
class AlgoParamsV2(BaseModel):
    min_prate: Optional[float] = None
    max_prate: Optional[float] = None
    leg_size : Optional[int] = None
    trigger_price: Optional[int] = None
    benchmark_price: Optional[int] = None
    benchmark_type: Optional[BenchMarkTypeV2]= None
    cleanup_price: Optional[int] = None
    entry_price: Optional[int] = None
    exit_price: Optional[int] = None
    cleanup_max_prate: Optional[float]= None
    count_otm_volume: Optional[bool] = None
    start_time: Optional[str] = None
    end_time: Optional[str] = None

    
    model_config = ConfigDict(
        from_attributes=True,     
        populate_by_name=True, 
        ser_json_exclude_none= True,
        ser_dict_exclude_none= True   
    )

class CreateOrderV2(BaseModel):
    algo_id : Optional[str] = None
    ref_id: int
    order_type: OrderTypeEnumV2
    order_qty: int
    order_side: OrderSideEnum
    order_delivery_type : DeliveryTypeEnum
    validity_type : ValidityTypeEnumV2
    price_type : PriceTypeEnumV2
    order_price: Optional[int] = None
    exchange: ExchangeEnum
    tag: Optional[str] = None

    algo_params: Optional[AlgoParamsV2] = None

    @model_validator(mode="after")
    def check_price_type(self):
        if self.algo_id and self.price_type == PriceTypeEnumV2.MARKET:
            raise ValueError("MARKET orders not allowed with algo_id")
        return self
    
    model_config = ConfigDict(
        from_attributes=True,     
        populate_by_name=True, 
        ser_json_exclude_none= True,
        ser_dict_exclude_none= True   
    )




class CreateOrderResponseV2(BaseModel):
    order_id : int
    algo_id : Optional[str] = None
    exchange: Optional[ExchangeEnum] = None
    basket_id: Optional[int] = None
    exchange_order_id: Optional[int] = None
    ref_id: Optional[int] = None
    order_type: OrderTypeEnumV2
    order_side: OrderSideEnum
    order_price: Optional[int] = None
    order_qty: Optional[int] = None
    filled_qty: Optional[int] = None
    avg_filled_price: Optional[int] = None
    order_status: Optional[str] = None
    last_modified: Optional[int] = None
    ref_data: Optional[RefData]= None
    last_traded_price: Optional[int]= Field(default= None, alias= "LTP")
    order_delivery_type: DeliveryTypeEnum
    display_name: Optional[str] = None
    brokerage : Optional[float] = None
    price_type: PriceTypeEnumV2
    validity_type: ValidityTypeEnumV2
    execution_type: Optional[str]= None
    leg_size: Optional[int] = None
    duration: Optional[int] = None
    trigger_price: Optional[int] = None
    max_prate: Optional[int]= None
    algo_params : Optional[AlgoParamsV2] = None
    tag: Optional[str] = None
    update_msg: Optional[str]= None
    
    model_config = ConfigDict(
        from_attributes=True,    
        populate_by_name=True, 
        ser_json_exclude_none= True,
        ser_dict_exclude_none= True        
    )

class GetOrderResponseV2(BaseModel):
    order_id : int
    algo_id : Optional[str] = None
    ref_id : Optional[int] = None
    order_type : Optional[OrderTypeEnumV2] = None
    order_side : Optional[OrderSideEnum] = None
    order_price : Optional[int] = None
    order_qty : Optional[int] = None
    filled_qty : Optional[int] = None
    avg_filled_price : Optional[int] = None
    order_status : Optional[OrderStatusEnum] = None
    order_time : Optional[int] = None
    ack_time : Optional[int] = None
    filled_time: Optional[int] = None
    last_modified : Optional[int] = None
    updated_by : Optional[int] = None
    ref_data : Optional[RefData] = None
    order_delivery_type : Optional[DeliveryTypeEnum] = None
    display_name : Optional[str] = None
    brokerage : Optional[float] = None
    price_type : Optional[PriceTypeEnumV2] = None
    validity_type : Optional[ValidityTypeEnumV2] = None
    exchange_order_id : Optional[int] = None
    execution_type : Optional[str] = None
    algo_params : Optional[AlgoParamsV2] = None
    exchange : Optional[ExchangeEnum] = None
    LTP : Optional[int] = None
    is_sor : Optional[bool] = None
    order_expiry_date : Optional[int] = None

    model_config = ConfigDict(
        from_attributes=True,    
        populate_by_name=True, 
        ser_json_exclude_none= True,
        ser_dict_exclude_none= True        
    )
 
class MetaInfo(BaseModel):
    trailing_sl_limit_price: Optional[int] = None
    trailing_sl_trigger_price: Optional[int] = None
    parent_order_id: Optional[int] = None
    response_id: Optional[int] = None

    model_config= ConfigDict(
        from_attributes= True,
        populate_by_name= True,
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

class ExecutionResponseV2(BaseModel):
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
    request_type: Optional[str] = None

    @model_validator(mode="before")
    @classmethod
    def map_id(cls, data):
        raw_id = data.get("id")

        if data.get("execution_type") == "EXECUTION_TYPE_FLEXI" or data.get("basket_params"):
            data["basket_id"] = raw_id
            if data.get("order_params") != None:
                data["order_params"] = None
        else:
            data["order_id"] = raw_id
            if data.get("basket_params") != None:
                data["basket_params"] = None

        data.pop("id", None)
        return data



    model_config = ConfigDict(
        from_attributes=True,    
        populate_by_name=True, 
        ser_json_exclude_none= True,
        ser_dict_exclude_none= True   
    )  

#Validation for MultiOrder
class SingleMultiOrderV2(BaseModel):
    ref_id: int
    order_type: OrderTypeEnumV2
    order_qty: int
    order_side: OrderSideEnum
    order_delivery_type : DeliveryTypeEnum
    validity_type : ValidityTypeEnumV2
    price_type : PriceTypeEnumV2
    order_price: Optional[int] = None
    tag: Optional[str] = None
    algo_params: Optional[AlgoParamsV2] = None
    
    model_config = ConfigDict(
        from_attributes=True,     
        populate_by_name=True, 
        ser_json_exclude_none= True,
        ser_dict_exclude_none= True   
    )


class MultiOrderV2(BaseModel):
    orders: List[CreateOrderV2]

    model_config = ConfigDict(
        from_attributes=True,     
        populate_by_name=True, 
        ser_json_exclude_none= True,
        ser_dict_exclude_none= True   
    )


class MultiOrderResponseV2(BaseModel):
    orders: List[CreateOrderResponseV2]


#Validation for Basket Order
class SingleBasketOrderV2(BaseModel):
    ref_id: int
    order_qty : int
    order_side: OrderSideEnum

    model_config = ConfigDict(
        from_attributes=True,     
        populate_by_name=True, 
        ser_json_exclude_none= True,
        ser_dict_exclude_none= True   
    )

class BasketParamsV2(BaseModel):
    order_side: OrderSideEnum
    order_delivery_type: DeliveryTypeEnum
    price_type: PriceTypeEnumV2

    multiplier: int

    entry_price: Optional[int]= None
    momentum_trigger_price: Optional[int] = None

    exit_price : Optional[int] = None
    stoploss_price: Optional[int] = None

    entry_time: Optional[str]= None
    exit_time: Optional[str] = None

    basket_type_name: Optional[str] = None
    basket_strategy: Optional[BasketStrategyEnum] = None
    algo_params: Optional[AlgoParamsV2] = None
    model_config = ConfigDict(
        from_attributes=True,     
        populate_by_name=True, 
        ser_json_exclude_none= True,
        ser_dict_exclude_none= True   
    )


class BasketOrderV2(BaseModel):
    algo_id : Optional[str] = None
    exchange: ExchangeEnum
    basket_name: str
    order_type: Optional[OrderTypeEnumV2]= None
    tag: Optional[str]= None
    orders: List[SingleBasketOrderV2]
    basket_params: BasketParamsV2

    @model_validator(mode="after")
    def check_price_type(self):
        if self.algo_id and self.basket_params.price_type == PriceTypeEnumV2.MARKET:
            raise ValueError("MARKET orders not allowed with algo_id")
        return self

    model_config = ConfigDict(
        from_attributes=True,     
        populate_by_name=True, 
        ser_json_exclude_none= True,
        ser_dict_exclude_none= True   
    )



class BasketOrderResponseV2(BaseModel):
    basket_id: Optional[int]
    user_id: Optional[int] = None
    basket_name : Optional[str] = None
    orders: List[CreateOrderResponseV2]
    model_config = ConfigDict(
        from_attributes=True,     
        populate_by_name=True, 
        ser_json_exclude_none= True,
        ser_dict_exclude_none= True   
    )



class SingleBasketOrderModV2(BaseModel):
    ref_id: int

    model_config = ConfigDict(
        from_attributes=True,     
        populate_by_name=True, 
        ser_json_exclude_none= True,
        ser_dict_exclude_none= True   
    )


#validation for Mod Basket
class ModBasketRequestV2(BaseModel):
    algo_id : Optional[str] = None
    exchange: ExchangeEnum
    orders: List[SingleBasketOrderModV2]
    basket_params: BasketParamsV2

    @model_validator(mode="after")
    def check_price_type(self):
        if self.algo_id and self.basket_params.price_type == PriceTypeEnumV2.MARKET:
            raise ValueError("MARKET orders not allowed with algo_id")
        return self

    model_config = ConfigDict(
        from_attributes=True,     
        populate_by_name=True, 
        ser_json_exclude_none= True,
        ser_dict_exclude_none= True   
    )

#validation for mod order 
class ModOrderRequestV2(BaseModel):
    algo_id : Optional[str] = None
    order_qty : int
    order_price: int
    order_type: OrderTypeEnumV2
    exchange: ExchangeEnum
    algo_params: Optional[AlgoParamsV2] = None

    model_config = ConfigDict(
        from_attributes=True,     
        populate_by_name=True, 
        ser_json_exclude_none= True,
        ser_dict_exclude_none= True   
    )

class CreateOrderMargin(BaseModel):
    ref_id: int
    order_type: Optional[OrderTypeEnumV2] = None
    order_qty: int
    order_side: OrderSideEnum
    order_delivery_type : Optional[DeliveryTypeEnum] = None
    validity_type : Optional[ValidityTypeEnumV2] = None
    price_type : Optional[PriceTypeEnumV2] = None
    order_price: Optional[int] = None

    algo_params: Optional[AlgoParamsV2] = None
    request_type: Optional[RequestTypeEnum] = None
    
    model_config = ConfigDict(
        from_attributes=True,     
        populate_by_name=True, 
        ser_json_exclude_none= True,
        ser_dict_exclude_none= True   
    )

class BasketOrderMargin(BaseModel):
    order_side: Optional[OrderSideEnum] = None
    order_delivery_type: Optional[DeliveryTypeEnum] =  None
    price_type: Optional[PriceTypeEnumV2] = None

    multiplier: int

    entry_price: Optional[int]= None
    momentum_trigger_price: Optional[int] = None

    exit_price : Optional[int] = None
    stoploss_price: Optional[int] = None

    entry_time: Optional[str]= None
    exit_time: Optional[str] = None

    basket_type_name: Optional[str] = None
    basket_strategy: Optional[BasketStrategyEnum] = None
    algo_params: Optional[AlgoParamsV2] = None
    model_config = ConfigDict(
        from_attributes=True,     
        populate_by_name=True, 
        ser_json_exclude_none= True,
        ser_dict_exclude_none= True   
    )




#validation for margin required
class MarginOrderRequest(BaseModel):
    exchange: ExchangeEnum
    orders: Optional[List[CreateOrderMargin]] = Field(default_factory=list)
    basket_params: Optional[BasketOrderMargin] = None
    model_config = ConfigDict(
        from_attributes=True,     
        populate_by_name=True, 
        ser_json_exclude_none= True,
        ser_dict_exclude_none= True   
    )

class MarginRequired(BaseModel):
    with_portfolio: bool
    with_legs: Optional[bool]= None
    is_basket: Optional[bool] = None
    order_req: MarginOrderRequest

    model_config = ConfigDict(
        from_attributes=True,     
        populate_by_name=True, 
        ser_json_exclude_none= True,
        ser_dict_exclude_none= True       
    )


#Validation for canceeling order 
class CancelRequestV2(BaseModel):
    exchange: ExchangeEnum
    order_type: OrderTypeEnumV2


#validation for get orders
class GetAllOrdersV2(RootModel[List[CreateOrderResponseV2]]):
    pass


class GetAllExecutions(RootModel[List[ExecutionResponseV2]]):
    pass


class BasketIDParamsV2(BaseModel):
    order_side: Optional[OrderSideEnum] = None
    order_delivery_type: Optional[str]= None
    price_type: Optional[PriceTypeEnumV2] = None

    multiplier: Optional[int]= None

    entry_price: Optional[int]= None
    momentum_trigger_price: Optional[int] = None

    exit_price : Optional[int] = None
    stoploss_price: Optional[int] = None

    entry_time: Optional[str]= None
    exit_time: Optional[str] = None

    basket_strategy: Optional[str] = None
    request_type: Optional[str] = None
    basket_status: Optional[BasketStatusEnum] = None
    basket_type_name: Optional[str] = None
    msg: Optional[str] = None
    basket_strategy: Optional[BasketStrategyEnum] = None
    algo_params: Optional[AlgoParamsV2] = None

    model_config = ConfigDict(
        from_attributes=True,     
        populate_by_name=True, 
        ser_json_exclude_none= True,
        ser_dict_exclude_none= True   
    )

class BasketParams(BaseModel):
    basket_strategy: str
    entry_price: Optional[int]
    exit_price: Optional[int]
    stoploss_price: Optional[int]
    entry_time: datetime
    exit_time: Optional[datetime] = None
    multiplier: Optional[int]
    momentum_trigger_price: Optional[int]
    order_side: OrderSideEnum
    order_delivery_type: DeliveryTypeEnum
    price_type: PriceTypeEnumV2
    basket_status: BasketStatusEnum
    basket_type_name: Optional[str] = None
    basket_strategy: Optional[BasketStrategyEnum] = None
    algo_params: Optional[AlgoParamsV2] = None


class BasketIDOrdersV2(BaseModel):
    exchange_order_id: Optional[int] = None
    exchange: Optional[str] = None
    order_id: int
    basket_id: Optional[int] = None
    ref_id: int
    order_type: Optional[OrderTypeEnumV2] = None
    order_side: Optional[OrderSideEnum] = None
    order_price: Optional[int] = None
    order_qty: Optional[int] = None
    filled_qty: Optional[int] = None
    avg_filled_price: Optional[int] = None
    order_status: Optional[OrderStatusEnum] = None
    order_time: Optional[int] = None
    ack_time: Optional[int] = None
    filled_time: Optional[int] = None
    last_modified: Optional[int] = None
    ref_data: Optional[RefData] = None
    order_delivery_type: Optional[DeliveryTypeEnum] = None
    display_name: Optional[str] = None
    brokerage: Optional[int] = None
    price_type: Optional[PriceTypeEnumV2] = None
    validity_type: Optional[ValidityTypeEnumV2] = None
    execution_type: Optional[str] = None
    last_traded_price: Optional[int] = Field(default= None, alias= "LTP")
    pnl: Optional[int] = None
    pnl_change: Optional[float] = None




class GetBasketV2(BaseModel):
    basket_id:Optional[int] = None
    algo_id : Optional[str] = None
    user_id: Optional[int] = None
    basket_name: Optional[str] = None
    tag: Optional[str] = None
    orders: Optional[List[BasketIDOrdersV2]]= Field(default_factory=list)
    basket_params: Optional[BasketIDParamsV2] = None
    last_traded_price: Optional[int] = Field(default=None, alias= "LTP")
    pnl: Optional[int] = None
    pnl_change: Optional[float] = None


class GetBasketResponseV2(RootModel[List[GetBasketV2]]):
    pass


class RefData(BaseModel):
    ref_id: int
    lot_size: int
    derivative_type: str

class Order(BaseModel):
    order_side: OrderSideEnum
    buy_qty: int
    sell_qty: int
    buy_avg: int
    sell_avg: int
    display_name: str
    ref_data: RefData
    last_traded_price: Optional[int] = Field(default=None, alias= "LTP")
    pnl: int
    pnl_change: float


class Basket(BaseModel):
    basket_id: int
    algo_id : Optional[str] = None
    user_id: int
    exchange: str
    basket_name: str
    tag: Optional[str] = None
    orders: Dict[str, Order]
    basket_params: BasketParams
    last_traded_price: Optional[int] = Field(default=None, alias= "LTP")
    pnl: int
    pnl_change: float

class BasketList(RootModel[Optional[list[Basket]]]):
    pass