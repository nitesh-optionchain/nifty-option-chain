# ==============================================================================
# ⚡ 3. STRICT HISTORICAL OHLCV EXTRACTION PIPELINE WITH HYBRID FALLBACK (Fixed Range)
# ==============================================================================
if market_engine:
    try:
        end_dt = datetime.utcnow()
        # 🎯 Optimal range selection for high-speed 5m intraday data blocks
        start_dt = end_dt - timedelta(days=2) 
        start_str = start_dt.strftime("%Y-%m-%dT00:00:00.000Z")
        end_str = end_dt.strftime("%Y-%m-%dT23:59:59.000Z")

        def unpack_nubra_points(points_list):
            if not points_list:
                return []
            return [float(p.value) for p in points_list]

        # --- PIPELINE LAYER A: NIFTY UNIFIED OHLCV MAPPING ---
        nifty_snap = market_engine.current_price("NIFTY", exchange="NSE")
        if nifty_snap and nifty_snap.price:
            st.session_state.master_storage["NIFTY"]["price"] = int(nifty_snap.price)
            st.session_state.master_storage["NIFTY"]["status"] = "LIVE"
            
            valid_history = []
            
            try:
                nifty_res = market_engine.historical_data({
                    "exchange": "NSE", "type": "INDEX", "values": ["NIFTY"],
                    "fields": ["open", "high", "low", "close", "cumulative_volume"],
                    "startDate": start_str, "endDate": end_str, "interval": "5m",
                    "intraDay": True, 
                    "realTime": False  # Locked to False for production history stability
                })
                if nifty_res and hasattr(nifty_res, 'result') and nifty_res.result and len(nifty_res.result) > 0:
                    for instrument_dict in nifty_res.result[0].values:
                        stock_chart = None
                        if isinstance(instrument_dict, dict) and "NIFTY" in instrument_dict:
                            stock_chart = instrument_dict["NIFTY"]
                        elif hasattr(instrument_dict, "NIFTY"):
                            stock_chart = getattr(instrument_dict, "NIFTY")

                        if stock_chart and hasattr(stock_chart, 'close') and stock_chart.close:
                            opens = unpack_nubra_points(stock_chart.open)
                            highs = unpack_nubra_points(stock_chart.high)
                            lows = unpack_nubra_points(stock_chart.low)
                            closes = unpack_nubra_points(stock_chart.close)
                            raw_vols = getattr(stock_chart, 'cumulative_volume', None) or getattr(stock_chart, 'volume', [])
                            vols = unpack_nubra_points(raw_vols)
                            
                            if len(opens) > 0:
                                for i in range(len(opens)):
                                    current_vol = vols[i] if i < len(vols) else 0.0
                                    valid_history.append({
                                        "open": float(opens[i]/100),
                                        "high": float(highs[i]/100),
                                        "low": float(lows[i]/100),
                                        "close": float(closes[i]/100),
                                        "volume": float(current_vol)
                                    })
            except Exception:
                pass
                
            if len(valid_history) == 0:
                mock_ltp = float(nifty_snap.price) / 100
                valid_history = [{"open": mock_ltp, "high": mock_ltp, "low": mock_ltp, "close": mock_ltp, "volume": 0.0}]
            
            st.session_state.master_storage["NIFTY"]["master_history"] = valid_history

        # --- PIPELINE LAYER B: SENSEX UNIFIED OHLCV MAPPING ---
        sensex_snap = market_engine.current_price("SENSEX", exchange="BSE")
        if sensex_snap and sensex_snap.price:
            st.session_state.master_storage["SENSEX"]["price"] = int(sensex_snap.price)
            st.session_state.master_storage["SENSEX"]["status"] = "LIVE"
            
            valid_history_s = []
            
            try:
                sensex_res = market_engine.historical_data({
                    "exchange": "BSE", "type": "INDEX", "values": ["SENSEX"],
                    "fields": ["open", "high", "low", "close", "cumulative_volume"],
                    "startDate": start_str, "endDate": end_str, "interval": "5m",
                    "intraDay": True, 
                    "realTime": False
                })
                if sensex_res and hasattr(sensex_res, 'result') and sensex_res.result and len(sensex_res.result) > 0:
                    for instrument_dict in sensex_res.result[0].values:
                        stock_chart_s = None
                        if isinstance(instrument_dict, dict) and "SENSEX" in instrument_dict:
                            stock_chart_s = instrument_dict["SENSEX"]
                        elif hasattr(instrument_dict, "SENSEX"):
                            stock_chart_s = getattr(instrument_dict, "SENSEX")

                        if stock_chart_s and hasattr(stock_chart_s, 'close') and stock_chart_s.close:
                            opens_s = unpack_nubra_points(stock_chart_s.open)
                            highs_s = unpack_nubra_points(stock_chart_s.high)
                            lows_s = unpack_nubra_points(stock_chart_s.low)
                            closes_s = unpack_nubra_points(stock_chart_s.close)
                            raw_vols_s = getattr(stock_chart_s, 'cumulative_volume', None) or getattr(stock_chart_s, 'volume', [])
                            vols_s = unpack_nubra_points(raw_vols_s)
                            
                            if len(opens_s) > 0:
                                for i in range(len(opens_s)):
                                    current_vol_s = vols_s[i] if i < len(vols_s) else 0.0
                                    valid_history_s.append({
                                        "open": float(opens_s[i]/100),
                                        "high": float(highs_s[i]/100),
                                        "low": float(lows_s[i]/100),
                                        "close": float(closes_s[i]/100),
                                        "volume": float(current_vol_s)
                                    })
            except Exception:
                pass
                
            if len(valid_history_s) == 0:
                mock_ltp_s = float(sensex_snap.price) / 100
                valid_history_s = [{"open": mock_ltp_s, "high": mock_ltp_s, "low": mock_ltp_s, "close": mock_ltp_s, "volume": 0.0}]
                
            st.session_state.master_storage["SENSEX"]["master_history"] = valid_history_s
            
    except Exception as error:
        print(f"⚠️ Live synchronization metrics downstream delay: {error}")
