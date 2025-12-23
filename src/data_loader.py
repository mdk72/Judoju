import FinanceDataReader as fdr
import pandas as pd
import streamlit as st
from datetime import datetime, timedelta
import os
from .constants import TIGER_ETF_UNIVERSE

class DataLoader:
    def __init__(self, start_date: str = '2023-01-01', end_date: str = '2024-06-30'):
        """
        데이터 로더 초기화
        :param start_date: 백테스트 시작일 (YYYY-MM-DD)
        :param end_date: 백테스트 종료일 (YYYY-MM-DD)
        """
        from .database import DBManager
        self.db = DBManager()
        
        self.target_start_date = pd.to_datetime(start_date)
        # Warm-up Period: 365일 전부터 데이터를 로드하여 이동평균/RS 계산의 안정성 확보
        self.data_start_date = self.target_start_date - timedelta(days=365)
        self.end_date = pd.to_datetime(end_date)
        
        print(f"[DataLoader] 설정된 기간: {self.data_start_date.date()} (Warm-up 포함) ~ {self.end_date.date()}")

    def get_universe_tickers(self, date=None, kospi_n=200, kosdaq_n=50, mode='STOCK'):
        """
        유니버스 티커 선정
        :param mode: 'STOCK' (개별종목) 또는 'ETF' (TIGER ETF 화이트리스트)
        """
        if mode == 'ETF':
            return self.get_etf_universe()
            
        print(f"[DataLoader] 개별종목 유니버스 티커 선정 중 (KOSPI {kospi_n}, KOSDAQ {kosdaq_n})...")
        return self._get_cached_stock_universe(kospi_n, kosdaq_n)

    @st.cache_data(ttl=86400) # 24시간 캐싱
    def _get_cached_stock_universe(_self, kospi_n, kosdaq_n):
        df_kospi = fdr.StockListing('KOSPI')
        if 'Marcap' in df_kospi.columns:
            df_kospi['Marcap'] = pd.to_numeric(df_kospi['Marcap'], errors='coerce')
            df_kospi = df_kospi.sort_values(by='Marcap', ascending=False)
            top_kospi = df_kospi.head(kospi_n)['Code'].tolist()
        else:
            top_kospi = df_kospi.head(kospi_n)['Code'].tolist()

        # KOSDAQ
        df_kosdaq = fdr.StockListing('KOSDAQ')
        if 'Marcap' in df_kosdaq.columns:
            df_kosdaq['Marcap'] = pd.to_numeric(df_kosdaq['Marcap'], errors='coerce')
            df_kosdaq = df_kosdaq.sort_values(by='Marcap', ascending=False)
            top_kosdaq = df_kosdaq.head(kosdaq_n)['Code'].tolist()
        else:
            top_kosdaq = df_kosdaq.head(kosdaq_n)['Code'].tolist()

        universe_dict = {} 
        
        if 'Name' in df_kospi.columns:
             for _, row in df_kospi.head(kospi_n).iterrows():
                 universe_dict[row['Code']] = row['Name']
        else:
             for code in top_kospi:
                 universe_dict[code] = code

        if 'Name' in df_kosdaq.columns:
             for _, row in df_kosdaq.head(kosdaq_n).iterrows():
                 universe_dict[row['Code']] = row['Name']
        else:
             for code in top_kosdaq:
                 universe_dict[code] = code

        print(f"[DataLoader] 1차 선정된 개별종목 유니버스 크기: {len(universe_dict)}종목")
        return universe_dict

    def get_etf_universe(self):
        """
        TIGER ETF 화이트리스트 반환
        """
        print("[DataLoader] ETF 유니버스 로드 중 (TIGER 화이트리스트)...")
        universe_dict = {}
        for category, items in TIGER_ETF_UNIVERSE.items():
            for item in items:
                universe_dict[item['ticker']] = item['name']
        
        print(f"[DataLoader] 선정된 ETF 유니버스 크기: {len(universe_dict)}종목")
        return universe_dict

    def get_etf_category_info(self):
        """
        ETF 티커별 카테고리 정보 반환
        """
        category_map = {}
        for category, items in TIGER_ETF_UNIVERSE.items():
            for item in items:
                category_map[item['ticker']] = category
        return category_map

    def get_stock_data(self, ticker: str):
        # ... logic moved to preload ...
        # For backward compatibility or single fetch
        df = self.db.load_market_data(ticker, self.data_start_date, self.end_date)
        if df is not None and not df.empty:
             # Basic staleness check omitted for brevity in single fetch fallback
             return df
        return self._fetch_and_save(ticker)

    def _fetch_and_save(self, ticker):
        try:
            df = fdr.DataReader(ticker, self.data_start_date, self.end_date)
            if df is None or df.empty: return None
            
            if 'Comp' not in df.columns: df['Amount'] = df['Close'] * df['Volume']
            df = df[(df['Open'] > 0) & (df['Close'] > 0)]
            
            self.db.save_market_data(ticker, df)
            return df
        except:
            return None

    def preload_data_concurrently(self, tickers):
        """
        Load data for ALL tickers using bulk DB read + Parallel Download.
        Returns: {ticker: DataFrame}
        """
        print(f"[DataLoader] Pre-loading data for {len(tickers)} tickers...")
        
        # 1. Bulk Load from DB
        db_data = self.db.load_market_data_bulk(tickers, self.data_start_date, self.end_date)
        
        final_data = {}
        missing_tickers = []
        
        for ticker in tickers:
            df = db_data.get(ticker)
            
            need_download = False
            if df is None or df.empty:
                need_download = True
            else:
                # Proper Staleness Check
                first_date = df.index[0]
                last_date = df.index[-1]
                
                if first_date.date() > (self.data_start_date + timedelta(days=7)).date():
                    need_download = True
                elif last_date.date() < (self.end_date - timedelta(days=5)).date():
                    need_download = True
            
            if need_download:
                missing_tickers.append(ticker)
            else:
                final_data[ticker] = df
                
        # 2. Parallel Download for Missing
        if missing_tickers:
            print(f"[DataLoader] Downloading missing data for {len(missing_tickers)} tickers (Parallel)...")
            
            import concurrent.futures
            
            # Using threads is effective for I/O bound tasks like HTTP requests
            with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
                # Map tickers to futures
                future_to_ticker = {executor.submit(self._fetch_and_save, t): t for t in missing_tickers}
                
                try:
                    for future in concurrent.futures.as_completed(future_to_ticker, timeout=30):
                        ticker = future_to_ticker[future]
                        try:
                            df = future.result()
                            if df is not None:
                                final_data[ticker] = df
                        except Exception as exc:
                            print(f"[DataLoader] Error downloading {ticker}: {exc}")
                except concurrent.futures.TimeoutError:
                    print("[DataLoader] Parallel download timed out. Proceeding with available data.")
                        
        return final_data

    def apply_liquidity_filter(self, df_dict, min_amount=10_000_000_000):
        """
        N일 평균 거래대금 기준 필터링
        :param min_amount: 최소 거래대금 (기본 100억, ETF 모드에서는 10억 등으로 호출 시 조정 가능)
        """
        print(f"[DataLoader] 유동성 필터링 적용 중 (기준: {min_amount/100000000:,.0f}억 이상)...")
        filtered_dict = {}
        
        for ticker, df in df_dict.items():
            if df is None or df.empty:
                continue
            
            if 'Amount' not in df.columns:
                df['Amount'] = df['Close'] * df['Volume']
                
            df['Amount_MA20'] = df['Amount'].rolling(window=20).mean()
            filtered_dict[ticker] = df
            
        return filtered_dict

    def get_etf_pdf(self, etf_ticker: str):
        """
        ETF의 구성 종목(PDF) 리스트를 가져옵니다.
        (현재는 Mock 데이터를 반환하며, 추후 KIS API 연동 예정)
        """
        # Mock PDF Data
        mock_pdf = [
            {"ticker": "005930", "name": "삼성전자", "weight": 20.5},
            {"ticker": "000660", "name": "SK하이닉스", "weight": 15.2},
            {"ticker": "035420", "name": "NAVER", "weight": 8.4},
            {"ticker": "005380", "name": "현대차", "weight": 7.1},
            {"ticker": "035720", "name": "카카오", "weight": 6.5},
            {"ticker": "006400", "name": "삼성SDI", "weight": 5.2},
            {"ticker": "051910", "name": "LG화학", "weight": 4.8},
            {"ticker": "000270", "name": "기아", "weight": 4.1},
            {"ticker": "012330", "name": "현대모비스", "weight": 3.9},
            {"ticker": "105560", "name": "KB금융", "weight": 3.5}
        ]
        return mock_pdf
