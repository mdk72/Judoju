import streamlit as st
import pandas as pd
import numpy as np
import os
import glob
import sys
import json
import datetime

# 프로젝트 루트 경로 추가
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.data_loader import DataLoader
from src.backtester import Backtester
from src.strategy import Strategy
from src.database import DBManager

# Import UI Modules
from src.ui.styles import apply_styles
from src.ui.overview import render_overview
from src.ui.portfolio import render_portfolio
from src.ui.analysis import render_analysis
from src.ui.logs import render_logs
from src.ui.etf_analysis import render_etf_analysis

# Initialize DB Manager
db = DBManager()

# -----------------------------------------------------------------------------
# Page Configuration
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="Quant Strategy Dashboard",
    layout="wide",
    initial_sidebar_state="expanded"
)

# -----------------------------------------------------------------------------
# Configuration Persistence
# -----------------------------------------------------------------------------
CONFIG_FILE = 'user_config.json'

def load_config():
    default_config = {
        'ma_short': 20,
        'ma_long': 60,
        'sell_slope_mult': 1.5,
        'weights': [0.4, 0.3, 0.2, 0.1],
        'start_date': '2023-01-01',
        'end_date': '2024-06-30',
        'kospi_n': 200,
        'kosdaq_n': 50,
        'slope_lookback': 60
    }
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                saved_config = json.load(f)
                default_config.update(saved_config)
        except Exception:
            pass # Load failed, use defaults
    return default_config

def save_config(config):
    try:
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=4)
    except Exception as e:
        print(f"Config Save Error: {e}")

# -----------------------------------------------------------------------------
# Main Logic Helper
# -----------------------------------------------------------------------------
def get_latest_file(pattern):
    files = glob.glob(pattern)
    if not files:
        return None
    files.sort(key=os.path.getmtime, reverse=True)
    return files[0]

@st.cache_resource
def get_data_loader(start_date, end_date):
    return DataLoader(start_date=start_date, end_date=end_date)

@st.cache_resource
def get_strategy(params):
    return Strategy(**params)

def run_simulation(start_date, end_date, strategy_params, universe_params):
    """
    Run backtest with given parameters and save to DB.
    """
    loader = DataLoader(start_date=start_date, end_date=end_date)
    backtester = Backtester(
        data_loader=loader,
        start_date=start_date, 
        end_date=end_date,
        strategy_params=strategy_params,
        universe_params=universe_params
    )
    
    with st.spinner("Running Simulation... (This may take a moment)"):
        result_df = backtester.run()
        
    trades_df = pd.DataFrame(backtester.trade_log)
    
    # Save Results to DB
    sim_config = {
        'start_date': start_date,
        'end_date': end_date,
        **strategy_params,
        **universe_params
    }
    db.save_simulation(sim_config, result_df, trades_df)
    
    return result_df, trades_df, backtester.portfolio

