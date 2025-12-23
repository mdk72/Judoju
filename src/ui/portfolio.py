import streamlit as st
import pandas as pd
import datetime
from src.data_loader import DataLoader

def render_portfolio(portfolio, trades, end_dt, loader_p):
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("#### Current Holdings")
    
    selected_ticker = None
    selected_name = None

    if portfolio is not None:
        if portfolio:
            # 1. Convert Dictionary to DataFrame
            # input: {ticker: {'qty':..., 'avg_price':..., 'buy_date':..., 'cost':...}}
            
            # Need names mapping. 
            name_map = {}
            if not trades.empty:
                    name_map = dict(zip(trades['Ticker'], trades['Name']))
                    
            p_data = []
            total_p_value = 0
            
            # Use passed loader instead of creating a new one
            
            for ticker, info in portfolio.items():
                name = name_map.get(ticker, ticker)
                qty = info['qty']
                avg_price = info['avg_price']
                buy_date = info.get('buy_date', None) # Get Buy Date
                
                # Calculate Duration
                duration_days = 0
                if buy_date:
                    # Robust Date Conversion
                    if isinstance(buy_date, pd.Timestamp):
                        buy_date = buy_date.date()
                    elif isinstance(buy_date, datetime.datetime):
                        buy_date = buy_date.date()
                    elif isinstance(buy_date, str):
                        try:
                            # Try ISO format first
                            buy_date = datetime.datetime.strptime(buy_date, '%Y-%m-%d').date()
                        except ValueError:
                                # Fallback or ignore
                                pass
                    
                    # Ensure end_dt is date object
                    curr_date_obj = end_dt 
                    if isinstance(curr_date_obj, str):
                            curr_date_obj = datetime.datetime.strptime(curr_date_obj, '%Y-%m-%d').date()
                            
                    # Calculate duration if both are date objects
                    if isinstance(buy_date, datetime.date) and isinstance(curr_date_obj, datetime.date):
                        duration_days = (curr_date_obj - buy_date).days
                
                # Fetch current price
                curr_price = avg_price # fallback
                try:
                    df_temp = loader_p.get_stock_data(ticker)
                    if df_temp is not None and not df_temp.empty:
                            curr_price = df_temp['Close'].iloc[-1]
                except:
                    pass
                    
                val = qty * curr_price
                profit = (curr_price - avg_price) / avg_price * 100
                
                p_data.append({
                    'Ticker': ticker,
                    'Name': name,
                    'Buy Date': buy_date, # New Column
                    'Duration': duration_days, # New Column
                    'Qty': qty,
                    'Avg Price': avg_price,
                    'Current Price': curr_price,
                    'Value': val,
                    'Profit %': profit
                })
                total_p_value += val
                
            if p_data:
                portfolio_df = pd.DataFrame(p_data)
                
                # Apply Style for Comma Formatting (Robust)
                styled_portfolio = portfolio_df.style.format({
                    "Qty": "{:,.0f}",
                    "Avg Price": "{:,.0f}",
                    "Current Price": "{:,.0f}",
                    "Value": "{:,.0f}",
                    "Profit %": "{:,.2f}%"
                })

                # CONFIG for table
                gb_config = {
                    "Ticker": st.column_config.TextColumn("Ticker", width="small"),
                    "Name": st.column_config.TextColumn("Name", width="medium"),
                    "Buy Date": st.column_config.DateColumn("Buy Date", format="YYYY-MM-DD"),
                    "Duration": st.column_config.NumberColumn("Days", format="%d days"),
                    "Qty": st.column_config.NumberColumn("Qty"),
                    "Avg Price": st.column_config.NumberColumn("Avg Price (₩)"), 
                    "Current Price": st.column_config.NumberColumn("Current Price (₩)"), 
                    "Value": st.column_config.NumberColumn("Value (₩)"),
                    "Profit %": st.column_config.NumberColumn("Profit %"),
                }
                
                st.metric("Total Holdings Value", f"₩{total_p_value:,.0f}")

                # Interactive Table
                selection = st.dataframe(
                    styled_portfolio, # Pass Styler
                    hide_index=True,
                    column_config=gb_config,
                    selection_mode="single-row",
                    on_select="rerun", # Updates session state on click
                    key="portfolio_table" 
                )
                
                # Check Selection
                if selection and selection.selection.rows:
                    selected_index = selection.selection.rows[0]
                    selected_ticker = portfolio_df.iloc[selected_index]['Ticker']
                    selected_name = portfolio_df.iloc[selected_index]['Name']
                
        else:
            st.info("Portfolio is empty.")
    else:
        st.warning("**Portfolio Data Missing.** Please click **'Run Simulation'** in the sidebar to generate the current holdings list.")

    return selected_ticker, selected_name
