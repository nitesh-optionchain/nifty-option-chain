#src/nubra_python_sdk/portfolio/validation.py
from pydantic import BaseModel, field_validator, Field, ConfigDict # type: ignore
from typing import List, Optional, Annotated, Any, Literal



#holdings
class Holding(BaseModel):
    """
    Represents an individual holding in a user's portfolio.

    Attributes:
        ref_id (int): Reference ID of the holding.
        nubra_name (str): Internal name used by Nubra (aliased from `zanskar_name`).
        displayName (str): Display name for UI.
        derivative_type (str): Type of derivative instrument, if applicable.
        strike_price (Optional[int]): Strike price in paise, converted to float.
        lot_size (Optional[int]): Lot size for derivative instruments.
        exchange (str): Exchange code (e.g., NSE, BSE).
        asset (str): Underlying asset type.
        symbol (str): Trading symbol.
        quantity (int): Number of units held (aliased from `qty`).
        pledged_qty (Optional[int]): Quantity pledged as collateral.
        t1_qty (Optional[int]): Quantity in T+1 settlement.
        avg_price (Optional[int]): Average buy price (converted from paise).
        prev_close (Optional[int]): Previous closing price.
        last_traded_price (Optional[int]): Last traded price (aliased from `ltp`).
        last_traded_price_change (Optional[int]): LTP change (aliased from `ltp_chg`).
        invested_value (Optional[int]): Total invested value.
        current_value (Optional[int]): Current market value.
        net_pnl (Optional[int]): Net profit or loss.
        net_pnl_chg (Optional[float]): Change in net PnL.
        day_pnl (Optional[int]): Daily profit or loss.
        haircut (Optional[float]): Haircut percentage for pledging.
        margin_benefit (Optional[int]): Margin benefit obtained from holding.
        available_to_pledge (Optional[int]): Quantity available for pledging.
    """
    ref_id: int = Field(alias= "ref_id")
    nubra_name: str= Field(alias= "zanskar_name")
    displayName: str
    derivative_type: str
    strike_price: Optional[int]= None
    lot_size: Optional[int]= None
    exchange: str
    asset: str
    symbol: str
    quantity: int= Field(default= None, alias= "qty")
    pledged_qty: Optional[int]= None
    t1_qty: Optional[int]= None
    avg_price: Optional[int]= None
    prev_close: Optional[int]= None
    last_traded_price: Optional[int]= Field(default= None, alias= "ltp")
    last_traded_price_change: Optional[float]= Field(default= None, alias= "ltp_chg")
    invested_value: Optional[int]= None
    current_value: Optional[int]= None
    net_pnl: Optional[int]= None
    net_pnl_chg: Optional[float] = None
    day_pnl: Optional[int] = None
    haircut: Optional[float]= None
    margin_benefit: Optional[int]
    available_to_pledge: Optional[int]= None
    is_pledgeable: Optional[bool] = None
        
    model_config = ConfigDict(
        from_attributes=True,     
        populate_by_name=True, 
        ser_json_exclude_none= True,
        ser_dict_exclude_none= True       
    )







class HoldingStats(BaseModel):
    """
    Summary statistics for all holdings in the portfolio.

    Attributes:
        invested_amount (Optional[float]): Total invested amount.
        current_value (Optional[float]): Current portfolio value.
        total_pnl (Optional[float]): Total profit or loss.
        total_pnl_chg (Optional[float]): Change in total PnL.
        day_pnl (Optional[float]): Daily PnL.
        day_pnl_chg (Optional[float]): Change in daily PnL.
    """
    invested_amount: Optional[int]= None
    current_value: Optional[int]= None
    total_pnl: Optional[int]= None
    total_pnl_chg: Optional[float]= None
    day_pnl: Optional[int]= None
    day_pnl_chg: Optional[float]= None
        
    model_config = ConfigDict(
        from_attributes=True,     
        populate_by_name=True, 
        ser_json_exclude_none= True,
        ser_dict_exclude_none= True       
    )
        



