# settings.py
import os

USER_FILE = "authorized_users.json"
SESSION_FILE = "session_login.json"
DATA_FILE = "admin_data_v2.json"
SETTINGS_FILE = "matrix_settings.json"

# --- MERCHANDISE UPI SETTINGS CONFIG ---
ADMIN_UPI_ID = "9304768496@ybl"  # Yahan aapki UPI ID
MONTHLY_SUBSCRIPTION_FEES = 799.00     # Fees amount

# Admin Mappings
ADMIN_DB_DEFAULT = {"9304768496": "Admin Chief", "7982046438": "Admin x"}
SUPER_ADMIN_IDS = ["9304768496", "7982046438"]

# settings.py (Added Refresh Rate Option)
import os

USER_FILE = "authorized_users.json"
SESSION_FILE = "session_login.json"
DATA_FILE = "admin_data_v2.json"
SETTINGS_FILE = "matrix_settings.json"

# --- MERCHANDISE UPI SETTINGS CONFIG ---
ADMIN_UPI_ID = "9304768496@ybl"
MONTHLY_SUBSCRIPTION_FEES = 499.00

# Admin Mappings
ADMIN_DB_DEFAULT = {"9304768496": "Admin Chief", "7982046438": "Admin x"}
SUPER_ADMIN_IDS = ["9304768496", "7982046438"]

# --- LOOP INTERVALS ---
REFRESH_INTERVAL_MS = 5000
