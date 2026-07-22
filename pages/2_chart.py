import streamlit as st
import time
import os
from datetime import datetime, timedelta
from streamlit_autorefresh import st_autorefresh

# ================= 1. PAGE SETUP =================
st.set_page_config(layout="wide", page_title="SmartWealth Premium Zones Terminal")

# ================= 2. NATIVE SDK CONNECTION MATRIX =================
from nubra_python_sdk.start_sdk import InitNubraSdk, NubraEnv
from nubra_python_sdk.marketdata.market_data import MarketData

if "direct_market_engine" not in st.session_state:
    try:
        sdk_client = InitNubraSdk(NubraEnv.PROD, env_creds=True)
        st.session_state["direct_market_engine"] = MarketData(sdk_client)
    except Exception:
        st.session_state["direct_market_engine"] = None

market_data = st.session_state["direct_market_engine"]

if market_data is None:
    st.error("❌ Market engine connection failed.")
    st.stop()

# ================= 3. SIDEBAR ANCHORS FRAME =================
st.sidebar.header("⚙️ Terminal Controller")
target_symbol = st.sidebar.selectbox("🔤 Select Active Index", ["NIFTY", "BANKNIFTY", "SENSEX"], index=0)

exchange_type = "BSE" if target_symbol == "SENSEX" else "NSE"

prev_close_map = {"NIFTY": 24050.00, "BANKNIFTY": 52200.00, "SENSEX": 79300.00}
current_ltp = 0.0
yesterday_close = prev_close_map.get(target_symbol, 24000.0)

try:
    snap = market_data.current_price(target_symbol, exchange=exchange_type)
    if snap:
        if getattr(snap, 'price', None):
            raw_p = float(snap.price)
            current_ltp = raw_p / 100.0 if raw_p > 100000 else raw_p
        
        if hasattr(snap, 'close') and snap.close:
            raw_c = float(snap.close)
            yesterday_close = raw_c / 100.0 if raw_c > 100000 else raw_c
        elif hasattr(snap, 'prev_close') and snap.prev_close:
            raw_pc = float(snap.prev_close)
            yesterday_close = raw_pc / 100.0 if raw_pc > 100000 else raw_pc
except Exception:
    pass

if current_ltp == 0.0:
    fallback_prices = {"NIFTY": 24081.10, "BANKNIFTY": 57602.00, "SENSEX": 77156.35}
    current_ltp = fallback_prices.get(target_symbol, yesterday_close)

net_change = current_ltp - yesterday_close
change_pct = (net_change / yesterday_close) * 100.0 if yesterday_close > 0 else 0.0

if net_change >= 0:
    color_class = "text-market-up"
    index_glow_class = "index-glow-green"
    arrow = "▲"
    sign = "+"
else:
    color_class = "text-market-down"
    index_glow_class = "index-glow-red"
    arrow = "▼"
    sign = ""

# ================= 4. TRADECLUE STYLE 9:20 LOCKED ZONES ENGINE =================
from datetime import datetime, timedelta

# Current IST Time nikalna
now_ist = datetime.utcnow() + timedelta(hours=5, minutes=30)
current_time_str = now_ist.strftime("%H:%M")
current_date_str = now_ist.strftime("%Y-%m-%d")

# Unique cache key jisme date bhi ho taaki har naye din naya zone lock ho sake
cache_key = f"locked_zones_{target_symbol}_{current_date_str}"

