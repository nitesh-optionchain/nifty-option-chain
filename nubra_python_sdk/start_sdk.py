import os, glob, shelve, requests, sys
import pandas as pd
import numpy as np
from enum import Enum
from typing import Dict
from dotenv import load_dotenv

from nubra_python_sdk.validation import InstrumentData, VersionEnum

SDK_VERSION = "0-4-0"


# ==========================
# ENV ENUM
# ==========================
class NubraEnv(str, Enum):
    DEV = "DEV"
    STAGING = "STAGING"
    PROD = "PROD"
    UAT = "UAT"


# ==========================
# SAFE SECRET HELPER
# ==========================
def safe_get_secret(key: str):
    try:
        import streamlit as st
        return st.secrets.get(key)
    except:
        return None


# ==========================
# INIT SDK CLASS
# ==========================
class InitNubraSdk:

    REF_ID_MAP: Dict[int, InstrumentData] = {}
    SYMBOL_MAP: Dict[str, InstrumentData] = {}
    NUBRA_MAP: Dict[str, InstrumentData] = {}

    TOKEN_STORE = "auth_data.db"
    HEADERS = {"Content-Type": "application/json"}

    BEARER_TOKEN = None
    FLAG = {"value": False}

    VERSION_URL = "https://test.pypi.org/pypi/nubra-sdk/json"
    VERSION = SDK_VERSION.replace("-", ".")

    # ==========================
    # INIT
    # ==========================
    def __init__(self, env: NubraEnv, totp_login=False, env_creds=False, insti_login=False):

        if env == NubraEnv.DEV:
            self.API_BASE_URL = "https://nubra-dev1.zanskar.xyz/api"
        elif env == NubraEnv.STAGING:
            self.API_BASE_URL = "https://nubra-staging.zanskar.xyz/api"
        elif env == NubraEnv.PROD:
            self.API_BASE_URL = "https://api.nubra.io"
        elif env == NubraEnv.UAT:
            self.API_BASE_URL = "https://uatapi.nubra.io"
        else:
            raise ValueError("Invalid ENV")

        self.WEBSOCKET_URL = ""
        self.WEBSOCKET_URL_BATCH = ""

        self.totp_login = totp_login
        self.insti_login = insti_login

        self.__phone_number = None
        self.__mpin = None

        self.client_code = None
        self.exchange_client_code = None
        self.username = None
        self.password = None

        self.token_data = {}
        self.db_path = self.TOKEN_STORE
        self.env_path_login = env_creds

        # ==========================
        # LOAD ENV
        # ==========================
        if self.env_path_login:
            self.load_env_variables()

        # ==========================
        # SAFE INIT BLOCK (FIXED)
        # ==========================
        if not type(self).FLAG["value"]:
            try:
                self.auth_flow()
                self.__refresh_ref_data()
                self.__get_user_info()
                type(self).FLAG["value"] = True
            except Exception as e:
                print("SDK INIT FAILED:", e)
                raise

    # ==========================
    # ENV LOADER (FIXED)
    # ==========================
    def load_env_variables(self):
        try:
            load_dotenv()

            self.__phone_number = safe_get_secret("PHONE_NO")
            self.__mpin = safe_get_secret("MPIN")

            self.client_code = os.getenv("CLIENT_CODE")
            self.exchange_client_code = os.getenv("EXCHANGE_CLIENT_CODE")
            self.username = os.getenv("USERNAME")
            self.password = os.getenv("PASSWORD")

            missing = []

            if not self.insti_login:
                if not self.__phone_number:
                    missing.append("PHONE_NO")

            if not self.__mpin:
                missing.append("MPIN")

            if self.insti_login:
                if not self.client_code:
                    missing.append("CLIENT_CODE")
                if not self.exchange_client_code:
                    missing.append("EXCHANGE_CLIENT_CODE")
                if not self.username:
                    missing.append("USERNAME")
                if not self.password:
                    missing.append("PASSWORD")

            if missing:
                print("⚠️ Missing ENV:", missing)

            return True

        except Exception as e:
            print("ENV LOAD FAILED:", e)
            return False

    # ==========================
    # TOKEN LOAD
    # ==========================
    def __load_tokens(self):
        try:
            with shelve.open(self.db_path, flag='c') as db:
                self.token_data = {
                    "auth_token": db.get("auth_token"),
                    "session_token": db.get("session_token"),
                    "x-device-id": db.get("x-device-id"),
                }
        except Exception as e:
            print("Token load failed:", e)
            self.token_data = {}

    # ==========================
    # TOKEN SAVE
    # ==========================
    def __save_tokens(self, auth_token=None, session_token=None, x_device_id=None):
        try:
            with shelve.open(self.db_path, flag='c') as db:
                if auth_token:
                    db["auth_token"] = auth_token
                if session_token:
                    db["session_token"] = session_token
                if x_device_id:
                    db["x-device-id"] = x_device_id
                db.sync()
        except Exception as e:
            print("Token save failed:", e)

    # ==========================
    # REFRESH DATA (SAFE)
    # ==========================
    def __refresh_ref_data(self):
        self.__load_tokens()

    # ==========================
    # USER INFO
    # ==========================
    def __get_user_info(self):
        try:
            url = f"{self.API_BASE_URL}/userinfo"
            res = requests.get(url, headers=self.HEADERS)
            if res.status_code == 200:
                data = res.json()

                env_info = data.get("env_info", {})
                self.WEBSOCKET_URL = env_info.get("user_ws_url", self.WEBSOCKET_URL)
                self.WEBSOCKET_URL_BATCH = env_info.get("market_ws_url", self.WEBSOCKET_URL_BATCH)

        except Exception as e:
            print("User info error:", e)

    # ==========================
    # AUTH FLOW (PLACEHOLDER SAFE)
    # ==========================
    def auth_flow(self):
        try:
            self.__load_tokens()
            if not self.token_data.get("auth_token"):
                print("⚠️ No auth token found, login required")
        except Exception as e:
            print("Auth flow error:", e)