class Portfolio(BaseModel):
    """
    Represents the complete portfolio for holdings.

    Attributes:
        client_code (str): Unique identifier for the client.
        holding_stats (HoldingStats): Aggregated statistics for holdings.
        holdings (List[Holding]): List of individual holdings.
    """

    client_code: str
    holding_stats: Optional[HoldingStats]= None
    holdings: Optional[List[Holding]]= Field(default_factory=list)

    model_config = ConfigDict(
        from_attributes=True,     
        populate_by_name=True, 
        ser_json_exclude_none= True,
        ser_dict_exclude_none= True       
    )


class HoldingsMessage(BaseModel):
    """
    Message wrapper for holdings response.

    Attributes:
        message (Literal["holdings"]): Static message string identifier.
        portfolio (Portfolio): Portfolio object with holding details.
    """
    message: Literal["holdings"] = "holdings"  
    portfolio: Optional[Portfolio] = None

    model_config = ConfigDict(
        from_attributes=True,     
        populate_by_name=True, 
        ser_json_exclude_none= True,
        ser_dict_exclude_none= True       
    )



#positions
class PositionStats(BaseModel):
    """
    Summary statistics for open positions.

    Attributes:
        realised_pnl (Optional[float]): Realised profit or loss.
        unrealised_pnl (Optional[float]): Unrealised profit or loss.
        total_pnl (Optional[float]): Combined PnL.
        total_pnl_chg (Optional[float]): Change in total PnL.
    """

    realised_pnl: Optional[int]= None
    unrealised_pnl: Optional[int]= None
    total_pnl: Optional[int]= None
    total_pnl_chg: Optional[float]= None
        
    model_config = ConfigDict(
        from_attributes=True,     
        populate_by_name=True, 
        ser_json_exclude_none= True,
        ser_dict_exclude_none= True       
    )

class PositionStatsV2(BaseModel):
    """
    Summary statistics for open positions.

    Attributes:
        total_pnl (Optional[float]): Combined PnL.
        total_pnl_chg (Optional[float]): Change in total PnL.
    """
    total_pnl: Optional[int]= None
    total_pnl_chg: Optional[float]= None
        
    model_config = ConfigDict(
        from_attributes=True,     
        populate_by_name=True, 
        ser_json_exclude_none= True,
        ser_dict_exclude_none= True       
    )


class PositionStruct(BaseModel):
    """
    Represents an individual open or closed position.

    Attributes:
        ref_id (Optional[int]): Unique reference ID.
        nubra_name (str): Internal name (aliased from `zanskar_name`).
        displayName (Optional[str]): Display name for UI.
        derivative_type (Optional[str]): Type of derivative instrument.
        strike_price (Optional[int]): Strike price (in paise).
        lot_size (Optional[int]): Lot size for the instrument.
        exchange (str): Exchange where instrument is traded.
        asset (str): Asset class.
        symbol (str): Trading symbol.
        product (Optional[str]): Product type (e.g., MIS, CNC).
        order_side (Optional[str]): Order side (BUY/SELL).
        quantity (Optional[int]): Quantity in the position.
        last_traded_price (Optional[float]): LTP (aliased from `ltp`).
        avg_price (Optional[float]): Average price.
        avg_buy_price (Optional[float]): Average buy price.
        avg_sell_price (Optional[float]): Average sell price.
        pnl (Optional[float]): Current profit/loss.
        pnl_chg (Optional[float]): Change in PnL.
    """
    ref_id: Optional[int]
    nubra_name: str= Field(alias= "zanskar_name")
    displayName: Optional[str]= None
    derivative_type: Optional[str] = None
    strike_price: Optional[int]= None
    lot_size: Optional[int]= None
    exchange: str
    asset: str
    symbol: str
    product: Optional[str]= None
    order_side: Optional[str]= None
    quantity: Optional[int] = Field(default= None, alias= "qty")
    last_traded_price: Optional[int] = Field(alias= "ltp")
    avg_price: Optional[int]= None
    avg_buy_price: Optional[int]= None
    avg_sell_price: Optional[int]= None
    pnl: Optional[int]= None
    pnl_chg: Optional[float]= None

    model_config = ConfigDict(
        from_attributes=True,     
        populate_by_name=True, 
        ser_json_exclude_none= True,
        ser_dict_exclude_none= True       
    )

