#src/nubra_python_sdk/portfolio/portfolio_data.py
import os
import json

from datetime import datetime
from typing import Union, List, Optional

import pandas as pd # type: ignore
from pydantic import ValidationError # type: ignore


from nubra_python_sdk.start_sdk import InitNubraSdk
from nubra_python_sdk.interceptor.htttpclient import BaseHttpClient
from nubra_python_sdk.interceptor.errors import NubraValidationError
from nubra_python_sdk.portfolio.validation import (
    HoldingsMessage,
    PortfolioMessage,
    PortfolioMessageV2,
    PFMMessage
    )

import logging
logger= logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())
print = lambda *args, **kwargs: None


class NubraPortfolio(InitNubraSdk):
    """
    Fetches real-time, trading data from Nubra.
    """

    def __init__(self, client: InitNubraSdk):
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
    
    def positions(self, version= None):
        """
        Fetches the current portfolio positions for the logged-in user.

        It returns a structured response containing current stock, futures, options,
        and closed positions, along with profit and loss (PnL) statistics.

        Returns:
            PortfolioMessage: A Pydantic model containing a message and a detailed portfolio breakdown,
            including realized/unrealized PnL and categorized positions (stocks, futures, options, closed).

        Raises:
            NubraValidationError: If the response fails to validate against the expected data schema.
        """

        try:
            if version is None or version == "V1":
                response= self.client.request("get", self._url("portfolio/positions"))
                if response.json() is None:
                    return []
                return PortfolioMessage(**response.json())
            elif version =="V2":
                response= self.client.request("get", self._url("portfolio/v2/positions"))
                if response.json() is None:
                    return []
                return PortfolioMessageV2(**response.json())
            else:
                return {"message": f"Only version V1 or V2 supported."}
        except ValidationError as ve:
            raise NubraValidationError(ve.errors())
        
    def holdings(self):
        """
        Fetches the current equity holdings for the logged-in user.

        It includes per-asset information such as quantity, average price, pledged quantity, current value, PnL, and 
        margin benefit.

        Returns:
            HoldingsMessage: A Pydantic model containing a message and a detailed portfolio with
            holding statistics (`HoldingStats`) and a list of current equity holdings (`Holding`).

        Raises:
            NubraValidationError: If the response data fails validation against the `HoldingsMessage` schema.
        """
        try:
            response= self.client.request("get",self._url("portfolio/holdings"))
            if response.json() is None:
                return []
            return HoldingsMessage(**response.json())
        except ValidationError as ve:
            raise NubraValidationError(ve.errors())
        
    def funds(self):
        """
        Retrieves the user's funds and margin details from the portfolio.

        Returns a structured response containing a detailed breakdown of available funds, 
        collateral, pay-in/pay-out amounts, margin usage, and MTM (Mark to Market) values.

        Returns:
            PFMMessage: A Pydantic model containing a `message` string and a detailed `PFMStruct` 
            object that includes all user funds and margin information.

        Raises:
            NubraValidationError: If the response data does not conform to the expected schema 
            defined by the `PFMMessage` Pydantic model.
        """
        try:
            response= self.client.request("get",self._url("portfolio/user_funds_and_margin"))
            if response.json() is None:
                return []
            return PFMMessage(**response.json())
        except ValidationError as ve:
            raise NubraValidationError(ve.errors())

            
        