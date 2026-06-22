# trading_zones.py
import streamlit as st

def render_dual_zone_framework(index_choice, chain, live_px):
    # Base configurations mapping
    strike_gap = 50 if index_choice == "NIFTY" else 100
    
    # Fallback/Default values agar table empty ho
    final_ce_strike = round(live_px / strike_gap) * strike_gap
    final_pe_strike = round(live_px / strike_gap) * strike_gap

    # EXTRACT MAX OI + VOLUME BASE FROM AVAILABLE OPTION CHAIN DATA
    try:
        if chain is not None and hasattr(chain, 'data') and not chain.data.empty:
            df_source = chain.data.copy()
            
            # 🔴 CE Side Maximum Scoring
            if 'call_open_interest' in df_source.columns and 'call_volume' in df_source.columns:
                df_source['ce_score'] = df_source['call_open_interest'].fillna(0) + df_source['call_volume'].fillna(0)
                raw_ce = float(df_source.loc[df_source['ce_score'].idxmax(), 'strike_price'])
                final_ce_strike = round((raw_ce / 100 if raw_ce > 100000 else raw_ce) / strike_gap) * strike_gap
                
            # 🟢 PE Side Maximum Scoring
            if 'put_open_interest' in df_source.columns and 'put_volume' in df_source.columns:
                df_source['pe_score'] = df_source['put_open_interest'].fillna(0) + df_source['put_volume'].fillna(0)
                raw_pe = float(df_source.loc[df_source['pe_score'].idxmax(), 'strike_price'])
                final_pe_strike = round((raw_pe / 100 if raw_pe > 100000 else raw_pe) / strike_gap) * strike_gap
    except Exception:
        pass

    # Ranges assignment
    r1 = final_ce_strike
    r2 = final_ce_strike + strike_gap
    s1 = final_pe_strike
    s2 = final_pe_strike - strike_gap

    if r1 > r2: r1, r2 = r2, r1
    if s2 > s1: s1, s2 = s2, s1

    # ==================== TABLE 1: 🔒 MAXIMUM OI + VOLUME EXPECTED ZONE ====================
    st.markdown("### 🔒 TABLE 1: MAX OI + VOLUME INSTITUTIONAL ZONE (Data-Driven Range)")
    
    t1_upper_str = f"{r1:,.0f} - {r2:,.0f}"
    t1_lower_str = f"{s2:,.0f} - {s1:,.0f}"
    t1_remark = f"🎯 Max Institutional Concentration detected at Strikes {final_ce_strike:,.0f} CE & {final_pe_strike:,.0f} PE."

    t1_col1, t1_col2, t1_col3 = st.columns([1.5, 1.5, 2])
    with t1_col1:
        st.markdown(f'<div style="background-color: #fef2f2; border-left: 4px solid #ef4444; padding: 10px; border-radius: 4px;"><small style="color: #991b1b; font-weight: bold;">🔴 MAX CE OI+VOL RESISTANCE</small><h3 style="margin:0; color: #dc2626; font-size: 20px;">{t1_upper_str}</h3></div>', unsafe_allow_html=True)
    with t1_col2:
        st.markdown(f'<div style="background-color: #f0fdf4; border-left: 4px solid #22c55e; padding: 10px; border-radius: 4px;"><small style="color: #166534; font-weight: bold;">🟢 MAX PE OI+VOL SUPPORT</small><h3 style="margin:0; color: #16a34a; font-size: 20px;">{t1_lower_str}</h3></div>', unsafe_allow_html=True)
    with t1_col3:
        st.markdown(f'<div style="background-color: #f8fafc; border: 1px solid #e2e8f0; padding: 10px; border-radius: 4px;"><small style="color: #475569; font-weight: bold;">📝 SYSTEM ALGORITHM REMARK</small><p style="margin:0; color: #334155; font-size: 14px; font-weight: 500;">{t1_remark}</p></div>', unsafe_allow_html=True)

    st.markdown("---")

    # ==================== TABLE 2: ⚡ LIVE MARKET ACTIVITY SCANNER ====================
    st.markdown("### ⚡ TABLE 2: LIVE MARKET ACTIVITY SCANNER (Real-Time Intraday Shifting)")

    driver_status = "🛡️ INSTITUTIONAL OI WALL BLOCK (Operators Holding)"
    driver_color = "#1e40af"

    try:
        if chain is not None and hasattr(chain, 'data') and not chain.data.empty:
            df_scan = chain.data.copy()
            idx_row_c = df_scan[df_scan['strike_price'] == final_ce_strike].iloc[0] if not df_scan[df_scan['strike_price'] == final_ce_strike].empty else None
            if idx_row_c is not None and 'call_volume' in idx_row_c and 'call_open_interest' in idx_row_c:
                if idx_row_c['call_volume'] > idx_row_c['call_open_interest'] * 1.5:
                    driver_status = "🔥 HEAVY INTRADAY VOLUME CHURNING (Scalpers Active)"
                    driver_color = "#ea580c"
    except Exception:
        pass

    t2_upper_str = f"{final_ce_strike:,.0f}"
    t2_lower_str = f"{final_pe_strike:,.0f}"

    t2_col1, t2_col2, t2_col3 = st.columns([1.5, 1.5, 2])
    with t2_col1:
        st.markdown(f'<div style="background-color: #fff5f5; border-left: 4px solid #f87171; padding: 10px; border-radius: 4px;"><small style="color: #991b1b; font-weight: bold;">🔥 LIVE RESISTANCE STRIKE</small><h3 style="margin:0; color: #b91c1c; font-size: 20px;">{t2_upper_str}</h3></div>', unsafe_allow_html=True)
    with t2_col2:
        st.markdown(f'<div style="background-color: #f0fdf4; border-left: 4px solid #4ade80; padding: 10px; border-radius: 4px;"><small style="color: #166534; font-weight: bold;">🌊 LIVE SUPPORT STRIKE</small><h3 style="margin:0; color: #15803d; font-size: 20px;">{t2_lower_str}</h3></div>', unsafe_allow_html=True)
    with t2_col3:
        st.markdown(f'<div style="background-color: #f8fafc; border: 1px solid #cbd5e1; padding: 10px; border-radius: 4px;"><small style="color: #334155; font-weight: bold;">⚡ CURRENT MARKET DRIVER</small><p style="margin:0; color: {driver_color}; font-size: 13px; font-weight: bold;">{driver_status}</p></div>', unsafe_allow_html=True)
