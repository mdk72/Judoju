import streamlit as st
import pandas as pd
import numpy as np
import datetime
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots

def render_overview(equity, trades, start_dt, end_dt):
    # Calculate Key Metrics
    initial_val = equity['TotalValue'].iloc[0]
    final_val = equity['TotalValue'].iloc[-1]
    
    # Simple Return
    total_return = (final_val - initial_val) / initial_val * 100
    
    # MDD Calculation
    peak = equity['TotalValue'].cummax()
    drawdown = (equity['TotalValue'] - peak) / peak
    mdd = drawdown.min() * 100
    
    # Win Rate (from trades)
    if not trades.empty:
        sell_trades = trades[trades['Action'] == 'SELL']
        if not sell_trades.empty:
            win_trades = sell_trades[sell_trades['Note'].str.contains('Profit', na=False) & (sell_trades['Note'].str.extract(r'Profit: ([-\d.]+)%')[0].astype(float) > 0)]
            win_rate = (len(win_trades) / len(sell_trades) * 100)
            total_trades = len(sell_trades)
        else:
            win_rate = 0
            total_trades = 0
    else:
        win_rate = 0
        total_trades = 0
        
    # CAGR Calculation
    days = (equity.index[-1] - equity.index[0]).days
    if days > 0:
        cagr = (final_val / initial_val) ** (365 / days) - 1
        cagr *= 100
    else:
        cagr = 0.0

    # Layout: Metrics (Compact)
    c1, c2, c3, c4, c5 = st.columns(5)
    
    # Helper for metric card
    def metric_card(label, value, sub, color="black"):
        return f"""
        <div class="metric-container">
            <div class="metric-label">{label}</div>
            <div class="metric-value" style="color: {color};">{value}</div>
            <div class="metric-sub">{sub}</div>
        </div>
        """

    with c1:
        st.markdown(metric_card("Total Equity", f"₩{final_val:,.0f}", f"Init: ₩{initial_val:,.0f}"), unsafe_allow_html=True)

    with c2:
        color = "#27AE60" if total_return >= 0 else "#C0392B"
        st.markdown(metric_card("Total Return", f"{total_return:+.2f}%", "All-time", color), unsafe_allow_html=True)
        
    with c3:
        st.markdown(metric_card("CAGR", f"{cagr:.2f}%", "Annualized", "#27AE60"), unsafe_allow_html=True)

    with c4:
        st.markdown(metric_card("Max Drawdown", f"{mdd:.2f}%", "Worst Decline", "#C0392B"), unsafe_allow_html=True)
        
    with c5:
        st.markdown(metric_card("Win Rate", f"{win_rate:.1f}%", f"{total_trades} Trades"), unsafe_allow_html=True)

    st.markdown("<div style='margin-bottom: 20px;'></div>", unsafe_allow_html=True)

    # Layout: Charts
    # Adjusted ratio: Chart narrower, Heatmap wider
    c_chart_main, c_chart_side = st.columns([1.1, 1.4])

    with c_chart_main:
        # Dual Axis Chart: Equity + MDD (skipping unchanged lines...)
        fig = make_subplots(specs=[[{"secondary_y": True}]])
        
        # Trace 1: Equity Curve
        fig.add_trace(
            go.Scatter(x=equity.index, y=equity['TotalValue'], name="Portfolio Value", 
                        line=dict(color='#2C3E50', width=2)),
            secondary_y=False
        )
        
        # Trace 2: Drawdown (Filled Area)
        fig.add_trace(
            go.Scatter(x=equity.index, y=drawdown * 100, name="Drawdown %", 
                        fill='tozeroy', line=dict(color='#E74C3C', width=1), 
                        opacity=0.3), # Semi-transparent red
            secondary_y=True
        )

        fig.update_layout(
            template="plotly_white",
            margin=dict(l=10, r=10, t=30, b=10),
            hovermode="x unified",
            xaxis=dict(showgrid=False, title=None),
            yaxis=dict(showgrid=True, gridcolor='#F1F3F5', title=None), # Left Y
            yaxis2=dict(showgrid=False, title=None, overlaying='y', side='right', range=[mdd*1.2, 0]), # Right Y (Inverted-ish range)
            height=320, # Compact Height
            dragmode='pan',
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            title=dict(text="Equity Curve & MDD Trend", font=dict(size=14, color='#6C757D')),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
        )
        st.plotly_chart(fig, config={'scrollZoom': True})

    with c_chart_side:
        if not equity.empty:
            # 1. Prepare Data
            monthly_data = equity['TotalValue'].resample('ME').last()
            
            if len(monthly_data) > 0:
                # Current month might be partial, but we calculate it anyway
                monthly_returns = monthly_data.pct_change() * 100
                
                # Convert to Matrix: Year x Month
                heatmap_data = pd.DataFrame({
                    'Year': monthly_returns.index.year,
                    'Month': monthly_returns.index.month,
                    'Return': monthly_returns.values
                })
                # Pivot: Index=Year, Cols=1..12
                heatmap_pivot = heatmap_data.pivot(index='Year', columns='Month', values='Return')
                
                # Fill missing months with 0 or NaN
                # Ensure all months 1-12 exist
                for m in range(1, 13):
                    if m not in heatmap_pivot.columns:
                        heatmap_pivot[m] = np.nan
                heatmap_pivot = heatmap_pivot.sort_index(ascending=False).sort_index(axis=1) # Sort Years Desc, Months Asc

                # 2. Year Stats
                # Year Return
                yearly_returns = equity['TotalValue'].groupby(equity.index.year).apply(lambda x: (x.iloc[-1] / x.iloc[0] - 1) * 100)
                # Year MDD
                yearly_mdd = drawdown.groupby(drawdown.index.year).min() * 100
                
                # Sort Descending to match heatmap
                yearly_returns = yearly_returns.sort_index(ascending=False)
                yearly_mdd = yearly_mdd.sort_index(ascending=False)
                
                # 3. Visualization: Subplots (Heatmap | Table/Heatmap)
                # We will use two Heatmaps sharing Y axis to simulate the table look
                # Scale 1: Monthly Returns (e.g. -10 to +10)
                # Scale 2: Yearly Returns (e.g. -20 to +50) - Separate to distinct visible range
                
                fig_hm = make_subplots(
                    rows=1, cols=2,
                    column_widths=[0.85, 0.15], # Adjusted width
                    shared_yaxes=True,
                    horizontal_spacing=0.03,
                    subplot_titles=("Monthly Returns (%)", "Year Summary")
                )

                # Trace 1: Monthly Heatmap
                # X-axis Labels (Use Numbers to prevent merging unique keys)
                month_nums = list(range(1, 13))
                month_labels = ['J', 'F', 'M', 'A', 'M', 'J', 'J', 'A', 'S', 'O', 'N', 'D']
                
                # Color limitation: Outliers can distort scale. Clip visualization to +/- 20%?
                # Let's auto-scale but symmetrical
                z_max = max(abs(heatmap_pivot.min().min()), abs(heatmap_pivot.max().max()), 10)
                
                fig_hm.add_trace(
                    go.Heatmap(
                        z=heatmap_pivot.values,
                        x=month_nums,
                        y=heatmap_pivot.index,
                        colorscale='RdBu', 
                        zmid=0,
                        zmin=-z_max,
                        zmax=z_max,
                        text=heatmap_pivot.values,
                        texttemplate="%{text:.1f}",
                        textfont={"size": 12}, # Font size increased
                        showscale=False
                    ),
                    row=1, col=1
                )
                
                # Trace 2: Yearly Stats
                # Construct a matrix for Yearly stats (2 columns)
                # Col 1: Return, Col 2: MDD
                stat_matrix = pd.DataFrame({'Ret': yearly_returns, 'MDD': yearly_mdd})
                
                fig_hm.add_trace(
                    go.Heatmap(
                        z=stat_matrix.values,
                        x=['Return', 'MDD'],
                        y=stat_matrix.index,
                        colorscale='RdBu', 
                        zmid=0,
                        text=stat_matrix.values,
                        texttemplate="%{text:.1f}",
                        textfont={"size": 12, "weight": "bold"}, # Font size increased
                        showscale=False
                    ),
                    row=1, col=2
                )
                
                fig_hm.update_layout(
                    template="plotly_white",
                    margin=dict(l=40, r=10, t=60, b=10), # t=60 for Title Clearance
                    height=320,
                    paper_bgcolor='rgba(0,0,0,0)',
                    plot_bgcolor='rgba(0,0,0,0)',
                    yaxis=dict(autorange="reversed", type='category'), # Ensure 2024 is top
                    xaxis=dict(
                        tickmode='array',
                        tickvals=month_nums,
                        ticktext=month_labels,
                        side="bottom"
                    )
                )
                st.plotly_chart(fig_hm)

            else:
                    st.info("Not enough data for heatmap.")
        else:
                st.info("No data.")
