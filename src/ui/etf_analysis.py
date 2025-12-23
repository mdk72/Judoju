import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta
from src.constants import TIGER_ETF_UNIVERSE

@st.cache_data(ttl=3600)
def get_cached_etf_ranking(_data_loader, _strategy, tickers):
    """
    ETF 랭킹 분석 결과를 캐싱합니다. (1시간 유효)
    """
    # 실제 데이터 로드 및 RS 계산
    df_dict = _data_loader.preload_data_concurrently(tickers)
    # ETF는 10억 기준 유동성 필터 적용 가능
    df_dict = _data_loader.apply_liquidity_filter(df_dict, min_amount=1_000_000_000)
    return df_dict

@st.cache_data(ttl=3600)
def calculate_component_performance(_data_loader, pdf_tickers):
    """
    ETF 구성 종목의 기간별 수익률을 계산합니다.
    """
    df_dict = _data_loader.preload_data_concurrently(pdf_tickers)
    results = {}
    
    for ticker, df in df_dict.items():
        if df is None or len(df) < 60:
            results[ticker] = {w: 0.0 for w in [1, 2, 4, 8, 12]}
            continue
            
        last_price = df['Close'].iloc[-1]
        
        # 주 단위 영업일 기준 (1주=5일, 2주=10일, 4주=20일, 8주=40일, 12주=60일)
        perf = {}
        for weeks, days in [(1, 5), (2, 10), (4, 20), (8, 40), (12, 60)]:
            try:
                base_price = df['Close'].iloc[-(days + 1)]
                perf[weeks] = round(((last_price - base_price) / base_price) * 100, 1)
            except IndexError:
                perf[weeks] = 0.0
        results[ticker] = perf
    return results

def render_etf_analysis(data_loader, strategy):
    st.markdown("## ETF Drill-down Analysis")
    st.caption("TIGER ETF 유니버스 기반 모멘텀 분석 및 상위 구성 종목 성과 추적")

    # 1. 카테고리 선택
    categories = ["전체"] + list(TIGER_ETF_UNIVERSE.keys())
    sel_cat = st.selectbox("카테고리 선택", categories)

    # 2. 데이터 유니버스 로딩
    universe = data_loader.get_etf_universe()
    cat_info = data_loader.get_etf_category_info()
    
    # 필터링
    if sel_cat != "전체":
        display_tickers = [t for t, name in universe.items() if cat_info.get(t) == sel_cat]
    else:
        display_tickers = list(universe.keys())

    # 3. RS 계산 및 유동성 필터 (캐싱 적용)
    st.markdown("### ETF RS Ranking")
    
    with st.spinner("Analyzing ETF Momentum..."):
        df_dict = get_cached_etf_ranking(data_loader, strategy, display_tickers)
        
        # 최신 날짜 기준 RS 계산
        rs_results = []
        for ticker in display_tickers:
            df = df_dict.get(ticker)
            if df is None or df.empty: continue
            
            # 마지막 거래일 기준
            last_idx = df.index[-1]
            rs_score = strategy.calculate_rs_score(df)
            
            # 슬로프 계산
            up_slope, slope_pct, max_up = strategy.calculate_slopes(df, last_idx, lookback=60)
            
            item = {
                "Ticker": ticker,
                "Name": universe[ticker],
                "Category": cat_info[ticker],
                "RS Score": round(rs_score, 2),
                "Slope(Up)": round(up_slope, 4),
                "MA20_Amount": round(df.at[last_idx, 'Amount_MA20'] / 1e8, 1) # 억 단위
            }
            rs_results.append(item)
            
        if not rs_results:
             st.warning("데이터가 부족하거나 유동성 조건에 부합하는 ETF가 없습니다.")
             return

        rs_df = pd.DataFrame(rs_results).sort_values(by="RS Score", ascending=False)

    # 테이블 표시
    st.dataframe(
        rs_df,
        column_config={
            "Ticker": st.column_config.TextColumn("코드"),
            "Name": st.column_config.TextColumn("ETF 명칭"),
            "RS Score": st.column_config.NumberColumn("RS 점수 (High=Strong)"),
            "MA20_Amount": st.column_config.NumberColumn("20일 평균 거래대금 (억)")
        },
        use_container_width=True,
        hide_index=True
    )

    st.divider()

    # 4. Drll-down: PDF 성과 분석
    st.markdown("### ETF Component Deep Dive (Top 10)")
    
    selected_etf = st.selectbox("심층 분석할 ETF 선택", rs_df['Name'].tolist())
    if selected_etf:
        etf_ticker = rs_df[rs_df['Name'] == selected_etf]['Ticker'].iloc[0]
        pdf = data_loader.get_etf_pdf(etf_ticker)
        
        st.caption(f"**{selected_etf} ({etf_ticker})** 의 상위 10개 종목 성과 (1주~12주)")
        
        # 실제 구성 종목 수익률 계산
        pdf_tickers = [stock['ticker'] for stock in pdf]
        perf_data = calculate_component_performance(data_loader, pdf_tickers)
        
        pdf_results = []
        for stock in pdf:
            ticker = stock['ticker']
            perf = perf_data.get(ticker, {1:0, 2:0, 4:0, 8:0, 12:0})
            
            pdf_results.append({
                "종목": stock['name'],
                "비중(%)": stock['weight'],
                "1주": perf.get(1, 0.0),
                "2주": perf.get(2, 0.0),
                "4주": perf.get(4, 0.0),
                "8주": perf.get(8, 0.0),
                "12주": perf.get(12, 0.0)
            })
            
        if not pdf_results:
             st.warning("선택한 ETF의 구성 종목 정보를 가져올 수 없습니다. (API 응답 없음)")
             return

        pdf_df = pd.DataFrame(pdf_results)
        
        # 컬럼 존재 여부 최종 확인
        required_cols = ['1주', '2주', '4주', '8주', '12주']
        existing_cols = [c for c in required_cols if c in pdf_df.columns]
        
        # Heatmap 스타일 적용
        def color_bg(val):
            if isinstance(val, (int, float)):
                color = '#f5f7fa'
                if val >= 5: color = '#e6f4ea' # Soft Green
                elif val > 0: color = '#f1f8e9' # V. Light Green
                elif val <= -5: color = '#fce8e6' # Soft Red
                elif val < 0: color = '#fff7e6' # Soft Orange
                return f'background-color: {color}'
            return ''

        st.table(pdf_df.style.applymap(color_bg, subset=existing_cols))
        
        # 비중 차트
        fig = px.pie(pdf_df, values='비중(%)', names='종목', title=f"{selected_etf} 구성 비중",
                     color_discrete_sequence=px.colors.sequential.RdBu)
        fig.update_layout(margin=dict(t=50, b=0, l=0, r=0), height=300)
        st.plotly_chart(fig, use_container_width=True)