# -----------------------------------------------------------------------------
# Main Application
# -----------------------------------------------------------------------------
def main():
    # Apply CSS
    apply_styles()

    def to_date(date_str):
        try:
            return datetime.datetime.strptime(date_str, '%Y-%m-%d').date()
        except:
            return datetime.date(2023, 1, 1)

    # Load Config
    config = load_config()

    # Sidebar: Strategy Parameters
    st.sidebar.markdown("### STRATEGY CONFIG")
    
    with st.sidebar.form("simulation_form"):
        # 1. Period Settings
        with st.expander("Simulation Period", expanded=True):
            st.caption("Select backtest range")
            start_dt = st.date_input("Start Date", to_date(config['start_date']))
            end_dt = st.date_input("End Date", to_date(config['end_date']))
            
            if start_dt < datetime.date(2014, 1, 1):
                st.warning("⚠️ Data source limit: History prior to 2014 may not be available (Max ~3000 trading days).")

        # 2. Universe Settings
        with st.expander("Universe Parameters", expanded=True):
            market_mode = st.radio("Market Mode", ["STOCK", "ETF"], index=0 if config.get('market_mode', 'STOCK') == 'STOCK' else 1, horizontal=True)
            
            if market_mode == "STOCK":
                st.caption("Market Cap Ranking Filter")
                kospi_n = st.slider("KOSPI Top N", 50, 500, config.get('kospi_n', 200), 10)
                kosdaq_n = st.slider("KOSDAQ Top N", 10, 200, config.get('kosdaq_n', 50), 10)
            else:
                st.info("📊 ETF Mode: TIGER Whitelist (Total 23 items)")
                kospi_n = 0
                kosdaq_n = 0

        # 3. Strategy Logic
        with st.expander("Strategy Logic", expanded=False):
            st.caption("Moving Average & RS Weights")
            ma_short = st.slider("Short MA (Days)", 5, 50, config['ma_short'])
            ma_long = st.slider("Long MA (Days)", 20, 200, config['ma_long'])
            
            st.caption("Relative Strength Weights (3m, 6m, 12m, 1m)")
            current_weights = config.get('weights', [0.4, 0.3, 0.2, 0.1])
            col_w1, col_w2 = st.columns(2)
            with col_w1:
                w3 = st.number_input("3 Months", 0.0, 1.0, current_weights[0], 0.1)
                w12 = st.number_input("12 Months", 0.0, 1.0, current_weights[2], 0.1)
            with col_w2:
                w6 = st.number_input("6 Months", 0.0, 1.0, current_weights[1], 0.1)
                w1 = st.number_input("1 Month", 0.0, 1.0, current_weights[3], 0.1)

        # 4. Advanced Sell Logic
        with st.expander("Sell & Risk", expanded=False):
             sell_slope_mult = st.slider("Sell Slope Multiplier", 1.0, 3.0, config['sell_slope_mult'], 0.1, help="Down slope > Up slope * Multiplier")
             slope_lookback = st.slider("Sell Threshold Lookback (Days)", 20, 120, config.get('slope_lookback', 60), 10, help="Period to calculate Max Up Slope for threshold")
             use_trend_break = st.checkbox("Enable Trend Break Sell (< 20MA)", value=config.get('use_trend_break', True), help="Sell if close price drops below 20-day MA")
        
        run_btn = st.form_submit_button("Run Simulation", type="primary", use_container_width=True)

    # 5. Data Management (Outside Form)
    with st.sidebar.expander("Data Management", expanded=False):
        if st.button("Clear Market Data Cache (DB)"):
            db.clear_market_data()
            st.success("Market Data Cleared from DB!")

    # 6. Strategy Guide (Popup)
    @st.dialog("📘 주도주 매매 전략 상세 가이드 (Strategy Guide)")
    def show_strategy_guide():
        st.markdown("""
        ### 1. 유니버스 선정 (Universe Selection)
        **"어떤 종목을 살 것인가?"**
        
        *   **대상:** KOSPI 상위 200개 / KOSDAQ 상위 50개 (시가총액 기준)
        *   **거래대금 필터:** 20일 평균 거래대금 **100억 원 이상**인 종목만 거래합니다.
            *   *예시: 시총은 크지만 거래량이 적어 호가가 텅 빈 종목은 제외합니다.*

        ---

        ### 2. 매수 조건 (Buy Logic) - AND 조건
        **"이 모든 조건을 만족해야 삽니다."**

        1.  **정배열 추세 (Trend Setup):**
            *   현재가가 **20일 이동평균선** 위에 있어야 합니다.
            *   현재가가 **60일 이동평균선** 위에 있어야 합니다.
            *   *의미: 바닥에서 기고 있거나 하락세인 종목은 건드리지 않습니다.*
        
        2.  **모멘텀 점수 (RS Score):**
            *   최근 1년치 주가 상승률에 가중치를 두어 점수를 매깁니다.
            *   **공식:** `(3개월*0.4) + (6개월*0.3) + (12개월*0.2) + (1개월*0.1)`
            *   이 점수가 전체 유니버스 중 **상위 10등** 안에 들어야 매수 후보가 됩니다.
            *   *예시: 1년 전보다 2배 올랐어도, 최근 3개월 동안 비실비실하면 점수가 낮아집니다.*

        ---

        ### 3. 매도 조건 (Sell Logic) - OR 조건
        **"이 중 하나라도 걸리면 팝니다."**

        1.  **추세 이탈 (Trend Break) - [옵션 선택 가능]**
            *   **종가가 20일 이동평균선 아래로 떨어지면** 즉시 매도합니다.
            *   *설정창에서 'Enable Trend Break Sell' 체크박스로 켜고 끌 수 있습니다.*
            *   **체크 해제 시:** 이평선이 깨져도 팔지 않고, 아래의 '기울기 매도' 조건만 기다립니다. (수익 극대화 vs 안전 추구)

        2.  **주도주 탈락 (Rank Logic):**
            *   RS 점수 순위가 너무 떨어지면(예: 30위 밖으로 밀려남) 교체 매매를 위해 매도합니다.

        3.  **기울기 매도 (Slope Protection) - **핵심 로직****
            *   **"오를 때보다 내릴 때 더 가파르면 도망쳐라"**
            *   최근 60일 동안 **가장 가파르게 올랐던 각도(Max Up Slope)**를 기억합니다.
            *   현재 하락 각도가 그 상승 각도보다 **일정 비율(Multiplier)** 이상 가파르면 매도합니다.
            *   *예시:*
                *   주가가 2달 동안 천천히 +10% 올랐는데 (각도 완만)
                *   단 3일 만에 -5%가 빠진다면? (각도 급격함)
                *   **"이건 건전한 조정이 아니라 폭락의 징조다"**라고 판단하여 즉시 매도합니다.
        """)

    if st.sidebar.button("전략 가이드 (상세보기)", use_container_width=True):
        show_strategy_guide()

    # Header
    st.markdown("### LEADING STOCK QUANT STRATEGY")
    st.markdown("Running Status: **Active** | Environment: **Local (Mock)**")
    
    # State Management for Simulation Results
    if 'sim_equity' not in st.session_state:
        st.session_state.sim_equity = None
        st.session_state.sim_trades = None
        st.session_state.sim_portfolio = None

    if run_btn:
        # Save New Config
        new_config = {
            'ma_short': ma_short,
            'ma_long': ma_long,
            'sell_slope_mult': sell_slope_mult,
            'weights': [w3, w6, w12, w1],
            'start_date': str(start_dt),
            'end_date': str(end_dt),
            'market_mode': market_mode,
            'kospi_n': kospi_n,
            'kosdaq_n': kosdaq_n,
            'slope_lookback': slope_lookback,
            'use_trend_break': use_trend_break
        }
        save_config(new_config)
        
        params = {
            'ma_short': ma_short,
            'ma_long': ma_long,
            'sell_slope_multiplier': sell_slope_mult,
            'rs_weights': (w3, w6, w12, w1),
            'slope_lookback': slope_lookback,
            'use_trend_break': use_trend_break
        }
        
        universe_params = {
            'mode': market_mode,
            'kospi_n': kospi_n,
            'kosdaq_n': kosdaq_n
        }
        
        equity, trades, portfolio = run_simulation(str(start_dt), str(end_dt), params, universe_params)
        st.session_state.sim_equity = equity
        st.session_state.sim_trades = trades
        st.session_state.sim_portfolio = portfolio
        st.rerun() 
    
    # Determine which data to show
    if st.session_state.sim_equity is None:
        last_config, equity, trades = db.get_latest_simulation()
        portfolio = None 
        data_source = "Latest DB Record"
    else:
        equity = st.session_state.sim_equity
        trades = st.session_state.sim_trades
        portfolio = st.session_state.sim_portfolio
        data_source = "Simulation Result"

    if equity is None or equity.empty:
        st.info("No trading data found. Please run a simulation from the sidebar.")
        return

    st.caption(f"Showing Data Source: **{data_source}**")

    # Tabs
    tab_overview, tab_portfolio, tab_analysis, tab_etf, tab_logs = st.tabs([
        "Overview", 
        "Portfolio", 
        "Analysis", 
        "ETF Analysis",
        "Logs"
    ])

    # 1. Overview Tab
    with tab_overview:
        render_overview(equity, trades, start_dt, end_dt)

    # 2. Portfolio Tab
    sel_ticker = None
    sel_name = None
    with tab_portfolio:
        # Pass cached loader
        loader_p = get_data_loader(str(start_dt), str(end_dt))
        sel_ticker, sel_name = render_portfolio(portfolio, trades, end_dt, loader_p)

    # 3. Analysis Tab
    with tab_analysis:
        # Reconstruct current strategy params for Visualization
        current_strategy_params = {
            'ma_short': ma_short,
            'ma_long': ma_long,
            'sell_slope_multiplier': sell_slope_mult,
            'rs_weights': (w3, w6, w12, w1),
            'slope_lookback': slope_lookback,
            'use_trend_break': use_trend_break
        }
        # Pass cached loader
        loader_a = get_data_loader(str(start_dt), str(end_dt))
        render_analysis(trades, portfolio, start_dt, end_dt, current_strategy_params, sel_ticker, sel_name, loader_a)

    # 4. ETF Analysis Tab
    with tab_etf:
        current_strategy_params = {
            'ma_short': ma_short,
            'ma_long': ma_long,
            'sell_slope_multiplier': sell_slope_mult,
            'rs_weights': (w3, w6, w12, w1),
            'slope_lookback': slope_lookback,
            'use_trend_break': use_trend_break
        }
        loader_etf = get_data_loader(str(start_dt), str(end_dt))
        strategy_etf = get_strategy(current_strategy_params)
        render_etf_analysis(loader_etf, strategy_etf)

    # 5. Logs Tab
    with tab_logs:
        render_logs(trades)

if __name__ == "__main__":
    main()
