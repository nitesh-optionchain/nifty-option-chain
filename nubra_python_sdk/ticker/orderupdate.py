#src/nubra_python_sdk/ticker/orderupdate.py
import asyncio
import aiohttp # type: ignore
import threading
import queue
import json
import traceback
import time
import logging
import math
from typing import Callable, List, Optional, Dict, Tuple, Set
from google.protobuf.any_pb2 import Any  # type: ignore
from google.protobuf.json_format import MessageToDict  # type: ignore
from nubra_python_sdk.trading.trading_enum import ExchangeEnum, TradingAPIVersion
from nubra_python_sdk.ticker.validation import (
    OrderInfoWrapper,
    AckInfoWrapper,
    BasketWrapper,
    ExecutionInfoWrapper, 
    PortfolioResponse, 
    PositionStats, 
    PositionStruct, 
    Holding, 
    HoldingsResponse, 
    HoldingStats, 
    PositionsResponse
)
from nubra_python_sdk.start_sdk import InitNubraSdk
from nubra_python_sdk.protos import market_pb2
from nubra_python_sdk.protos import nubrafrontend_pb2

logger= logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())

class OrderUpdate:
    """
    Real-time WebSocket client for streaming market data using the Nubra SDK.

    This class manages an asynchronous WebSocket connection to receive order updates.
    It supports automatic reconnection.

    The WebSocket client runs in a dedicated background thread with its own asyncio
    event loop to enable low-latency, non-blocking data handling in real-time systems.

    Typical usage:
    --------------
    >>> socket = OrderUpdate(client, on_order_update=on_order_update)
    >>> socket.connect()
    """
    EXCHANGE_MAP={
        1: "EXCH_NSE", 
        2: "EXCH_BSE"
    }

    ORDERSIDE_MAP= {
        1: "ORDER_SIDE_BUY", 
        2: "ORDER_SIDE_SELL"
    }

    ORDERDELIVERY_TYPE_MAP={
        1: "ORDER_DELIVERY_TYPE_CNC", 
        2: "ORDER_DELIVERY_TYPE_IDAY"
    }
    def __init__(
        self,
        client: InitNubraSdk,
        on_error: Optional[Callable[[str], None]] = None,
        on_close: Optional[Callable[[str], None]] = None,
        on_connect: Optional[Callable[[str], None]] = None,
        on_order_update: Optional[Callable[[dict], None]] = None,
        on_trade_update: Optional[Callable[[dict], None]] = None,
        on_portfolio_update: Optional[Callable[[dict], None]] = None,
        reconnect: bool = True,
        logger: Optional[logging.Logger] = None,
    ):
        

        """
        Initializes a NubraDataSocket instance for real-time market data streaming.

        Parameters
        ----------
        client : InitNubraSdk
            The initialized Nubra SDK client providing authentication, WebSocket URL, and config.
        on_error : Callable[[str], None], optional
            Callback when an internal or connection-related error occurs.

        on_close : Callable[[str], None], optional
            Callback when the WebSocket connection closes.

        on_connect : Callable[[str], None], optional
            Callback upon successful WebSocket connection.

        on_order_update : Callable[[dict], None], optional
            Callback for live order state changes (used in trading mode).

        on_trade_update : Callable[[dict], None], optional
            Callback for trade execution updates (used in trading mode).

        reconnect : bool, default=True
            Whether to automatically reconnect if the connection drops

        logger : logging.Logger, optional
            Optional logger. If not provided, defaults to logger named "NubraDataSocket".
        """
        self.client = client
        self.bt = self.client.BEARER_TOKEN
        self.url = client.WEBSOCKET_URL
        self.api_base_url = client.API_BASE_URL
        self.db_path = client.db_path
        self.totp_login = client.totp_login
        self.token_data = client.token_data
        self.db_path = client.db_path
        self.env_path_login = client.env_path_login

        self.on_error = on_error
        self.on_close = on_close
        self.on_connect = on_connect
        self.on_order_update = on_order_update
        self.on_trade_update = on_trade_update
        self.on_portfolio_update = on_portfolio_update

        self.main_order_queue = queue.Queue()
        self.reconnect = reconnect
        self.logger = logger or logging.getLogger("NubraDataSocket")

        self.ws = None
        self.session = None

        self.keep_alive = True
        self.connected = False

        self._connect_lock = asyncio.Lock()
        self._token_refresh_lock = asyncio.Lock()
        self.ping_task = None
        self.version = None

        # Create a new event loop for the thread
        self.loop = asyncio.new_event_loop()
        self._thread = threading.Thread(target=self._start_loop, daemon=True)
        self._background_tasks: List[asyncio.Task] = []
        self._order_dispatch_thread = threading.Thread(target=self._dispatcher, daemon=True)
        self._order_dispatch_thread.start()


    def _start_loop(self):
        asyncio.set_event_loop(self.loop)
        self.session = aiohttp.ClientSession(loop=self.loop)
        # Start the subscription sender loop as a task
        self.loop.run_until_complete(self._connect())


    def connect(self, version = TradingAPIVersion.V1):
        self.version = version
        self._thread.start()

    def keep_running(self):
        """
        Keeps the main thread alive. Intended to be run in foreground scripts
        to prevent the main thread from exiting.
        """
        while self.keep_alive:
                time.sleep(1)

    def _dispatcher(self):
        """
        Continuously processes messages from the internal order queue and dispatches them
        to either trade or order callbacks based on trade quantity.
        """
        while self.keep_alive:
            try:
                order = self.main_order_queue.get()

                if self.version == TradingAPIVersion.V1:
                    status = getattr(order, "order_status", None)
                    trade_qty = getattr(order, "trade_qty", None)

                    if trade_qty and isinstance(order, AckInfoWrapper):
                        if callable(self.on_trade_update):
                            try:
                                self.on_trade_update(order)
                            except Exception as cb_err:
                                self._handle_error(f"Error in on_trade_update callback: {cb_err}, order={order}")

                    elif not trade_qty and isinstance(order, OrderInfoWrapper): 
                        if callable(self.on_order_update):
                            try:
                                self.on_order_update(order)
                            except Exception as cb_err:
                                self._handle_error(f"Error in on_order_update callback: {cb_err}, order={order}")

                if self.version == TradingAPIVersion.V2:
                    execution_type = getattr(order, "execution_type", None)
                    if execution_type == "EXECUTION_TYPE_FLEXI":
                        basket_params = getattr(order, "basket_params", None)
                        order_params = list(getattr(basket_params, "order_params", None))
                        for order_param in order_params:
                            trade_qty = getattr(order_param, "trade_qty", None)
                            if trade_qty:
                                break
                        # print(trade_qty)
                    else:
                        order_params = getattr(order, "order_params", None)
                        trade_qty = getattr(order_params, "trade_qty", None)

                    
                    if trade_qty and isinstance(order, ExecutionInfoWrapper):
                        if callable(self.on_trade_update):
                            try:
                                self.on_trade_update(order)
                            except Exception as cb_err:
                                self._handle_error(f"Error in on_trade_update callback: {cb_err}, order={order}")

                    elif not trade_qty and isinstance(order, ExecutionInfoWrapper): 
                        if callable(self.on_order_update):
                            try:
                                self.on_order_update(order)
                            except Exception as cb_err:
                                self._handle_error(f"Error in on_order_update callback: {cb_err}, order={order}")

            except queue.Empty:
                time.sleep(0.001)
                continue
            except Exception as e:
                if hasattr(self, "on_error") and callable(self.on_error):
                    try:
                        self.on_error(f"Error dispatching: {e}, order={order}")
                    except Exception as cb_err:
                        self._handle_error(f"Error : {cb_err}, order={order}")



    async def _connect(self):
        """
        Connects to the WebSocket and starts the ping loop and message receiving loop.
        Handles reconnect with exponential backoff
        """
        backoff = 1
        max_attempts = 30
        attempts = 0
        async with self._connect_lock:
            while self.keep_alive:
                try:                  
                    self.logger.info("Connecting to WebSocket...")
                    self.ws = await self.session.ws_connect(self.url, autoping=False)
                    self.connected = True
                    if self.ping_task:
                        self.ping_task.cancel()
                        self.ping_task= asyncio.create_task(self._ping_loop())
                    else:
                        self.ping_task= asyncio.create_task(self._ping_loop())

                    self.logger.info("✅ Connected to WebSocket.")
                    if self.on_connect:
                        self.on_connect("WebSocket Connected!")

                    msg = msg = f"subscribe {self.bt} notifications notification"
                    await self.ws.send_str(msg)
                    try:
                        await self._receive_loop()
                    except asyncio.CancelledError:
                        self.logger.info("Connect task cancelled, shutting down")
                        break
                    except Exception as e:
                        self.logger.error(f"Error in receive loop: {e}")

                    if not self.keep_alive:
                        break
                except asyncio.CancelledError:
                    self.logger.info("Connect cancelled during connection attempt")
                    if self.on_close:
                        self.on_close("WebSocket closed")
                    break
                except Exception as e:
                    attempts += 1
                    self.logger.warning(f"Connection failed: {str(e)}")
                    self._handle_error(f"Connection failed: {str(e)}")
                    self.connected = False
                    if self.on_close:
                        self.on_close("WebSocket closed")
                    if not self.reconnect or attempts >= max_attempts:
                        self._handle_error(f"Max reconnection attempts ({max_attempts}) reached")
                        break
                    await asyncio.sleep(backoff)
                    backoff = min(backoff * 2, 10)

    async def _receive_loop(self):
        """
        Continuously receives messages from the WebSocket and decodes them.
        Handles reconnect logic if connection is closed.
        """
        while self.keep_alive and self.connected:
            try:
                msg = await self.ws.receive()
                if msg.type == aiohttp.WSMsgType.BINARY:
                    decoded_msg = self._decode_protobuf(msg.data)
                elif msg.type == aiohttp.WSMsgType.TEXT:
                    data = msg.data.strip()

                    if data == "Invalid Token":
                        await self._handle_token_expiry()
                        break

                    elif "Error" in data or "Exception" in data or "Failed" in data:
                        self.logger.error(f"WebSocket error message received: {data}")
                        self._handle_error(data)
                    else:
                        self.logger.info(f"Text message received: {msg.data}")
                elif msg.type in (aiohttp.WSMsgType.CLOSED, aiohttp.WSMsgType.CLOSING, aiohttp.WSMsgType.CLOSE):
                    break
            except Exception as e:
                self._handle_error(f"Error in receive loop: {str(e)}")
                self.connected = False
                if self.on_close:
                    self.on_close("WebSocket closed")
                if self.reconnect and self.keep_alive:
                    self.logger.info("Attempting to reconnect...")
                    await self._connect()
                break

    async def _ping_loop(self):
        """Sends periodic pings to keep the connection alive."""
        try:
            while self.connected and self.keep_alive:
                try:
                    if self.ws is not None:
                        await self.ws.ping()  # send websocket ping
                        self.logger.debug("Ping sent")
                    await asyncio.sleep(20)  # ping interval
                except Exception as e:
                    self._handle_error(f"Ping failed: {e}")
                    self.logger.error(f"Ping failed: {e}")
        except asyncio.CancelledError:
            self.logger.info("Ping loop cancelled")

    def _decode_protobuf(self, raw: bytes):
        """
        Decodes raw protobuf messages from the WebSocket and dispatches them
        to appropriate callbacks.

        Args:
            raw (bytes): Raw binary message from WebSocket.
        """
        try:
            wrapper = Any()
            wrapper.ParseFromString(raw)
            inner = Any()
            inner.ParseFromString(wrapper.value)

            if self.version == TradingAPIVersion.V1:
                if inner.type_url.endswith("Order"):
                    msg = nubrafrontend_pb2.Order()
                    inner.Unpack(msg)
                    msg_dict = MessageToDict(msg, preserving_proto_field_name=True)
                    try:
                        if len(msg_dict)<5:
                            try:
                                basket_obj= BasketWrapper(**msg_dict)
                                if self.on_order_update:
                                    self.on_order_update(basket_obj)
                            except Exception as e:
                                if self.on_error:
                                    self.on_error(f"Exception occured: {e}")
                                traceback.print_exc()
                        else:
                            order_obj = OrderInfoWrapper(**msg_dict)
                            trade_obj= AckInfoWrapper(**msg_dict)
                            try:
                                self.main_order_queue.put(order_obj)
                            except queue.Full:
                                if self.on_error:
                                    self.on_error("Queue is full while putting OrderInfoWrapper")
                            try:
                                self.main_order_queue.put(trade_obj)
                            except queue.Full:
                                if self.on_error:
                                    self.on_error("Queue is full while putting AckInfoWrapper")
                    except Exception as e:
                        if self.on_error:
                            self.on_error(f"Exception occured : {e}")
                        traceback.print_exc()

            if self.version == TradingAPIVersion.V2:
                if inner.type_url.endswith("Executions"):
                    msg = nubrafrontend_pb2.Executions()
                    inner.Unpack(msg)
                    msg_dict = MessageToDict(msg, preserving_proto_field_name=True)
                    
                    try:
                        trade_obj = ExecutionInfoWrapper(**msg_dict)
                        try:
                            self.main_order_queue.put(trade_obj)
                        except queue.Full:
                            if self.on_error:
                                self.on_error("Queue is full while putting ExecutionInfoWrapper")
                    except Exception as e:
                        if self.on_error:
                            self.on_error(f"Exception occured : {e}")
                        traceback.print_exc()

            if inner.type_url.endswith("PortfolioResponse"):
                msg = nubrafrontend_pb2.PortfolioResponse()
                inner.Unpack(msg)
                try:
                    portfolio_obj = self.portfolio_from_proto(msg)

                    if self.on_portfolio_update:
                        self.on_portfolio_update(portfolio_obj)
                except Exception as e:
                    if self.on_error:
                        self.on_error(f"Exception occured: {e}")


        except Exception as e:
            if self.on_error:
                self.on_error(f"Error: {e}")
            self.logger.warning(f"Error: {e}")
        return None

    def portfolio_from_proto(self, proto_obj) -> PortfolioResponse:
        
        def holding_from_proto(h) -> Holding:
            return Holding(
                ref_id=h.ref_id if h.ref_id else None,
                zanskar_name=h.zanskar_name if h.zanskar_name else None,
                display_name=h.display_name if h.display_name else None,
                derivative_type=h.derivative_type if h.derivative_type else None,
                strike_price=h.strike_price if h.strike_price else None,
                lot_size=h.lot_size if h.lot_size else None,
                exchange=type(self).EXCHANGE_MAP.get(h.exchange, "EXCH_INVALID") if h.exchange else None,
                asset=h.asset if h.asset else None,
                symbol=h.symbol if h.symbol else None,
                qty=h.qty if h.qty else None,
                pledged_qty=h.pledged_qty if h.pledged_qty else None,
                t1_qty=h.t1_qty if h.t1_qty else None,
                avg_price=h.avg_price if h.avg_price else None,
                prev_close=h.prev_close if h.prev_close else None,
                ltp=h.ltp if h.ltp else None,
                ltp_chg=h.ltp_chg if h.ltp_chg else None,
                invested_value=h.invested_value if h.invested_value else None,
                current_value=h.current_value if h.current_value else None,
                net_pnl=h.net_pnl if h.net_pnl else None,
                net_pnl_chg=h.net_pnl_chg if h.net_pnl_chg else None,
                day_pnl=h.day_pnl if h.day_pnl else None,
                haircut=h.haircut if h.haircut else None,
                margin_benefit=h.margin_benefit if h.margin_benefit else None,
                available_to_pledge=h.available_to_pledge if h.available_to_pledge else None,
                supported_exchanges=dict(h.supported_exchanges) if h.supported_exchanges else None,
            )

        def holding_stats_from_proto(hs) -> HoldingStats:
            return HoldingStats(
                invested_amount=hs.invested_amount if hs.invested_amount else None,
                current_value=hs.current_value if hs.current_value else None,
                total_pnl=hs.total_pnl if hs.total_pnl else None,
                total_pnl_chg=hs.total_pnl_chg if hs.total_pnl_chg else None,
                day_pnl=hs.day_pnl if hs.day_pnl else None,
                day_pnl_chg=hs.day_pnl_chg if hs.day_pnl_chg else None,
            )

        def position_from_proto(p) -> PositionStruct:
            return PositionStruct(
                ref_id=p.ref_id if p.ref_id else None,
                zanskar_name=p.zanskar_name if p.zanskar_name else None,
                display_name=p.display_name if p.display_name else None,
                derivative_type=p.derivative_type if p.derivative_type else None,
                strike_price=p.strike_price if p.strike_price else None,
                lot_size=p.lot_size if p.lot_size else None,
                exchange=type(self).EXCHANGE_MAP.get(p.exchange, "EXCH_INVALID") if p.exchange else None,
                asset=p.asset if p.asset else None,
                symbol=p.symbol if p.symbol else None,
                order_delivery_type= type(self).ORDERDELIVERY_TYPE_MAP.get(p.order_delivery_type, "ORDER_DELIVERY_TYPE_INVALID") if p.order_delivery_type else None,
                order_side= type(self).ORDERSIDE_MAP.get(p.order_side, "ORDER_SIDE_INVALID") if p.order_side else None,
                qty=p.qty if p.qty else None,
                ltp=p.ltp if p.ltp else None,
                avg_price=p.avg_price if p.avg_price else None,
                avg_buy_price=p.avg_buy_price if p.avg_buy_price else None,
                avg_sell_price=p.avg_sell_price if p.avg_sell_price else None,
                pnl=p.pnl if p.pnl else None,
                pnl_chg=p.pnl_chg if p.pnl_chg else None,
            )

        def position_stats_from_proto(ps) -> PositionStats:
            return PositionStats(
                realised_pnl=ps.realised_pnl if ps.realised_pnl else None,
                unrealised_pnl=ps.unrealised_pnl if ps.unrealised_pnl else None,
                total_pnl=ps.total_pnl if ps.total_pnl else None,
                total_pnl_chg=ps.total_pnl_chg if ps.total_pnl_chg else None,
            )

        def holdings_response_from_proto(hr) -> HoldingsResponse:
            return HoldingsResponse(
                client_code=hr.client_code if hr.client_code else None,
                holding_stats=holding_stats_from_proto(hr.holding_stats) if hr.HasField("holding_stats") else None,
                holdings=[holding_from_proto(h) for h in hr.holdings] if hr.holdings else None,
            )

        def positions_response_from_proto(pr) -> PositionsResponse:
            return PositionsResponse(
                client_code=pr.client_code if pr.client_code else None,
                position_stats=position_stats_from_proto(pr.position_stats) if pr.HasField("position_stats") else None,
                stock_positions=[position_from_proto(p) for p in pr.stock_positions] if pr.stock_positions else None,
                fut_positions=[position_from_proto(p) for p in pr.fut_positions] if pr.fut_positions else None,
                opt_positions=[position_from_proto(p) for p in pr.opt_positions] if pr.opt_positions else None,
                close_positions=[position_from_proto(p) for p in pr.close_positions] if pr.close_positions else None,
            )

        return PortfolioResponse(
            position_response=positions_response_from_proto(proto_obj.position_response) if proto_obj.HasField("position_response") else None,
            holding_response=holdings_response_from_proto(proto_obj.holding_response) if proto_obj.HasField("holding_response") else None,
        )

    async def _send_subscribe(self, data_type: Optional[str]= None, symbol: Optional[str]= None, exchange: Optional[ExchangeEnum] = None, interval: Optional[str] = None):
        """
        Sends a subscription message to the WebSocket for a given stream and symbol.

        Args:
            data_type (str): Stream type ('index', 'option', or 'orderbook', 'index_bucket').
            symbol (str): Symbol to subscribe to.
        """
        try:
            if not self.connected or not self.ws or self.ws.closed:
                if self.on_error:
                    self.on_error(f"Cannot send subscription: WebSocket is not connected or closed")
                self.logger.warning(
                    f"Cannot send subscription: WebSocket is not connected or closed!"
                )
                return

            if exchange == ExchangeEnum.NSE or exchange is None:
                if data_type == "index":
                    msg = f"subscribe {self.bt} index {symbol}"
            await self.ws.send_str(msg)
        except Exception as e:
            self._handle_error(f"Failed to subscribe: data_type={data_type}, symbol={symbol}, error={e}")

    async def _handle_token_expiry(self):
        """
        Handles token expiry scenario by re-authenticating the client
        and reconnecting to the WebSocket.
        """
        self.logger.warning("Token expired. Re-authenticating...")
        async with self._token_refresh_lock:
            if not self.keep_alive:
                return
            try:
                self.client.auth_flow()
                self.bt = self.client.BEARER_TOKEN
                if not self.bt:
                    self._handle_error("Re-authentication failed. No token.")
                    self.keep_alive = False
                    return
                await self._connect()
            except Exception as e:
                self._handle_error(f"Failed to refresh token: {e}")
                self.keep_alive = False


    def _handle_error(self, message: str):
        """
        Logs the error and optionally invokes the `on_error` callback.

        Args:
            message (str): Error message.
        """
        self.logger.error(message)
        if self.on_error:
            self.on_error(message)


    def close(self):
        """
        Gracefully shuts down the WebSocket client by stopping the loop,
        canceling tasks, and closing the WebSocket connection.
        """
        self.keep_alive = False
        self.connected = False
        
        try:
            if self.ping_task:
                self.ping_task.cancel()
            if self.ws:
                try:
                    if hasattr(self.ws, '_closed'):
                        self.ws._closed = True
                    if hasattr(self.ws, '_close_code') and not self.ws._close_code:
                        self.ws._close_code = 1000
                except Exception:
                    pass
                self.ws = None
                
            if self.session:
                try:
                    self.session._closed = True
                    if hasattr(self.session, '_connector') and self.session._connector:
                        connector = self.session._connector
                        if hasattr(connector, '_conns'):
                            connector._conns.clear()
                except Exception:
                    pass
                self.session = None
            # Wait for threads
            if self._thread:
                self._thread.join(timeout=2.0)
            if self._order_dispatch_thread:
                self._order_dispatch_thread.join(timeout=2.0)
                
            if self.on_close:
                self.on_close("WebSocket closed")
                
        except Exception as e:
            self._handle_error(f"Error during shutdown: {repr(e)}")