# Agar subah 9:20 ke baad pehli baar chal raha hai aur session mein nahi hai, tabhi lock karein
if cache_key not in st.session_state and current_time_str >= "09:20":
    best_ce_strike = None
    best_pe_strike = None
    
    if "ticks" in st.session_state and isinstance(st.session_state.ticks, dict) and len(st.session_state.ticks) > 0:
        try:
            max_ce_score = -1
            max_pe_score = -1
            
            for key, tick_data in st.session_state.ticks.items():
                if not isinstance(tick_data, dict):
                    continue
                symbol_tag = tick_data.get("symbol", "").upper()
                if target_symbol not in symbol_tag:
                    continue
                strike = float(tick_data.get("strike", 0))
                if strike == 0:
                    continue
                
                # OI aur Volume dono ko combine karke strongest institutional weight nikalna
                ce_oi = float(tick_data.get("ce_oi", tick_data.get("CE OI", 0)))
                ce_vol = float(tick_data.get("ce_volume", tick_data.get("CE Volume", 0)))
                ce_score = ce_oi + (ce_vol * 0.1)
                
                pe_oi = float(tick_data.get("pe_oi", tick_data.get("PE OI", 0)))
                pe_vol = float(tick_data.get("pe_volume", tick_data.get("PE Volume", 0)))
                pe_score = pe_oi + (pe_vol * 0.1)
                
                if ce_score > max_ce_score:
                    max_ce_score = ce_score
                    best_ce_strike = strike
                if pe_score > max_pe_score:
                    max_pe_score = pe_score
                    best_pe_strike = strike
        except Exception:
            pass

    # Fallback aur Zone Range Calculation
    if target_symbol == "NIFTY":
        bs = float((current_ltp // 50) * 50)
        s_low = best_ce_strike if best_ce_strike else bs
        s_high = s_low + 30
        d_high = best_pe_strike if best_pe_strike else (bs - 100)
        d_low = d_high - 30
    elif target_symbol == "BANKNIFTY":
        bs = float((current_ltp // 100) * 100)
        s_low = best_ce_strike if best_ce_strike else bs
        s_high = s_low + 150
        d_high = best_pe_strike if best_pe_strike else (bs - 300)
        d_low = d_high - 150
    else: # SENSEX
        bs = float((current_ltp // 100) * 100)
        s_low = best_ce_strike if best_ce_strike else bs
        s_high = s_low + 100
        d_high = best_pe_strike if best_pe_strike else (bs - 200)
        d_low = d_high - 100

    # Values ko us din ke liye session mein permanently lock kar do
    st.session_state[cache_key] = {
        "sup_low": s_low,
        "sup_high": s_high,
        "dem_high": d_high,
        "dem_low": d_low
    }

# Zones ko fetch karna (Agar 9:20 ke baad lock ho gaya hai toh wahi dikhega poore din)
if cache_key in st.session_state:
    locked_zones = st.session_state[cache_key]
    sup_low = locked_zones["sup_low"]
    sup_high = locked_zones["sup_high"]
    dem_high = locked_zones["dem_high"]
    dem_low = locked_zones["dem_low"]
else:
    # 9:20 se pehle ya ticks aane se pehle ka default fallback level
    if target_symbol == "NIFTY":
        bs = float((current_ltp // 50) * 50)
    elif target_symbol == "BANKNIFTY":
        bs = float((current_ltp // 100) * 100)
    else:
        bs = float((current_ltp // 100) * 100)
        
    sup_low = bs
    sup_high = sup_low + 30
    dem_high = sup_low - 100
    dem_low = dem_high - 30

p_point = round((sup_low + dem_high) / 2)
now_ist_str = (datetime.utcnow() + timedelta(hours=5, minutes=30)).strftime("%Y-%m-%d %H:%M:%S IST")
# ================= 5. DYNAMIC HTML/CSS VISUAL ENGINE =================
st.html(f"""
<style>
    .block-container {{
        padding-top: 1.5rem !important;
        padding-bottom: 1rem !important;
        max-width: 95% !important;
    }}
    
    /* MAIN CONTROLLER CONTAINER WITH CYAN/BLUE NEO GLOW */
    .terminal-container {{
        background-color: #151922 !important;
        border: 1px solid #00d2ff !important;
        border-radius: 14px !important;
        padding: 24px !important;
        box-shadow: 0 0 25px rgba(0, 210, 255, 0.28) !important;
        margin-bottom: 25px !important;
        font-family: sans-serif !important;
    }}
    
    .asset-header-row {{
        display: flex !important;
        justify-content: space-between !important;
        align-items: center !important;
        border-bottom: 1px solid #232d3f !important;
        padding-bottom: 16px !important;
        margin-bottom: 22px !important;
    }}
    
    .asset-title {{
        font-size: 20px !important;
        font-weight: 800 !important;
        color: #ffffff !important;
        letter-spacing: 1px !important;
    }}
    
    /* DYNAMIC MARKET LOG IN LTPS BADGES */
    .live-ltp-badge-container {{
        font-size: 15px !important;
        font-weight: 800 !important;
        padding: 8px 16px !important;
        border-radius: 8px !important;
        display: flex !important;
        align-items: center !important;
        gap: 12px !important;
        background-color: #11151d !important;
        transition: all 0.4s ease !important;
    }}
    
    .index-glow-green {{
        border: 2px solid #00ff66 !important;
        box-shadow: 0 0 18px rgba(0, 255, 102, 0.45) !important;
    }}
    
    .index-glow-red {{
        border: 2px solid #ff3333 !important;
        box-shadow: 0 0 18px rgba(255, 51, 51, 0.45) !important;
    }}
    
    .text-market-up {{ color: #00ff66 !important; font-weight: 900 !important; }}
    .text-market-down {{ color: #ff3333 !important; font-weight: 900 !important; }}
    
    /* DETAILED THIN BORDER BOXES RE-ADDED */
    .zones-grid {{
        display: flex !important;
        gap: 16px !important;
        flex-wrap: wrap !important;
        width: 100% !important;
    }}
    
    .zone-card {{
        flex: 1 !important;
        min-width: 260px !important;
        border-radius: 8px !important;
        padding: 20px 12px !important;
        text-align: center !important;
        background-color: #1a202c !important;
        transition: all 0.3s ease !important;
    }}
    
    /* Solid Thin Borders Restored */
    .card-resistance {{
        border: 1px solid #ef4444 !important;
    }}
    
    .card-pivot {{
        border: 1px solid #eab308 !important;
    }}
    
    .card-support {{
        border: 1px solid #22c55e !important;
    }}
    
    .card-label {{
        font-size: 11px !important;
        font-weight: 700 !important;
        color: #a0aec0 !important;
        text-transform: uppercase !important;
        letter-spacing: 1px !important;
        margin-bottom: 10px !important;
    }}
    
    .card-value {{
        font-size: 26px !important;
        font-weight: 800 !important;
    }}
    .val-red {{ color: #ff4d4d !important; }}
    .val-yellow {{ color: #ffcc00 !important; }}
    .val-green {{ color: #33ff77 !important; }}
    
    .sync-timestamp {{
        font-size: 10px !important;
        color: #5c6b73 !important;
        text-align: right !important;
        margin-top: 18px !important;
        font-family: monospace !important;
    }}
</style>

<div class="terminal-container">
    <div class="asset-header-row">
        <div class="asset-title">NEXT DAY INSTITUTIONAL LEVELS GRID</div>
        <div class="live-ltp-badge-container {index_glow_class}">
            <span class="{color_class}">⚡ {target_symbol} LTP: ₹{current_ltp:.2f}</span>
            <span class="{color_class}">{arrow} {sign}{abs(net_change):.2f} ({sign}{change_pct:.2f}%)</span>
        </div>
    </div>
    
    <div class="zones-grid">
        <div class="zone-card card-resistance">
            <div class="card-label">🔴 SUPPLY / RESISTANCE (DR ZONE)</div>
            <div class="card-value val-red">{int(sup_low)} - {int(sup_high)}</div>
        </div>
        <div class="zone-card card-pivot">
            <div class="card-label">⚖️ INSTITUTIONAL BALANCE PIVOT (PP)</div>
            <div class="card-value val-yellow">{int(p_point)}</div>
        </div>
        <div class="zone-card card-support">
            <div class="card-label">🟢 DEMAND / SUPPORT (DS ZONE)</div>
            <div class="card-value val-green">{int(dem_low)} - {int(dem_high)}</div>
        </div>
    </div>
    
    <div class="sync-timestamp">🔒 Cloud Broker Node Connected | Last Dynamic Refresh: {now_ist}</div>
</div>
""")

# 🔄 AUTOMATIC 2-SECOND RUNTIME REFRESH
st_autorefresh(interval=2000, key="premium_zones_auto_sync")

st.markdown("---")

target_symbol = locals().get('target_symbol', 'NIFTY')
current_ltp = locals().get('current_ltp', 24000.0)

max_ce_strike_found = None
max_pe_strike_found = None
highest_ce_oi_val = -1
highest_pe_oi_val = -1
total_ce_oi_sum = 0
total_pe_oi_sum = 0
iv_list = []
delta_weighted_sum = 0
total_weight_count = 0

if "ticks" in st.session_state and isinstance(st.session_state.ticks, dict):
    try:
        for k, t_data in st.session_state.ticks.items():
            if not isinstance(t_data, dict):
                continue
            symbol_tag = t_data.get("symbol", "").upper()
            if target_symbol not in symbol_tag:
                continue
                
            strike_val = float(t_data.get("strike", 0))
            c_oi = float(t_data.get("ce_oi", t_data.get("CE OI", 0)))
            p_oi = float(t_data.get("pe_oi", t_data.get("PE OI", 0)))
            
            iv_val = float(t_data.get("iv", t_data.get("IV", 15.0)))
            delta_val = float(t_data.get("delta", t_data.get("Delta", 0.5)))
            
            if iv_val > 0:
                iv_list.append(iv_val)
            
            total_ce_oi_sum += c_oi
            total_pe_oi_sum += p_oi
            
            delta_weighted_sum += delta_val * (c_oi + p_oi)
            total_weight_count += (c_oi + p_oi)
            
            if c_oi > highest_ce_oi_val:
                highest_ce_oi_val = c_oi
                max_ce_strike_found = strike_val
                
            if p_oi > highest_pe_oi_val:
                highest_pe_oi_val = p_oi
                max_pe_strike_found = strike_val
    except Exception:
        pass

if not max_ce_strike_found:
    if target_symbol == "NIFTY":
        max_ce_strike_found = float((current_ltp // 50) * 50)
        max_pe_strike_found = max_ce_strike_found - 100
    elif target_symbol == "BANKNIFTY":
        max_ce_strike_found = float((current_ltp // 100) * 100)
        max_pe_strike_found = max_ce_strike_found - 200
    else:
        max_ce_strike_found = float((current_ltp // 100) * 100)
        max_pe_strike_found = max_ce_strike_found - 200

display_ce_pain = int(max_ce_strike_found)
display_pe_pain = int(max_pe_strike_found) if max_pe_strike_found else display_ce_pain - 100

avg_iv = sum(iv_list) / len(iv_list) if iv_list else 14.5
net_delta = (delta_weighted_sum / total_weight_count) if total_weight_count > 0 else 0.5

if total_ce_oi_sum > 0 and total_pe_oi_sum > 0:
    if total_ce_oi_sum > total_pe_oi_sum:
        market_bias = "BEARISH ACTIVE"
    elif total_pe_oi_sum > total_ce_oi_sum:
        market_bias = "BULLISH ACTIVE"
    else:
        market_bias = "SIDEWAYS ACTIVE"
else:
    if current_ltp >= display_ce_pain:
        market_bias = "BULLISH ACTIVE"
    else:
        market_bias = "BEARISH ACTIVE"

if avg_iv > 18:
    vol_status = "High"
elif avg_iv < 12:
    vol_status = "Low"
else:
    vol_status = "Sideways"

st.markdown(f"**⚡ INSTITUTIONAL QUANT MATRIX: MAX PAIN, IV & DELTA ({target_symbol})**")

col1, col2, col3 = st.columns(3)

with col1:
    st.metric(label="MAX PAIN STRIKES (CE / PE)", value=f"{display_ce_pain} / {display_pe_pain}")

with col2:
    st.metric(label="SETTLEMENT BIAS MESSAGE", value=market_bias)

with col3:
    st.metric(label=f"IV ({avg_iv:.1f}%) | DELTA ({net_delta:.2f})", value=vol_status)
