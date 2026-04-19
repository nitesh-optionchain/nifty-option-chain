
#src/nubra_python_sdk/trading/trading_data.py
import os
import json

from datetime import datetime
from typing import Union, List, Optional

import pandas as pd # type: ignore
import requests # type: ignore
from pydantic import ValidationError # type: ignore


from nubra_python_sdk.start_sdk import InitNubraSdk
from nubra_python_sdk.interceptor.htttpclient import BaseHttpClient
from nubra_python_sdk.interceptor.errors import NubraValidationError
from nubra_python_sdk.trading.validation import (
    MarginRequest,
    MarginResponse,
    CreateOrderV2, 
    CreateOrderResponseV2, 
    MultiOrderV2, 
    BasketOrderV2, 
    BasketOrderResponseV2, 
    ModOrderRequestV2, 
    ModBasketRequestV2,
    MarginRequired, 
    CancelRequestV2,
    GetAllOrdersV2, 
    GetAllExecutions,
    MultiOrderResponseV2, 
    GetBasketV2, 
    GetBasketResponseV2, 
    BasketList, 
    GetOrderResponseV2,
    )
from nubra_python_sdk.trading.trading_enum import ExchangeEnum, TradingAPIVersion
import logging
logger= logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())
print = lambda *args, **kwargs: None