class PositionStructV2(BaseModel):
    """
    Represents an individual open or closed position.

    Attributes:
        ref_id (Optional[int]): Unique reference ID.
        nubra_name (str): Internal name (aliased from `zanskar_name`).
        displayName (Optional[str]): Display name for UI.
        derivative_type (Optional[str]): Type of derivative instrument.
        strike_price (Optional[int]): Strike price (in paise).
        lot_size (Optional[int]): Lot size for the instrument.
        exchange (str): Exchange where instrument is traded.
        asset (str): Asset class.
        symbol (str): Trading symbol.
        product (Optional[str]): Product type (e.g., MIS, CNC).
        order_side (Optional[str]): Order side (BUY/SELL).
        quantity (Optional[int]): Quantity in the position.
        last_traded_price (Optional[float]): LTP (aliased from `ltp`).
        avg_price (Optional[float]): Average price.
        avg_buy_price (Optional[float]): Average buy price.
        avg_sell_price (Optional[float]): Average sell price.
        pnl (Optional[float]): Current profit/loss.
        pnl_chg (Optional[float]): Change in PnL.
    """
    ref_id: Optional[int]
    nubra_name: str= Field(alias= "zanskar_name")
    display_name: Optional[str] = None
    derivative_type: Optional[str] = None
    strike_price: Optional[int]= None
    lot_size: Optional[int]= None
    exchange: str
    asset: str
    symbol: str
    asset_type: Optional[str] = None
    delivery_type: Optional[str] = None
    order_side: Optional[str]= None
    status: Optional[str] = None
    buy_quantity: Optional[int] = Field(default= None, alias= "buy_qty")
    sell_quantity: Optional[int] = Field(default= None, alias= "sell_qty")
    net_quantity: Optional[int] = Field(default= None, alias= "net_qty")
    last_traded_price: Optional[int] = Field(alias= "ltp")
    avg_buy_price: Optional[int]= None
    avg_sell_price: Optional[int]= None
    pnl: Optional[int]= None
    pnl_chg: Optional[float]= None

    model_config = ConfigDict(
        from_attributes=True,     
        populate_by_name=True, 
        ser_json_exclude_none= True,
        ser_dict_exclude_none= True       
    )



class PortfolioV2(BaseModel):
    client_code: str
    position_stats: PositionStatsV2
    positions: Optional[List[PositionStructV2]] = Field(default_factory=list)
    

class Portfolio(BaseModel):
    """
    Represents the full position portfolio grouped by instrument type.

    Attributes:
        client_code (str): Unique client code.
        position_stats (PositionStats): Overall position summary.
        stock_positions (List[PositionStruct]): Positions in equities.
        fut_positions (List[PositionStruct]): Futures positions.
        opt_positions (List[PositionStruct]): Options positions.
        close_positions (List[PositionStruct]): Recently closed positions.
    """
    client_code: str
    position_stats: PositionStats
    stock_positions: Optional[List[PositionStruct]] = Field(default_factory=list)
    fut_positions: Optional[List[PositionStruct]] = Field(default_factory=list)
    opt_positions: Optional[List[PositionStruct]] = Field(default_factory=list)
    close_positions: Optional[List[PositionStruct]] = Field(default_factory=list)

    @field_validator(
        "stock_positions", "fut_positions", "opt_positions", "close_positions",
        mode="before"
    )
    @classmethod
    def ensure_list(cls, value: Any) -> Any:
        if value is None:
            return []
        return value
    
    model_config = ConfigDict(
        from_attributes=True,     
        populate_by_name=True, 
        ser_json_exclude_none= True,
        ser_dict_exclude_none= True       
    )

class PortfolioMessage(BaseModel):
    """
    Message wrapper for position portfolio response.

    Attributes:
        message (str): Identifier message (e.g., "positions").
        portfolio (Portfolio): Portfolio data.
    """
    message: str
    portfolio: Optional[Portfolio]= None

    model_config = ConfigDict(
        from_attributes=True,     
        populate_by_name=True, 
        ser_json_exclude_none= True,
        ser_dict_exclude_none= True       
    )
class PortfolioMessageV2(BaseModel):
    """
    Message wrapper for position portfolio response.

    Attributes:
        message (str): Identifier message (e.g., "positions").
        portfolio (Portfolio): Portfolio data.
    """
    message: str
    portfolio: Optional[PortfolioV2]= None

    model_config = ConfigDict(
        from_attributes=True,     
        populate_by_name=True, 
        ser_json_exclude_none= True,
        ser_dict_exclude_none= True       
    )



