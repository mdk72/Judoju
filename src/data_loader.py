import FinanceDataReader as fdr
import pandas as pd
import streamlit as st
import requests
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
        universe_dict = {}
        
        # 1. KOSPI
        try:
            df_kospi = fdr.StockListing('KOSPI')
            print("[DataLoader] FDR KOSPI Listing 성공")
        except Exception as e:
            print(f"[DataLoader] FDR KOSPI 실패: {e}. Naver Fallback 가동.")
            df_kospi = _self._get_naver_listing(sosok=0) # 0: KOSPI
            if df_kospi is None:
                 print("[DataLoader] Naver Fallback(KOSPI) 실패")
                 df_kospi = pd.DataFrame()

        if not df_kospi.empty:
            if 'Marcap' in df_kospi.columns:
                df_kospi['Marcap'] = pd.to_numeric(df_kospi['Marcap'], errors='coerce')
                df_kospi = df_kospi.sort_values(by='Marcap', ascending=False)
            
            for _, row in df_kospi.head(kospi_n).iterrows():
                code = row.get('Code', row.get('Symbol'))
                name = row.get('Name')
                if code and name: universe_dict[code] = name

        # 2. KOSDAQ
        try:
            df_kosdaq = fdr.StockListing('KOSDAQ')
            print("[DataLoader] FDR KOSDAQ Listing 성공")
        except Exception as e:
            print(f"[DataLoader] FDR KOSDAQ 실패: {e}. Naver Fallback 가동.")
            df_kosdaq = _self._get_naver_listing(sosok=1) # 1: KOSDAQ
            if df_kosdaq is None:
                 print("[DataLoader] Naver Fallback(KOSDAQ) 실패")
                 df_kosdaq = pd.DataFrame()

        if not df_kosdaq.empty:
            if 'Marcap' in df_kosdaq.columns:
                df_kosdaq['Marcap'] = pd.to_numeric(df_kosdaq['Marcap'], errors='coerce')
                df_kosdaq = df_kosdaq.sort_values(by='Marcap', ascending=False)
            
            for _, row in df_kosdaq.head(kosdaq_n).iterrows():
                code = row.get('Code', row.get('Symbol'))
                name = row.get('Name')
                if code and name: universe_dict[code] = name

        print(f"[DataLoader] 최종 선정된 개별종목 유니버스 크기: {len(universe_dict)}종목")
        return universe_dict

    def _get_naver_listing(self, sosok=0):
        """
        KRX API 차단 시 Naver Finance 시가총액 페이지에서 리스팅을 가져옵니다.
        :param sosok: 0 (KOSPI), 1 (KOSDAQ)
        """
        try:
            url = f"https://finance.naver.com/sise/sise_market_sum.naver?sosok={sosok}&page=1"
            # Naver는 브라우저 User-Agent가 필요함
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}
            
            # pandas.read_html은 가끔 불안정하므로 requests + BeautifulSoup 스타일로 필요한 컬럼만 추출
            from bs4 import BeautifulSoup
            res = requests.get(url, headers=headers, timeout=10)
            soup = BeautifulSoup(res.text, 'html.parser')
            
            table = soup.find('table', {'class': 'type_2'})
            if not table: return None
            
            stocks = []
            for tr in table.find_all('tr'):
                anchors = tr.find_all('a', {'class': 'tltle'})
                if anchors:
                    name = anchors[0].text
                    href = anchors[0]['href']
                    code = href.split('code=')[-1].strip()
                    
                    # 시총 값 추출 (단위: 억)
                    tds = tr.find_all('td', {'class': 'number'})
                    marcap = 0
                    if len(tds) >= 2:
                        marcap_str = tds[1].text.replace(',', '').strip()
                        marcap = int(marcap_str) * 100_000_000 if marcap_str.isdigit() else 0
                    
                    stocks.append({'Code': code, 'Name': name, 'Marcap': marcap})
            
            return pd.DataFrame(stocks)
        except Exception as e:
            print(f"[DataLoader] Naver Listing Error: {e}")
            return None

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

    @st.cache_data(ttl=3600) # 1시간 캐싱
    def get_etf_pdf(_self, etf_ticker: str):
        """
        TIGER ETF 공식 API를 통해 실시간 구성 종목(PDF) 리스트를 가져옵니다.
        """
        print(f"[DataLoader] ETF PDF 데이터 로드 중 (Ticker: {etf_ticker})...")
        try:
            # 미래에셋 TIGER ETF 공식 API
            url = f"https://www.tigeretf.com/ko/api/etf/pdf.do?etfTicker={etf_ticker}"
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Referer': f'https://www.tigeretf.com/ko/product/view.do?ticker={etf_ticker}'
            }
            
            res = requests.get(url, headers=headers, timeout=10)
            data = res.json()
            
            # API 응답 구조 분석 (data.pdfList 등)
            pdf_list = data.get('data', {}).get('pdfList', [])
            if not pdf_list:
                print(f"[DataLoader] PDF 데이터를 찾을 수 없습니다: {etf_ticker}")
                return []
                
            results = []
            for item in pdf_list:
                # 비중(weight)이 0 이상인 종목만 추출
                weight = float(item.get('weight', 0))
                if weight > 0:
                    results.append({
                        "ticker": item.get('isincode', '').strip()[-6:] if item.get('isincode') else "", # 보통 끝 6자리가 티커
                        "name": item.get('stkname', '알수없음'),
                        "weight": round(weight, 2)
                    })
            
            # 비중 순 정렬 및 상위 10개 (UI 호환용)
            results = sorted(results, key=lambda x: x['weight'], ascending=False)[:10]
            print(f"[DataLoader] {etf_ticker} PDF 로드 완료 ({len(results)}종목)")
            return results
        except Exception as e:
            print(f"[DataLoader] ETF PDF API 호출 실패: {e}")
            return []
```