class NubraTrader(InitNubraSdk):
    """
    Fetches real-time, trading data from Nubra.
    """

    def __init__(self, client: InitNubraSdk, version: Optional[TradingAPIVersion] = None):
        """
        Initializes the Trading Data instance using the provided Nubra SDK client.

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
 
    def create_order(self, orders: Union[List[dict], dict]):
        """
        Place single order.

        It serializes the input and sends a POST request to the order creation endpoint.

        Args:
            orders: Single order to be placed.

        Returns:
            CreateOrderWrapper: A wrapped response containing a list of order confirmation data.
            dict: Error message(s) in case of validation failure.
        
        Raises:
            NubraValidationError: If response deserialization fails due to invalid format.

        Example:
            >>> create_order({
            ...    "ref_id": 12345,
            ...    "request_type": "ORDER_REQUEST_NEW",
            ...    "order_type": "ORDER_TYPE_MARKET",
            ...    "order_qty": 1,
            ...    "order_price": 12,// in Rupees
            ...    "order_side": "ORDER_SIDE_BUY",
            ...    "order_delivery_type":"ORDER_DELIVERY_TYPE_IDAY",
            ...    "execution_type": "STRATEGY_TYPE_MARKET"
            ...    }
        """

        try:
            orders= CreateOrderV2(**orders)
        except ValidationError as ve:
            raise NubraValidationError(ve.errors())
        
        payload= orders.model_dump(by_alias= True)
        try:
            response= self.client.request("post", self._url("orders/v2/single"), json= payload)
            return CreateOrderResponseV2(**response.json())
        except ValidationError as ve:
            raise NubraValidationError(ve.errors())
        
        
    def get_flexi_order(self, tag: Optional[str]= None):
        path= "orders/v2/basket"
        if tag:
            path+=f"?tag={tag}"
        try:
            response= self.client.request("get", self._url(path=path))
            return BasketList(response.json())
        except ValidationError as ve:
            raise NubraValidationError(ve.errors())
        
        
    def get_order(self, order_id : int):
        path = f"orders/v2/{order_id}"
        try:
            response = self.client.request("get", self._url(path=path))
            return GetOrderResponseV2(**response.json())
        except ValidationError as ve:
            raise NubraValidationError(ve.errors())


    def multi_order(self, orders: Union[List[dict], dict]):
        """
        Place a basket of orders as a single atomic request.

        This method accepts a batch of orders and submits them together to the basket
        order endpoint. The input can be a single order dictionary, a list of order 
        dictionaries, or a list of validated `CreateOrder` Pydantic model instances.

        Args:
            orders (Union[List[dict], dict]): 
                A single order or multiple orders to be submitted in a basket.
                Each order must include fields such as `ref_id`, `order_type`, 
                `order_price`, `order_qty`, `order_side`, etc.

        Returns:
            BasketOrderWrapper: A parsed Pydantic response model containing basket-level 
                                details and individual order execution statuses.

            dict: An error dictionary if the input validation fails at the request level.

        Raises:
            NubraValidationError: If the HTTP response is valid JSON but fails to match
                                  the expected `BasketOrderWrapper` model schema.

        Example:
            >>> basket_order([
            ...     {
            ...         "ref_id": 12345,
            ...         "request_type": "ORDER_REQUEST_NEW",
            ...         "order_type": "ORDER_TYPE_LIMIT",
            ...         "order_qty": 1,
            ...         "order_price": 720, //in Rupees
            ...         "order_side": "ORDER_SIDE_BUY",
            ...         "order_delivery_type": "ORDER_DELIVERY_TYPE_IDAY",
            ...         "execution_type": "STRATEGY_TYPE_LIMIT"
            ...     },
            ...     {
            ...         "ref_id": 12346,
            ...         "request_type": "ORDER_REQUEST_NEW",
            ...         "order_type": "ORDER_TYPE_LIMIT",
            ...         "order_qty": 1,
            ...         "order_price": 650, // in Rupees
            ...         "order_side": "ORDER_SIDE_BUY",
            ...         "order_delivery_type": "ORDER_DELIVERY_TYPE_CNC",
            ...         "execution_type": "STRATEGY_TYPE_LIMIT"
            ...     }
            ... ])
        """

        if isinstance(orders, dict):
            try:
                orders= [CreateOrderV2(**orders)]
            except ValidationError as ve:
                raise NubraValidationError(ve.errors())
        elif isinstance(orders, list) and orders and isinstance(orders[0], dict):
            try:
                orders= [CreateOrderV2(**item) for item in orders]
            except ValidationError as ve:
                raise NubraValidationError(ve.errors())
        try:
            payload= {
                "orders": [ts.model_dump(by_alias= True) for ts in orders]
            }
            response= self.client.request("post", self._url("orders/v2/multi"), json= payload)
            return MultiOrderResponseV2(**response.json())
        except ValidationError as ve:
            raise NubraValidationError(ve.errors())           


    def flexi_order(self, order: dict):
        try:
            order= BasketOrderV2(**order)
        except ValidationError as ve:
            raise NubraValidationError(ve.errors())
        
        payload= order.model_dump(by_alias= True)
        try:
            response= self.client.request("post", self._url("orders/v2/basket"), json= payload)
            decoder = json.JSONDecoder()
            data, _ = decoder.raw_decode(response.text)
            return GetBasketV2(**data)
        except ValidationError as ve:
            raise NubraValidationError(ve.errors())


    def modify_order_v2(self, order_id: int, request: dict):
        try:
            request= ModOrderRequestV2(**request)
        except ValidationError as ve:
            raise NubraValidationError(ve.errors())
        
        payload= request.model_dump(by_alias= True)
        try:
            response= self.client.request("post", self._url(f"orders/v2/modify/{str(order_id)}"), json= payload)
            return response.json()
        except ValidationError as ve:
            raise NubraValidationError(ve.errors())
        
    def mod_flexi_order(self, basket_id: int,  request: dict):
        try:
            request= ModBasketRequestV2(**request)
        except ValidationError as ve:
            raise NubraValidationError(ve.errors())
        payload= request.model_dump(by_alias= True)
        try:
            response= self.client.request("put", self._url(f"orders/v2/basket/{str(basket_id)}"), json= payload)
            return response.json()
        except ValidationError as ve:
            raise NubraValidationError(ve.errors())
    

    def cancel_orders(self, order_ids: List[int]):
        """
        Cancel multiple orders at once.

        Args:
            order_ids (List[int]): A list of order IDs to cancel.

        Returns:
            dict: Response from the API after order cancellations.
        """

        payload = {
            "orders": [{"order_id": oid} for oid in order_ids]
        }
        path=f"orders/cancel"
        try:
            response= self.client.request("post", self._url(path), json= payload)
            return response.json()
        except ValidationError as ve:
            raise NubraValidationError(ve.errors())
        
        
    def cancel_orders_v2(self, basket_ids : Optional[List[int]] = None, order_ids : Optional[List[int]] = None):
        path = "orders/v2/cancelV2"
        payload = {
            "baskets" : basket_ids,
            "orders" : [{"order_id": oid} for oid in order_ids if oid is not None]
        }
        try:
            response = self.client.request("post", self._url(path=path), json = payload)
            return response.json()
        except ValidationError as ve:
            raise NubraValidationError(ve.errors())
        
    
    def orders(self, live: bool = False, executed: bool = False, tag: Optional[str]= None):
        """
        Retrieve all orders placed by the user.

        Returns:
            GetAllOrder: A list of all orders wrapped in a Pydantic model.
            list: An empty list if no orders are found.

        Raises:
            NubraValidationError: If response is invalid or cannot be parsed.
        """
            
        path= "orders/v2"
        if live and executed:
            raise NubraValidationError("Only one request parameter can be True")
        if tag:
            path+=f"?tag={tag}"
            if live:
                path+="&live=1"
            if executed:
                path+="&executed=1"
        else:
            if live:
                path+="?live=1"
            if executed:
                path+="?executed=1"
        try:
            response = self.client.request("get", self._url(path))
            if response.json() is None:
                return []
            return GetAllOrdersV2(response.json())
        except ValidationError as ve:
            raise NubraValidationError(ve.errors())
    
    def execute(self):
        path = "orders/v2/executions"
        try:
            response = self.client.request("get", self._url(path))
            response.raise_for_status()

            data = response.json()
            if not data:
                return []
            return GetAllExecutions(data)
        
        except ValidationError as ve:
            raise NubraValidationError(ve.errors())

        except Exception as e:
            raise NubraValidationError(str(e))

    def cancel_order_by_id(self, order_id: int):
        """
        Cancel a specific order by its ID.

        Args:
            order_id (int): The ID of the order to cancel.

        Returns:
            dict: Response from the API, or an error message if an exception occurs.
        """
        order_id= str(order_id)
        path= f"orders/{order_id}"
        try:
            response= self.client.request("delete", self._url(path))
            return response.json()
        except Exception as e:
            return {"msg": f"Exception: {e}"}
        
    def cancel_flexi_order(self, basked_id: int, exchange: ExchangeEnum):
        basked_id= str(basked_id)
        path= f"orders/v2/basket/{basked_id}"
        payload= {
            "exchange": exchange
        }
        try:
            response= self.client.request("post", self._url(path), json= payload)
            return response.json()
        except Exception as e:
            return {"msg": f"Exception: {e}"}
            

    def get_margin(self, request: dict):
        """
        Calculate the margin required for a set of trading orders.

        This method validates the input request using the `MarginRequest` Pydantic model,
        converts it into the expected payload format. If the response is valid, 
        it returns a `MarginResponse` object containing various margin components like 
        SPAN, exposure, delivery margin, etc.

        Parameters:
            request (dict): A dictionary representing the margin request, expected to 
                            conform to the `MarginRequest` model structure. It must 
                            include order details such as `ref_id`, `order_type`, 
                            `order_side`, `order_qty`, and optionally `order_price`.

        Returns:
            MarginResponse: A validated Pydantic model containing detailed margin 
                            requirements including SPAN, exposure, total margin, 
                            delivery margin, and per-leg breakdowns.

        Raises:
            NubraValidationError: If the response from the margin API cannot be parsed 
                                into a valid `MarginResponse` model.
        
        Example:
            >>> margin_required({
            ...     "with_portfolio": True,
            ...     "order_req": [{
            ...         "ref_id": 72329,
            ...         "request_type": "margin",
            ...         "order_type": "LIMIT",
            ...         "order_delivery_type": "INTRADAY",
            ...         "order_qty": 1,
            ...         "order_price": 123.45,
            ...         "order_side": "BUY",
            ...         "execution_type": "REGULAR"
            ...     }]
            ... })
        """    
        
        try: 
            request= MarginRequired(**request)
        except ValidationError as ve:
            raise NubraValidationError(ve.errors())
        
        payload= request.model_dump(by_alias= True)
        try:
            response= self.client.request("post", self._url("orders/v2/margin_required"), json= payload)
            return MarginResponse(**response.json())
        except ValidationError as ve:
            raise NubraValidationError(ve.errors())
        