#PFM
class PFMStruct(BaseModel):
    """
    Represents user's fund and margin details for trading.

    Attributes:
        client_code (str): Unique client identifier.
        start_of_day_funds (Optional[float]): Available cash at day start.
        pay_in_credit (Optional[float]): Amount credited via pay-in.
        pay_out_debit (Optional[float]): Amount debited via pay-out.
        net_derivative_prem_buy (Optional[float]): Premium paid for options.
        net_derivative_prem_sell (Optional[float]): Premium received.
        net_derivative_prem (Optional[float]): Net premium.
        cash_blocked_cnc_traded (Optional[float]): Cash blocked for CNC traded.
        cash_blocked_cnc_open (Optional[float]): Cash blocked for open CNC.
        cash_blocked_deriv_open (Optional[float]): Cash blocked for derivatives.
        cash_cnc_traded_and_open (Optional[float]): Cash for CNC (open + traded).
        mtm_deriv (Optional[float]): MTM value for derivatives.
        mtm_eq_iday_cnc (Optional[float]): MTM value for intraday equities.
        mtm_eq_delivery (Optional[float]): MTM for delivery-based trades.
        net_trading_amount (Optional[float]): Net value available for trading.
        net_withdrawal_amount (Optional[float]): Net amount available for withdrawal.
        total_payin_cash (Optional[float]): Total cash received via pay-in.
        start_of_day_collateral (Optional[float]): Collateral value at day start.
        iday_collateral_pledge (Optional[float]): Intraday pledged collateral.
        iday_collateral_pledge_sell (Optional[float]): Intraday collateral from sell.
        total_collateral (Optional[float]): Total collateral available.
        margin_used_deriv_traded (Optional[float]): Margin used in traded derivatives.
        margin_block_deriv_open_order (Optional[float]): Margin blocked for open orders.
        margin_used_eq_iday (Optional[float]): Margin used for intraday equity.
        margin_blocked_eq_iday_open (Optional[float]): Margin blocked for open intraday orders.
        net_margin_available (Optional[float]): Margin currently available.
        total_margin_blocked (Optional[float]): Total margin blocked.
    """
    client_code: str
    start_of_day_funds: Optional[int] = None
    pay_in_credit: Optional[int]= None
    pay_out_debit: Optional[int] = None
    net_derivative_prem_buy: Optional[int]= None
    net_derivative_prem_sell: Optional[int] = None
    net_derivative_prem: Optional[int]= None
    cash_blocked_cnc_traded: Optional[int] = None
    cash_blocked_cnc_open: Optional[int]= None
    cash_blocked_deriv_open: Optional[int]= None
    cash_cnc_traded_and_open: Optional[int]= None
    mtm_deriv: Optional[int]= None
    mtm_eq_iday_cnc: Optional[int]= None
    mtm_eq_delivery: Optional[int]= None
    net_trading_amount: Optional[int]= None
    net_withdrawal_amount: Optional[int]= None
    total_payin_cash: Optional[int]=None
    start_of_day_collateral: Optional[int]= None
    iday_collateral_pledge: Optional[int]= None
    iday_collateral_pledge_sell: Optional[int]= None
    total_collateral: Optional[int] = None
    margin_used_deriv_traded: Optional[int] = None
    margin_block_deriv_open_order: Optional[int] = None
    margin_used_eq_iday: Optional[int]= None
    margin_blocked_eq_iday_open: Optional[int]= None
    net_margin_available: Optional[int]= None
    total_margin_blocked: Optional[int]= None
    derivative_margin_blocked: Optional[int] = None
    brokerage: Optional[int] = None
        
    model_config = ConfigDict(
        from_attributes=True,     
        populate_by_name=True, 
        ser_json_exclude_none= True,
        ser_dict_exclude_none= True       
    )


class PFMMessage(BaseModel):
    """
    Message wrapper for funds and margin (PFM) response.

    Attributes:
        message (str): Message identifier (e.g., "pfm").
        port_funds_and_margin (PFMStruct): User's funds and margin details.
    """
    message: str
    port_funds_and_margin: Optional[PFMStruct] = None

    model_config = ConfigDict(
        from_attributes=True,     
        populate_by_name=True, 
        ser_json_exclude_none= True,
        ser_dict_exclude_none= True       
    )



