# tables_ui.py
import re
import pandas as pd
import streamlit as st

def render_option_chain_table(d_df, max_oi_ce, max_oi_pe, max_chg_ce, max_chg_pe, max_vol_ce, max_vol_pe, live_px, atm, res_stk, sup_stk, fmt_val):
    # Base DataFrame Creation
    ui = pd.DataFrame()
    ui["CE OI\n(Δ/%)"] = d_df.apply(lambda r: fmt_val(r["open_interest_CE"], r["oi_chg_CE"], max_oi_ce), axis=1)
    ui["CE OI CHG"] = d_df.apply(lambda r: f"{r['oi_chg_CE']:+,}\n{(r['oi_chg_CE']/max_chg_ce*100):.1f}%", axis=1)
    ui["CE VOL\n(%)"] = d_df.apply(lambda r: fmt_val(r["volume_CE"], 0, max_vol_ce), axis=1)
    ui["STRIKE"] = d_df["STRIKE"].astype(str)
    ui["PE VOL\n(%)"] = d_df.apply(lambda r: fmt_val(r["volume_PE"], 0, max_vol_pe), axis=1)
    ui["PE OI CHG"] = d_df.apply(lambda r: f"{r['oi_chg_PE']:+,}\n{(r['oi_chg_PE']/max_chg_pe*100):.1f}%", axis=1)
    ui["PE OI\n(Δ/%)"] = d_df.apply(lambda r: fmt_val(r["open_interest_PE"], r["oi_chg_PE"], max_oi_pe), axis=1)

    # --- PURE DATAFRAME SPOT ROW INJECTION ---
    for i in range(len(d_df) - 1):
        s1 = float(d_df.loc[i, "STRIKE"])
        s2 = float(d_df.loc[i+1, "STRIKE"])
        if (s1 >= live_px > s2) or (s1 <= live_px < s2):
            spot_row = pd.DataFrame([{
                "CE OI\n(Δ/%)": "---", "CE OI CHG": "---", "CE VOL\n(%)": "---",
                "STRIKE": f"🔹 SPOT: {live_px:,.2f}",
                "PE VOL\n(%)": "---", "PE OI CHG": "---", "PE OI\n(Δ/%)": "---"
            }])
            ui = pd.concat([ui.iloc[:i+1], spot_row, ui.iloc[i+1:]]).reset_index(drop=True)
            break

    def style_table(row):
        s, idx = [''] * 7, row.name
        current_strike_str = str(row["STRIKE"])
        
        if "🔹 SPOT" in current_strike_str:
            return ['background-color: #0284c7; color: white; font-weight: bold; font-size: 15px; text-align: center; border-top: 2px solid #00bcff; border-bottom: 2px solid #00bcff; vertical-align: middle;'] * 7

        try: stk_num = int(re.sub(r'[^0-9]', '', current_strike_str))
        except: stk_num = 0

        s[3] = 'background-color:#f8f9fa; color:black; font-weight:bold;'
        
        if stk_num == int(atm): 
            s = ['background-color: yellow !important; color: black !important; font-weight: bold; text-align: center; white-space: pre-line;'] * 7
        else:
            try:
                if float(row.iloc[0].split('\n')[-1].replace('%','')) >= 70: s[0] = 'background-color:#1565c0; color:white;'
                if float(row.iloc[1].split('\n')[-1].replace('%','')) >= 70: s[1] = 'background-color:#2e7d32; color:white;'
                if float(row.iloc[2].split('\n')[-1].replace('%','')) >= 75: s[2] = 'background-color:#1b5e20; color:white;'
                if float(row.iloc[4].split('\n')[-1].replace('%','')) >= 75: s[4] = 'background-color:#b71c1c; color:white;'
                if float(row.iloc[5].split('\n')[-1].replace('%','')) >= 70: s[5] = 'background-color:#c62828; color:white;'
                if float(row.iloc[6].split('\n')[-1].replace('%','')) >= 70: s[6] = 'background-color:#ef6c00; color:white;'
            except: pass

        # Structural styling for all columns to expand data padding
        for i in range(7):
            s[i] += '; text-align: center !important; white-space: pre-line !important; vertical-align: middle !important; font-size: 14px !important;'

        if stk_num == res_stk: 
            for i in range(7): s[i] += '; border-top: 5px solid blue !important;'
        if stk_num == sup_stk: 
            for i in range(7): s[i] += '; border-bottom: 5px solid red !important;'
            
        return s

    # 🌟 NEW AGGRESSIVE FULL-WIDTH CSS INJECTION (LEFT-RIGHT COVERS COMPLETE SCREEN)
    st.markdown("""
        <style>
            /* 1. Main block block container padding control */
            .block-container {
                padding-left: 1rem !important;
                padding-right: 1rem !important;
                max-width: 100% !important;
            }
            /* 2. Table structural layout override */
            div[data-testid="stTable"] {
                width: 100% !important;
                margin: 0 auto !important;
            }
            div[data-testid="stTable"] table {
                width: 100% !important;
                table-layout: fixed !important;
            }
            /* 3. Headers sizing & alignment map */
            div[data-testid="stTable"] th {
                text-align: center !important;
                font-size: 14px !important;
                font-weight: 900 !important;
                background-color: #1e293b !important;
                color: #ffffff !important;
                padding: 12px 2px !important;
            }
            /* 4. Cell text internal gap layout mapping */
            div[data-testid="stTable"] td {
                padding: 10px 2px !important;
                line-height: 1.4 !important;
            }
        </style>
    """, unsafe_allow_html=True)

    # Render Table
    st.table(ui.style.apply(style_table, axis=1))