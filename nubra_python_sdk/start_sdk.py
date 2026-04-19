#src/nubra_python_sdk/start_sdk.py
import os, glob, shelve, getpass, requests # type: ignore
import sys
import pandas as pd # type: ignore
import numpy as np # type: ignore
import uuid
from enum import Enum
from datetime import datetime
from typing import Dict
from nubra_python_sdk.validation import InstrumentData
from nubra_python_sdk.validation import VersionEnum
from nubra_python_sdk.interceptor.errors import NubraValidationError

from dotenv import load_dotenv  # type: ignore
from nubra_python_sdk.validation import InstrumentData


SDK_VERSION= "0-4-0"

class NubraEnv(str, Enum):
    DEV = "DEV"
    STAGING = "STAGING"
    PROD = "PROD"
    UAT = "UAT"

class InitNubraSdk:
    """
    A class to handle authentication, token management, and reference data retrieval for the Nubra SDK.
    """
    REF_ID_MAP: Dict[int, InstrumentData] = {}
    SYMBOL_MAP: Dict[str, InstrumentData] = {}
    NUBRA_MAP: Dict[str, InstrumentData]= {}
    REF_ID_MAP_GLOBAL: Dict[str, InstrumentData]= {}

    REF_ID_MAP_BSE: Dict[int, InstrumentData] = {}
    SYMBOL_MAP_BSE: Dict[str, InstrumentData] = {}
    NUBRA_MAP_BSE: Dict[str, InstrumentData] = {}


    DF_REF_DATA = pd.DataFrame()
    DF_REF_DATA_NSE = pd.DataFrame()
    DF_REF_DATA_BSE = pd.DataFrame()

    TOKEN_STORE = "auth_data.db"

    HEADERS = {"Content-Type": "application/json"}
    BEARER_TOKEN = None
    FLAG = {"value": False}
    VERSION_URL = "https://test.pypi.org/pypi/nubra-sdk/json"
    VERSION = SDK_VERSION.replace("-", ".")

    def __init__(self, env: NubraEnv, totp_login: bool = False, env_creds: bool = False, insti_login:bool = False):
        """
        Initializes the InitNubraSdk object. Loads tokens from storage and performs authentication if necessary.
        """
        if env == NubraEnv.DEV:
            self.API_BASE_URL = "https://nubra-dev1.zanskar.xyz/api"
            self.WEBSOCKET_URL = "wss://nubra-dev1.zanskar.xyz/api/ws"
            self.WEBSOCKET_URL_BATCH= "wss://nubra-dev1.zanskar.xyz/apibatch/ws"

        elif env == NubraEnv.STAGING:
            self.API_BASE_URL = "https://nubra-staging.zanskar.xyz/api"
            self.WEBSOCKET_URL = "wss://nubra-staging.zanskar.xyz/api/ws"
            self.WEBSOCKET_URL_BATCH = "wss://nubra-staging.zanskar.xyz/apibatch/ws"

        elif env == NubraEnv.PROD:
            self.API_BASE_URL = "https://api.nubra.io"
            self.WEBSOCKET_URL = "wss://api.nubra.io/ws"
            self.WEBSOCKET_URL_BATCH= "wss://api.nubra.io/apibatch/ws"

        elif env == NubraEnv.UAT:
            self.API_BASE_URL = "https://uatapi.nubra.io"
            self.WEBSOCKET_URL = "wss://uatapi.nubra.io/ws"
            self.WEBSOCKET_URL_BATCH= "wss://uatapi.nubra.io/apibatch/ws"
        else:
            raise ValueError(
                f"Expected one of: {NubraEnv.DEV}, {NubraEnv.STAGING}, {NubraEnv.PROD}, {NubraEnv.UAT}"
            )
        self.totp_login = totp_login
        self.__phone_number= None
        self.__mpin= None

        self.exchange_client_code = None
        self.client_code = None
        self.username = None
        self.password = None

        self.insti_login = insti_login
        
        self.token_data = {}
        self.db_path = self.TOKEN_STORE
        self.env_path_login = env_creds
        if self.env_path_login:
            self.load_env_variables()
       if not type(self).FLAG["value"]:
    try:
        self.auth_flow()
        self.__refresh_ref_data()
        self.__get_user_info()
        type(self).FLAG["value"] = True
    except Exception as e:
        print("SDK INIT FAILED:", e)
        raise
    def __refresh_ref_data(self):
        """
        Refreshes reference data by loading tokens and verifying session validity. If session is invalid or missing, triggers login.
        """
        self.__load_tokens()
        if not self.token_data.get("auth_token") or not self.token_data.get("x-device-id"):
            print("Missing token data, triggering login.")
            self.auth_flow()
        response = self._get_instruments()
        if response in (401, 440):
            print("Unauthorized, triggering re-login.")
            self.auth_flow()
            response = self._get_instruments()

    def __load_tokens(self):
        """
        Loads token data from the token store.
        """
        try:
            with shelve.open(self.db_path, flag='c') as db:
                self.token_data = {
                    "auth_token": db.get("auth_token"),
                    "session_token": db.get("session_token"),
                    "time_refdata": db.get("time_refdata"),
                    "x-device-id": db.get("x-device-id"),
                }
        except Exception as e:
            print(f"Failed to load tokens: {e}")
            self.token_data = {}
        return self.token_data

    def __save_tokens(self, auth_token=None, session_token=None, time_refdata=None, x_device_id=None):
        """
        Saves the provided token data to the token store.
        """
        try:
            with shelve.open(self.db_path, flag='c', writeback=True) as db:
                if auth_token is not None:
                    db["auth_token"] = auth_token
                if session_token is not None:
                    db["session_token"] = session_token
                if time_refdata is not None:
                    db["time_refdata"] = time_refdata
                if x_device_id is not None:
                    db["x-device-id"] = x_device_id
                db.sync()
        except Exception as e:
            print(f"Failed to save tokens: {e}")

    def __check_latest_nubra_sdk_version(self):
        try:
            response = requests.get(self.VERSION_URL, timeout=2)
            response.raise_for_status()

            data = response.json()
            latest_version = next(reversed(data["releases"])) 
            return latest_version
        except Exception: 
            return None

    def __get_user_info(self):
        try : 
            user_info_endpoint = f"{self.API_BASE_URL}/userinfo"
            result = requests.get(url=user_info_endpoint, headers=self.HEADERS)
            result.raise_for_status() 
            
            data = result.json()
    
            if not isinstance(data, dict):
                return
            
            env_info = data.get("env_info")
            if isinstance(env_info, dict):
                user_ws_url = env_info.get("user_ws_url")
                market_ws_url = env_info.get("market_ws_url")
                if user_ws_url != None:
                    self.WEBSOCKET_URL = user_ws_url
                if market_ws_url != None:
                     self.WEBSOCKET_URL_BATCH = market_ws_url
            
            version_info = data.get("version_info")
            if not isinstance(version_info, dict):
                return

            version_status = version_info.get("status")
            if version_status is None:
                return
            
            latest_version = self.__check_latest_nubra_sdk_version()
            if latest_version is not None:
                if version_status == VersionEnum.DEPRECATED:
                    sys.exit(f"WARNING: Upgrade nubra-sdk to version:-{latest_version}. Current version is deprecated !!")
                elif version_status == VersionEnum.DEPRECATION_WARNING:
                    print(f"WARNING: Upgrade nubra-sdk to version:-{latest_version}. Current version will deprecate soon !!")
                elif latest_version != self.VERSION:
                    print(f"New version available, Upgrade nubra-sdk to version:-{latest_version}.")

        except Exception as e: 
            print(f"Exception occured while fetching user info: {e}")

    def load_env_variables(self):
        try:
            dotenv_path = os.path.join(os.getcwd(), ".env")
            load_dotenv(dotenv_path)
            import streamlit as st
            self.__phone_number = st.secrets.get("PHONE_NO")
            self.__mpin = st.secrets.get("MPIN")
            self.client_code= os.getenv("CLIENT_CODE")
            self.exchange_client_code = os.getenv("EXCHANGE_CLIENT_CODE")
            self.username = os.getenv("USERNAME")
            self.password = os.getenv("PASSWORD")
            if not self.insti_login:
                if not self.__phone_number:
                    print('Missing "PHONE_NO" in environment variables.')
            if self.insti_login:
                if not self.client_code:
                    print('Missing "CLIENT_CODE" in environment variables')
                if not self.exchange_client_code:
                    print('Missing "EXCHANGE_CLIENT_CODE" in environment variable')
                if not self.username:
                    print('Missing "USERNAME" in environment variable')
                if not self.password:
                    print('Missing "PASSWORD" in environment variable')

            if not self.__mpin:
                print('Missing "MPIN" in environment variables.')
            return True
        except Exception as e:
            print("Failed to load environment variables:", str(e))


    def auth_flow(self):
        """
        Handles the authentication flow, including OTP and MPIN verification.
        If tokens are missing or invalid, initiates a new login sequence.
        """
        try:
            if self.__shelve_exists(self.db_path):
                self.__load_tokens()
                if not self.token_data.get("auth_token") or not self.token_data.get("x-device-id"):
                    print("Missing auth_token or x-device-id, initiating login.")
                    self._login()
                else:
                    self.__setup_headers_from_tokens()
                    if not self._verify_existing_session():
                        print("Invalid session, re-authenticating...")
                        self._login()
            else:
                self._login()
        except Exception as e:
            print(f"Exception in auth_flow: {e}")
            raise

    def __setup_headers_from_tokens(self):
        """
        Sets the request headers from the loaded tokens.
        """
        self.HEADERS["x-device-id"] = self.token_data["x-device-id"]
        self.HEADERS["Authorization"] = f"Bearer {self.token_data['session_token']}"
        self.HEADERS["x-app-version"] = self.VERSION
        self.HEADERS["x-device-os"] = "sdk"
        self.HEADERS["Cookie"] = f"deviceId={self.token_data['x-device-id']}"
        # self.HEADERS["x-canary"]= "true"
        type(self).BEARER_TOKEN = self.token_data["session_token"]

    def _verify_existing_session(self) -> bool:
        """
        Verifies whether the current session is valid by checking MPIN.
        """
        try:
            return self.__after_login_verify__mpin()
        except Exception as e:
            print(f"verify_existing_session failed: {e}")
            return False
        

    def __after_login_verify__mpin(self, max_attempts: int = 3) -> bool:
        """
        Verifies the MPIN after login. Allows multiple attempts.
        """
        for attempt in range(max_attempts):
            try:
                if self.__verify__mpin():
                    return True
                else:
                    print(f" Invalid MPIN ({max_attempts - attempt - 1} attempts left). Please try again.")
            except Exception as e:
                print(f"MPIN verification error ({max_attempts - attempt - 1} attempts left): {e}")
        raise ValueError("MPIN verification failed after multiple attempts.")

    def __shelve_exists(self, path: str) -> bool:
        """
        Checks if the shelve file exists.
        """
        exists = bool(glob.glob(f"{path}*"))
        return exists

    def __verify__mpin(self, auth_token: str = None, mpin: str = None) -> bool:
        """
        Verifies the MPIN with the server using the provided token and MPIN.
        """
        token = auth_token or self.token_data.get("auth_token")
        if not token:
            return False
        if self.env_path_login:
            if mpin:
                mpin= mpin
            else:
                mpin = self.__mpin
        else:
            mpin = mpin

        if not mpin:
            mpin = input("🔑 Enter your MPIN: ")

        url = f"{self.API_BASE_URL}/verifypin"
        headers = {**self.HEADERS, "Authorization": f"Bearer {token}"}
        try:
            response = requests.post(url, json={"pin": mpin}, headers=headers)
            if response.status_code == 200:
                session_token = response.json().get("session_token") or response.json().get("data", {}).get("token")
                if not session_token:
                    return False
                self.__save_tokens(session_token=session_token)
                self.token_data["session_token"] = session_token
                self.__setup_headers_from_tokens()
                return True
            elif response.status_code in (401, 440):
                self.reset_tokens()
                return False
            return False
        except Exception as e:
            print(f"verify__mpin exception: {e}")
            return False

    def __send_otp(self, phone: str) -> str:
        """
        Sends an OTP to the specified phone number and returns the temp_token.
        """
        url = f"{self.API_BASE_URL}/sendphoneotp"
        try:
            response = requests.post(url, json={"phone": phone, "flow" : "", "skip_totp": False})
            if response.status_code != 200:
                raise ValueError(f"Failed to send OTP: {response.status_code} - {response.text}")
            temp_token = response.json().get("temp_token")
            next_step = response.json().get("next")
            if not temp_token:
                raise ValueError("temp_token missing in OTP response")
            if not next_step:
                raise ValueError("Next Step Missing in response")
            if next_step == "VERIFY_MOBILE":
                return temp_token
            elif next_step == "VERIFY_TOTP":
                payload= {
                    "phone": phone, 
                    "flow" : "",
                    "skip_totp": True
                }
                headers= {"x-temp-token": temp_token}
                response = requests.post(url, json= payload, headers= headers)
                if response.status_code!=200:
                    raise ValueError(f"Failed to send Otp: {response.status_code} - {response.text}")
                temp_token= response.json().get("temp_token")
                if not temp_token:
                    raise ValueError("temp token missing in response")
                return temp_token
            else:
                raise ValueError(f"Invalid next step. Got: {next_step}")
        except Exception as e:
            print(f"send_otp failed: {e}")
            raise


    def totp_generate_secret(self):
        url = f"{self.API_BASE_URL}/totp/generate-secret"
        try:
            response = requests.get(url, headers=self.HEADERS)
            if response.status_code == 200:
                print(response.text)
                return response.text
            elif response.status_code in (401, 440):
                self.auth_flow()
                return self.totp_generate_secret()
            else:
                print(response.text)
                return response.text
        except Exception as e:
            print(f"Exception occurred: {e}")
            raise

    def _enable_totp(self, totp: str = None, mpin: str = None):
        try:
            url= f"{self.API_BASE_URL}/totp/enable"
            payload= {
                "mpin": mpin,
                "totp": totp
            }
            response= requests.post(url, headers=self.HEADERS, json= payload)
            if response.status_code == 200:
                print(response.text)
                return response.text
            elif response.status_code in (401, 440):
                self.auth_flow()
                return self._enable_totp()
            if response.status_code!=200:
                raise ValueError(f"TOTP verification failed, status_code= {response.status_code}")
        except Exception as e:
            print(f"Exception occured: {e}")
            raise
        

    def totp_enable(self):
        max_attempts=3
        for attempt in range(max_attempts):
            mpin = input("🔑 Enter your MPIN: ")
            totp= input("🔐 Enter TOTP: ")
            try:
                msg= self._enable_totp(totp, mpin)
                return msg
            except Exception as e:
                print(f"T-OTP verification failed ({max_attempts - attempt - 1} attempts left): {e}")
        raise ValueError("Maximum OTP attempts exceeded.")



    def totp_disable(self):
        url= f"{self.API_BASE_URL}/totp/disable"
        try:
            mpin = input("🔑 Enter your MPIN: ")
            payload={
                "mpin": mpin
            }
            response= requests.post(url, headers= self.HEADERS, json=payload)
            if response.status_code ==200:
                print(response.text)
                return response.text
            elif response.status_code in (401, 440):
                self.auth_flow()
                return self.totp_disable()
            else:
                print(response.text)
                return response.text
        except Exception as e:
            print(f"Exception occured: {e}")
            raise


    def _totp_login(self, phone: str, x_device_id: str, totp: str) ->str:
        url= f"{self.API_BASE_URL}/totp/login"
        headers= {"x-device-id": x_device_id}
        try:
            payload= {
                "phone": phone, 
                "totp": int(totp),
                "otp" : "",
            }
            response= requests.post(url, json= payload, headers=headers)
            if response.status_code!=201:
                raise ValueError(f"TOTP verification failed: {response.status_code} - {response.text}")
            
            auth_token= response.json().get("auth_token")
            if not auth_token:
                raise ValueError("auth_token missing in OTP verification response")
            self.__save_tokens(auth_token= auth_token, x_device_id= x_device_id)
            self.token_data["auth_token"] = auth_token
            return auth_token
        except Exception as e:
            print(f"verify_otp failed: {e}")
            raise

    def __verify_otp(self, phone: str, otp: str, temp_token: str, x_device_id: str) -> str:
        """
        Verifies the OTP for the provided phone number and temp_token.
        Returns the auth_token if successful.
        """
        url = f"{self.API_BASE_URL}/verifyphoneotp"
        headers = {"x-device-id": x_device_id, "x-temp-token": temp_token}
        payload = {"phone": phone, "otp": otp}
        try:
            response = requests.post(url, json=payload, headers=headers)
            if response.status_code != 201:
                raise ValueError(f"OTP verification failed: {response.status_code} - {response.text}")
            auth_token = response.json().get("auth_token")
            if not auth_token:
                raise ValueError("auth_token missing in OTP verification response")
            self.__save_tokens(auth_token=auth_token, x_device_id=x_device_id)
            self.token_data["auth_token"] = auth_token
            return auth_token
        except Exception as e:
            print(f"verify_otp failed: {e}")
            raise

    def insti_login_password(self, exchange_client_code: str, client_code: str, username: str, password: str, x_device_id: str ) -> str:
        url = f"{self.API_BASE_URL}/login-insti"
        headers = {"x-device-id": x_device_id}
        payload = {
            "exchange_client_code": exchange_client_code,
            "client_code": client_code,
            "username": username,
            "password": password,
        }
        try:
            response = requests.post(url, json=payload, headers=headers)
            if response.status_code == 404:
                print(f"{response.text}")
                raise StopIteration("User not found.")
            elif response.status_code == 500:
                raise ValueError(f"Password verification failed. {response.text}")
            elif response.status_code != 201:
                raise RuntimeError(f"Unexpected error: {response.status_code} - {response.text}")

            auth_token = response.json().get("auth_token")
            if not auth_token:
                raise RuntimeError("Auth token missing in password verification response.")

            self.__save_tokens(auth_token=auth_token, x_device_id=x_device_id)
            self.token_data["auth_token"] = auth_token
            return auth_token

        except (StopIteration, ValueError):
            raise 
        except Exception as e:
            print(f"verify password failed: {e}")
            raise

    def __ensure_device_id(self) -> str:
        """
        Ensures that a valid device ID exists. If not, generates a new one and stores it.
        """
        self.__load_tokens()
        x_device_id = self.token_data.get("x-device-id")
        if not x_device_id:
            x_device_id = f"{uuid.uuid1()}-sdk-{SDK_VERSION}"
            self.token_data["x-device-id"] = x_device_id
            self.__save_tokens(x_device_id=x_device_id)
        self.HEADERS["x-device-id"] = x_device_id
        self.HEADERS["x-app-version"] = self.VERSION
        self.HEADERS["x-device-os"] = "sdk"
        self.HEADERS["Cookie"] = f"deviceId={x_device_id}"
        return x_device_id
    

    def __prompt_and_verify_otp(self, phone: str, temp_token: str, x_device_id: str, max_attempts: int = 3) -> str:
        """
        Prompts the user to enter OTP and verifies it.
        Allows multiple attempts for OTP verification.
        """
        for attempt in range(max_attempts):
            otp = input("🔐 Enter OTP: ")
            try:
                auth_token = self.__verify_otp(phone, otp, temp_token, x_device_id)
                return auth_token
            except Exception as e:
                print(f"OTP verification failed ({max_attempts - attempt - 1} attempts left): {e}")
        raise ValueError("Maximum OTP attempts exceeded.")


    def __prompt_and_verify_password(self, exchange_client_code: str, client_code: str, username: str, x_device_id: str, max_attempts: int = 3) -> str:
        """
        Prompts the user to enter Password and verifies it.
        - Stops immediately if 404 (invalid user)
        - Retries on 500 (wrong password)
        - Returns auth_token on success (201)
        """
        for attempt in range(max_attempts):
            try:
                if self.env_path_login and os.getenv("PASSWORD"):
                    password = self.password
                else:
                    password = None
            except Exception as e:
                print(f"Exception occurred while checking env password: {e}")
                password = None

            if not password:
                password = input("Enter password: ").strip()

            try:
                auth_token = self.insti_login_password(
                    exchange_client_code, client_code, username, password, x_device_id
                )
                return auth_token 
            except StopIteration:
                sys.exit(1)
            except ValueError as e:
                remaining = max_attempts - attempt - 1
                print(f"Wrong password ({remaining} attempts left): {e}")
            except Exception as e:
                remaining = max_attempts - attempt - 1
                print(f"Unexpected error ({remaining} attempts left): {e}")

        print("Max password attempts reached. Exiting.")
        sys.exit(1)

        
    def __prompt_and_verify_totp(self, phone:str, x_device_id: str, max_attempts: int= 3)->str:
        """
        Prompts the user to enter TOTP and verifies it.
        Allows multiple attempts for OTP verification.
        """
        for attempt in range(max_attempts):
            totp= input("🔐 Enter TOTP: ")
            try:
                auth_token = self._totp_login(phone, x_device_id, totp= totp)
                return auth_token
            except Exception as e:
                print(f"TOTP verification failed ({max_attempts - attempt - 1} attempts left): {e}")
        raise ValueError("Maximum OTP attempts exceeded.")

    def __prompt_and_verify__mpin(self, auth_token: str, max_attempts: int = 3) -> bool:
        """
        Prompts the user to enter MPIN and verifies it.
        Allows multiple attempts for MPIN verification.
        """
        for attempt in range(max_attempts):
            mpin= self.__mpin
            if not mpin:
                mpin = input("🔑 Enter your MPIN: ")
                # self.__mpin = mpin
            try:
                if self.__verify__mpin(auth_token, mpin):
                    return True
                else:
                    print(f"Invalid MPIN ({max_attempts - attempt - 1} attempts left). Please try again.")
            except Exception as e:
                print(f"MPIN verification error ({max_attempts - attempt - 1} attempts left): {e}")
        raise ValueError("MPIN verification failed after multiple attempts.")


    def _login(self):
        """
        Prompts the user to enter their phone number, sends OTP, verifies it, and completes the login by verifying MPIN.
        """
        try:
            phone= self.__phone_number
            if not self.insti_login:
                if not phone:
                    phone = input("📱 Enter your phone number: ").strip()
                if self.totp_login:
                    x_device_id = self.__ensure_device_id()
                    auth_token= self.__prompt_and_verify_totp(phone, x_device_id)
                else:
                    print(f"🔄 Sending OTP to: {phone}")
                    x_device_id = self.__ensure_device_id()
                    temp_token = self.__send_otp(phone)
                    auth_token = self.__prompt_and_verify_otp(phone, temp_token, x_device_id)
                if self.__prompt_and_verify__mpin(auth_token):
                    print("✅ Login successful.")
                    return {"message": "Login successful"}
                
            elif self.insti_login:
                x_device_id = self.__ensure_device_id()
                exchange_client_code = self.exchange_client_code
                client_code = self.client_code
                username = self.username
                if not exchange_client_code:
                    exchange_client_code= input("Enter exchange client code: ").strip()
                if not client_code:
                    client_code = input("Enter client code: ").strip()
                if not username:
                    username = input("Enter username: ").strip()
                auth_token = self.__prompt_and_verify_password(exchange_client_code, client_code, username, x_device_id)

                if self.__prompt_and_verify__mpin(auth_token):
                    print("✅ Login successful.")
                    return {"message": "Login successful"}
        except Exception as e:
            print(f"Login failed: {e}")
            self.reset_tokens()
            return {"error": f"Login failed: {str(e)}"}

    def reset_tokens(self):
        """
        Resets all stored tokens and clears the authentication state.
        """
        try:
            for file in glob.glob(f"{self.db_path}*"):
                os.remove(file)
                print(f"Deleted: {file}")
            self.token_data = {}
            self.HEADERS.pop("Authorization", None)
            self.HEADERS.pop("x-device-id", None)
            self.HEADERS.pop("x-app-version", None)
            self.HEADERS.pop("x-device-os", None)
            self.HEADERS.pop("Cookie", None)
            type(self).BEARER_TOKEN = None
        except Exception as e:
            print(f"Failed to reset tokens: {e}")

    def logout(self):
        """
        Logs the user out by sending a logout request and resetting the tokens.
        """
        token=self.__load_tokens()
        auth_token= token.get("auth_token")
        x_device_id= token.get("x-device-id")
        Headers={
            "x-device-id": x_device_id,
            "Authorization": f"Bearer {auth_token}"
            
        }
        api_logout = f"{self.API_BASE_URL}/logout"

        response= requests.post(api_logout, headers= Headers)
        if response.status_code != 200:
                raise ValueError(f"failed to logout: {response}")
        
        self.reset_tokens()
        return {"msg": "Logout successful"}
    
    def reset_password(self):
        try:
            if self.insti_login:
                current_password = input("Enter current password: ").strip()
                new_password = input("Enter new password: ").strip()
                payload= {
                    "current_password": current_password, 
                    "new_password": new_password
                }
                reset_password_endpoint =  f"{self.API_BASE_URL}/reset_password"
                response = requests.post(reset_password_endpoint, headers= self.HEADERS, json = payload)
                print(f" status code : {response.status_code}, response: {response.text}")
                return response.status_code
            else:
                raise ValueError(f"Only allowed for insti-clients")
        except Exception as e:
            return {"msg": f"Exception occured: {e}"}
   
    def _get_instruments(self):
        """
        Fetches the instrument data for the current date.
        """
        today_date = datetime.today().strftime('%Y-%m-%d')
        url = f"{self.API_BASE_URL}/refdata/refdata/{today_date}"
        url_bse = f"{self.API_BASE_URL}/refdata/refdata/{today_date}?exchange=BSE"
        response = requests.get(url, headers=self.HEADERS)
        response_bse = requests.get(url_bse, headers=self.HEADERS)
        try:
            if response.status_code == 200:
                data = response.json().get("refdata")
                newDf = pd.DataFrame(data if isinstance(data, list) else [data])
                newDf[["ref_id","strike_price", "expiry", "tick_size","lot_size", "zanskar_id"]]= newDf[["ref_id","strike_price", "expiry", "tick_size", "lot_size", "zanskar_id"]].astype("Int64")
                newDf.rename(columns={
                    'zanskar_name': 'nubra_name'
                }, inplace=True)           

                type(self).DF_REF_DATA_NSE.drop(type(self).DF_REF_DATA_NSE.index, inplace=True)      

                for col in newDf.columns:
                    type(self).DF_REF_DATA_NSE[col] = newDf[col]
                if isinstance(data, list):
                    for item in data:
                        try:
                            obj = InstrumentData(**item)
                            type(self).REF_ID_MAP[obj.ref_id] = obj
                            type(self).SYMBOL_MAP[obj.stock_name] = obj
                            type(self).NUBRA_MAP[obj.nubra_name]= obj
                            type(self).REF_ID_MAP_GLOBAL[obj.ref_id] = obj
                        except Exception as e:
                            print(f"Exception occured for ref_id={item.get('ref_id')}, NSE : {e}")
                elif isinstance(data, dict):
                    try:
                        obj = InstrumentData(**data)
                        type(self).REF_ID_MAP[obj.ref_id] = obj
                        type(self).SYMBOL_MAP[obj.stock_name] = obj
                        type(self).NUBRA_MAP[obj.nubra_name]= obj
                        type(self).REF_ID_MAP_GLOBAL[obj.ref_id] = obj
                    except Exception as e:
                        print(f"Exception occured for ref_data:NSE, {e}")

            if response_bse.status_code ==200:
                data_bse =  response_bse.json().get("refdata")
                newDf_BSE = pd.DataFrame(data_bse if isinstance(data_bse, list) else [data_bse])
                newDf_BSE[["ref_id", "strike_price","expiry", "tick_size", "lot_size"]] = newDf_BSE[["ref_id", "strike_price", "expiry", "tick_size", "lot_size"]].astype("Int64")
                newDf_BSE.rename(columns={
                    'zanskar_name': 'nubra_name'
                }, inplace= True)

                type(self).DF_REF_DATA_BSE.drop(type(self).DF_REF_DATA_BSE.index, inplace=True)

                for col in newDf_BSE.columns:
                    type(self).DF_REF_DATA_BSE[col]= newDf_BSE[col]

                if isinstance(data_bse, list):
                    for item in data_bse:
                        try:
                            obj= InstrumentData(**item)
                            type(self).REF_ID_MAP_BSE[obj.ref_id]= obj
                            type(self).SYMBOL_MAP_BSE[obj.stock_name] = obj
                            type(self).NUBRA_MAP_BSE[obj.nubra_name] = obj
                            type(self).REF_ID_MAP_GLOBAL[obj.ref_id] = obj
                        except Exception as e:
                            print(f"Exception occured for ref_id={item.get('ref_id')}, BSE: {e}")
                elif isinstance(data_bse, dict):
                    try:
                        obj= InstrumentData(**data_bse)
                        type(self).REF_ID_MAP_BSE[obj.ref_id] = obj
                        type(self).SYMBOL_MAP_BSE[obj.stock_name]= obj
                        type(self).NUBRA_MAP_BSE[obj.nubra_name]= obj
                        type(self).REF_ID_MAP_GLOBAL[obj.ref_id] = obj
                    except Exception as e:
                        print(f"Exception occured for ref data: BSE, {e}")
            #Now concatenate the two df
            type(self).DF_REF_DATA= pd.concat([type(self).DF_REF_DATA_NSE, type(self).DF_REF_DATA_BSE], ignore_index= True)

            return response.status_code
        except Exception as e:
            print(f"Exception in get_instruments : {e}")
            return response.status_code
