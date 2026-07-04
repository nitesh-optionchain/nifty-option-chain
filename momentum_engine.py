# momentum_engine.py
import streamlit as st

def run_momentum_tracker(df_comb, index_choice, atm, live_px):
    # 🎯 ================= DYNAMIC REAL-TIME DENSE MOMENTUM TRACKER =================
    strike_diff = 50 if index_choice == "NIFTY" else 100
    near_strikes = df_comb[(df_comb["STRIKE"] >= atm - (strike_diff*2)) & (df_comb["STRIKE"] <= atm + (strike_diff*2))]
    
    near_ce_oichg = near_strikes["oi_chg_CE"].sum()
    near_pe_oichg = near_strikes["oi_chg_PE"].sum()
    near_ce_vol = near_strikes["volume_CE"].sum()
    near_pe_vol = near_strikes["volume_PE"].sum()
       
    # ================= PRE-TABLE BOUNDARY METRIC EXTRACTORS =================
    res_stk = int(df_comb.loc[df_comb["volume_CE"].idxmax(), "STRIKE"])
    sup_stk = int(df_comb.loc[df_comb["volume_PE"].idxmax(), "STRIKE"])

    max_oi_ce, max_oi_pe = df_comb["open_interest_CE"].max(), df_comb["open_interest_PE"].max()
    max_vol_ce, max_vol_pe = df_comb["volume_CE"].max(), df_comb["volume_PE"].max()
    max_chg_ce = df_comb["oi_chg_CE"].abs().max() or 1
    max_chg_pe = df_comb["oi_chg_PE"].abs().max() or 1

    def fmt_val(val, delta, m_val):
        pct = (val/m_val*100) if m_val > 0 else 0
        return f"{val:,.0f}\n({delta:+,})\n{pct:.1f}%"

    atm_idx = (df_comb["STRIKE"] - live_px).abs().idxmin()
    d_df = df_comb.iloc[max(atm_idx-10,0): atm_idx+11].copy().reset_index(drop=True)
    
    return d_df, max_oi_ce, max_oi_pe, max_vol_ce, max_vol_pe, max_chg_ce, max_chg_pe, res_stk, sup_stk, fmt_val
