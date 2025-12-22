import streamlit as st
import pandas as pd
from plotly.subplots import make_subplots
import plotly.graph_objects as go
from src.data_loader import DataLoader
from src.strategy import Strategy

def render_analysis(trades, portfolio, start_dt, end_dt, strategy_params, selected_from_table, selected_from_table_name):
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("#### Individual Stock Analysis")
    # st.caption("Select a stock from the menu below or click a row in the Portfolio tab.")

    if not trades.empty:
        # Get list of tickers that were traded
        traded_tickers = trades['Ticker'].unique().tolist()
        
        # Add Current Holdings to list if not present (edge case)
        if portfolio:
                holdings_tickers = list(portfolio.keys())
                traded_tickers = list(set(traded_tickers + holdings_tickers))
        
        # Name map for display
        ticker_options = []
        name_map = {}
        if not trades.empty:
                name_map = dict(zip(trades['Ticker'], trades['Name']))
                
        for t in traded_tickers:
            name = name_map.get(t, t)
            ticker_options.append(f"{t} | {name}")
            
        # Sorting Options
        ticker_options.sort()
        
        # --- LINKING LOGIC STARTS HERE ---
        # Initialize session state for tracking selection changes
        if 'last_table_selection' not in st.session_state:
            st.session_state.last_table_selection = None
            
        # Determine current table selection identifier (Ticker)
        current_table_selection = selected_from_table # e.g. "005930" or None
        
        # Check if table selection CHANGED
        if current_table_selection != st.session_state.last_table_selection:
            # Table selection changed! Enforce update on the dropdown.
            if current_table_selection:
                target_str = f"{current_table_selection} | {selected_from_table_name}"
                
                # Verify target exists in options to prevent errors
                if target_str in ticker_options:
                    st.session_state['stock_selector'] = target_str
                else:
                    # Fallback for when portfolio item works but not in trades list?
                    ticker_options.append(target_str)
                    st.session_state['stock_selector'] = target_str
                
            # Update last known selection
            st.session_state.last_table_selection = current_table_selection
            
        # Selectbox with key 'stock_selector'
        # Initialize session state BEFORE widget creation (if not exists)
        if 'stock_selector' not in st.session_state:
            st.session_state.stock_selector = ticker_options[0] if ticker_options else None
        
        # Ensure current value is valid
        if st.session_state.stock_selector not in ticker_options and ticker_options:
            st.session_state.stock_selector = ticker_options[0]
        
        selected_option = st.selectbox(
            "Select Traded Stock", 
            ticker_options, 
            key="stock_selector"
        )
        
        if selected_option:
            selected_ticker = selected_option.split(" | ")[0]
            
            # Load OHLCV Data
            # Use same date range as configuration for consistency
            loader = DataLoader(start_date=str(start_dt), end_date=str(end_dt))
            df_stock = loader.get_stock_data(selected_ticker)
            
            if df_stock is not None:
                # 1. Calc Indicators on FULL Data (incl. Warm-up)
                # Ensure strategy_params has correct keys
                # strategy_params passed from main should be dict
                temp_strategy = Strategy(**strategy_params)
                temp_strategy.prepare_indicators(df_stock) # Calculate on full history
                
                # Calculate MA Slope on FULL data to exist before slicing
                if 'MA_Short' in df_stock.columns:
                    df_stock['MA_Slope'] = df_stock['MA_Short'].diff()
                
                # Filter df_stock to the actual simulation period for visualization
                df_view = df_stock[(df_stock.index >= pd.to_datetime(start_dt)) & (df_stock.index <= pd.to_datetime(end_dt))].copy()

                if not df_view.empty:
                    # Strategy Indicator Calculation for Visualization
                    slope_pct = df_view['Slope_Pct']
                    threshold = - (df_view['Max_Slope_60d'] * strategy_params['sell_slope_multiplier'])
                    ma_slope = df_view.get('MA_Slope', pd.Series([0]*len(df_view), index=df_view.index))

                    # Create Subplots (Price + Indicators)
                    
                    fig_stock = make_subplots(
                        rows=3, cols=1, 
                        shared_xaxes=True, 
                        vertical_spacing=0.05,
                        row_heights=[0.5, 0.25, 0.25],
                        subplot_titles=(
                            f"{selected_option} Price", 
                            "Sell Logic (Price Slope vs Threshold)",
                            "Buy Logic (MA20 Slope Turn)"
                        )
                    )

                    # 1. Price Chart (Row 1)
                    fig_stock.add_trace(go.Candlestick(
                        x=df_view.index,
                        open=df_view['Open'],
                        high=df_view['High'],
                        low=df_view['Low'],
                        close=df_view['Close'],
                        name='OHLC',
                        increasing=dict(line=dict(color='#EF5350', width=1), fillcolor='#FFFFFF'),
                        decreasing=dict(line=dict(color='#2962FF', width=1), fillcolor='#FFFFFF')
                    ), row=1, col=1)

                    # Add MA Long (Trend Filter)
                    if 'MA_Long' in df_view.columns:
                        fig_stock.add_trace(go.Scatter(
                            x=df_view.index, y=df_view['MA_Long'],
                            mode='lines', line=dict(color='#9C27B0', width=1),
                            name=f"MA {strategy_params['ma_long']} (Trend)"
                        ), row=1, col=1)

                    # Trades (Row 1)
                    stock_trades = trades[trades['Ticker'] == selected_ticker]
                    buys = stock_trades[stock_trades['Action'] == 'BUY']
                    if not buys.empty:
                        fig_stock.add_trace(go.Scatter(
                            x=buys['Date'], y=buys['Price'] * 0.98,
                            mode='markers', marker=dict(symbol='triangle-up', size=12, color='#E91E63'),
                            name='Buy'
                        ), row=1, col=1)
                    
                    sells = stock_trades[stock_trades['Action'] == 'SELL']
                    if not sells.empty:
                        fig_stock.add_trace(go.Scatter(
                            x=sells['Date'], y=sells['Price'] * 1.02,
                            mode='markers', marker=dict(symbol='triangle-down', size=12, color='#2196F3'),
                            name='Sell'
                        ), row=1, col=1)

                    # 2. Sell Indicator Chart (Row 2)
                    fig_stock.add_trace(go.Scatter(
                        x=df_view.index, y=slope_pct,
                        mode='lines', line=dict(color='#607D8B', width=1),
                        name='Price Slope (%)'
                    ), row=2, col=1)
                    
                    fig_stock.add_trace(go.Scatter(
                        x=df_view.index, y=threshold,
                        mode='lines', line=dict(color='#FF5252', width=1, dash='dash'),
                        name='Sell Threshold'
                    ), row=2, col=1)
                    
                    # 3. Buy Indicator Chart (Row 3)
                    # Prepare Tooltip Data (Standardized to PASS/FAIL)
                    cond_trend = [
                        "PASS" if (p > m) else "FAIL" 
                        for p, m in zip(df_view['Close'], df_view['MA_Long'])
                    ]
                    
                    cond_turn = []
                    prev_val = 0
                    for curr in ma_slope:
                        if curr > 0 and prev_val <= 0:
                            cond_turn.append("PASS")
                        else:
                            cond_turn.append("FAIL")
                        prev_val = curr

                    rs_scores = df_view.get('RS_Score_Pre', pd.Series([0]*len(df_view))).fillna(0).tolist()
                    rs_display = [f"{r:.1f}" for r in rs_scores]

                    is_sell_vector = [s < t for s, t in zip(slope_pct, threshold)] 
                    
                    final_signal = []
                    for t, tr, is_sell in zip(cond_trend, cond_turn, is_sell_vector):
                        if t == "PASS" and tr == "PASS":
                            final_signal.append("BUY")
                        elif is_sell:
                            final_signal.append("SELL")
                        else:
                            final_signal.append("-")
                    
                    colors = ['#EF5350' if v > 0 else '#2962FF' for v in ma_slope]
                    
                    hover_bg_colors = []
                    for sig in final_signal:
                        if sig == "BUY":
                            hover_bg_colors.append("#EF5350") 
                        elif sig == "SELL": 
                            hover_bg_colors.append("#2962FF") 
                        else:
                            hover_bg_colors.append("#FFFFFF") 

                    custom_data = [
                        [t, tr, r, sig] 
                        for t, tr, r, sig in zip(cond_trend, cond_turn, rs_display, final_signal)
                    ]

                    fig_stock.add_trace(go.Bar(
                        x=df_view.index, y=ma_slope,
                        marker_color=colors,
                        name='MA20 Slope',
                        customdata=custom_data,
                        hovertemplate=(
                            "<b>Date</b>: %{x|%Y-%m-%d}<br>" +
                            "<b>MA Slope</b>: %{y:.4f}<br><br>" +
                            "<b>1. Trend Filter (>MA60)</b>: %{customdata[0]}<br>" +
                            "<b>2. Slope Turn (Red>Blue)</b>: %{customdata[1]}<br>" +
                            "<b>3. RS Score</b>: %{customdata[2]}<br>" +
                            "<b>4. Final Signal</b>: %{customdata[3]}<br>" +
                            "<extra></extra>"
                        )
                    ), row=3, col=1)

                    fig_stock.update_traces(
                        selector=dict(name='MA20 Slope'),
                        hoverlabel=dict(
                            bgcolor=hover_bg_colors,
                            font=dict(color='black') 
                        )
                    )

                    fig_stock.update_layout(
                        height=800, 
                        template="plotly_white",
                        xaxis_rangeslider_visible=False,
                        hovermode='closest', 
                        dragmode='zoom', 
                        showlegend=True
                    )
                    
                    st.plotly_chart(fig_stock, config={'scrollZoom': True})
                else:
                    st.warning("No price data available for the selected period.")
    else:
        st.info("Run simulation to see trade traces.")
