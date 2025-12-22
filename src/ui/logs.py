import streamlit as st
import pandas as pd

def render_logs(trades):
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("#### Trade Execution Log")
    
    if not trades.empty:
        display_df = trades.copy()
        display_df = display_df.sort_values(by='Date', ascending=False)
        
        # Extract Profit % from Note (for SELL trades)
        display_df['Profit %'] = display_df['Note'].str.extract(r'Profit: ([-\d.]+)%').astype(float)
        
        # Clean up Note (remove the Profit part to avoid redundancy)
        display_df['Note'] = display_df['Note'].str.replace(r'\(Profit: [-\d.]+%\)', '', regex=True).str.strip()
        
        cols = ['Date', 'Ticker', 'Name', 'Action', 'Price', 'Qty', 'Fee', 'Profit %', 'Note']
        display_df = display_df[cols]
        
        # Apply Styler for robust comma formatting
        styled_trades = display_df.style.format({
            "Price": "{:,.0f}",
            "Qty": "{:,.0f}",
            "Fee": "{:,.0f}",
            "Profit %": "{:,.2f}%"
        })

        st.dataframe(
            styled_trades, # Pass Styler

            hide_index=True,
            column_config={
                "Date": st.column_config.DateColumn("Date", format="YYYY-MM-DD"),
                "Ticker": st.column_config.TextColumn("Ticker", width="small"),
                "Name": st.column_config.TextColumn("Name", width="medium"),
                "Action": st.column_config.TextColumn("Action", width="small"),
                "Price": st.column_config.NumberColumn("Price (₩)"),
                "Qty": st.column_config.NumberColumn("Qty"),
                "Fee": st.column_config.NumberColumn("Fee (₩)"),
                "Profit %": st.column_config.NumberColumn("Profit %"),
                "Note": st.column_config.TextColumn("Details", width="large")
            }
        )
    else:
        st.info("No trades executed yet.")
