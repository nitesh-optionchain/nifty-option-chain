# live_tracker.py
# live_tracker.py (Continuity Appended Script Layer)
import pandas as pd
import streamlit as st
from datetime import datetime, timedelta

@st.cache_resource
def get_global_memory(): 
    return {"hist_df": {}}

def process_live_market_dashboard(md, index_choice, target_exch, memory):
    try:
        result = md.option_chain(index_choice, exchange=target_exch)
        if not result or not result.chain:
            st.info("Syncing Market Matrix... ⏳")
            st.stop()

        chain = result.chain
        spot = chain.current_price / 100 if chain.current_price > 100000 else chain.current_price
        atm = chain.at_the_money_strike / 100
        
        t_idx = st.session_state.ticks.get(index_choice, {})
        live_px = t_idx.get('index_value', 0)/100 or spot
        cur_chg = (live_px - spot)
        cur_pct = (cur_chg / spot * 100) if spot > 0 else 0.0

        # Upper Live Indicator Layer
        h_bg, h_txt = ("#e8f5e9", "#1b5e20") if cur_chg >= 0 else ("#ffebee", "#b71c1c")
        arrow = "▲" if cur_chg >= 0 else "▼"
        st.markdown(f'<div style="background:{h_bg}; padding:15px; border-radius:10px; text-align:center; border: 2px solid {h_txt};"><h1 style="color:{h_txt}; margin:0; font-size:32px; font-weight:bold;">{index_choice} {arrow} {live_px:,.2f} <span style="font-size:20px;">({cur_chg:+,.2f} | {cur_pct:+.2f}%)</span></h1></div>', unsafe_allow_html=True)
             
        df_ce = pd.DataFrame([vars(x) for x in chain.ce])
        df_pe = pd.DataFrame([vars(x) for x in chain.pe])
        df_comb = pd.merge(df_ce, df_pe, on="strike_price", suffixes=("_CE","_PE")).fillna(0)
        df_comb["STRIKE"] = (df_comb["strike_price"]/100).astype(int)

        # 🌟 ADDED HERE - Historical Database Pipeline Sync (Pre-market calculation base maps)
        hist_key = f"{index_choice}_5m"
        if hist_key not in memory["hist_df"]:
            try:
                end_t = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.000Z")
                start_t = (datetime.utcnow() - timedelta(days=5)).strftime("%Y-%m-%dT%H:%M:%S.000Z")
                hist_res = md.historical_data({"exchange": target_exch, "type": "INDEX", "values": [index_choice], "fields": ["open", "high", "low", "close", "cumulative_volume"], "startDate": start_t, "endDate": end_t, "interval": "5m", "intraDay": False, "realTime": False})
                raw = hist_res.result[0].values[0][index_choice]
                memory["hist_df"][hist_key] = pd.DataFrame({"time": [pd.to_datetime(p.timestamp, unit="ns").tz_localize("UTC").tz_convert("Asia/Kolkata") for p in raw.close], "open": [p.value/100 for p in raw.open], "high": [p.value/100 for p in raw.high], "low": [p.value/100 for p in raw.low], "close": [p.value/100 for p in raw.close], "vol": [p.value for p in raw.cumulative_volume]})
            except: 
                pass

        # PCR Calculation
        pcr = df_pe["open_interest"].sum() / df_ce["open_interest"].sum()
        mood = "🐂 BULLISH" if pcr > 1.15 else "🐻 BEARISH" if pcr < 0.85 else "↔️ SIDEWAYS"
        st.markdown(f'''<div style="background:#f8fafc; color:#1e293b; padding:10px; border-radius:8px; text-align:center; font-weight:bold; border: 1px solid #cbd5e1; margin-top:8px;">
            <span style="color:#f59e0b;">CE BEP: {atm + 100}</span> | <span>PCR: {pcr:.2f} ({mood})</span> | <span style="color:#ef4444;">PE BEP: {atm - 100}</span>
        </div>''', unsafe_allow_html=True)

        # OI Change Calculations
        df_comb["oi_chg_CE"] = df_comb["open_interest_CE"] - df_comb["previous_open_interest_CE"]
        df_comb["oi_chg_PE"] = df_comb["open_interest_PE"] - df_comb["previous_open_interest_PE"]
        
        return df_comb, spot, atm, live_px
        
    except Exception as e:
        st.error(f"Data Core Interrupt: {str(e)}")
        st.stop()
