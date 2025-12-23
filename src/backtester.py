import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from tqdm import tqdm
from .strategy import Strategy

class Backtester:
    def __init__(self, data_loader, start_date='2023-01-01', end_date='2024-06-30', strategy_params=None, universe_params=None):
        self.loader = data_loader
        # Strategy Param Injection
        if strategy_params is None:
            strategy_params = {}
        self.strategy = Strategy(**strategy_params)
        
        # Universe Params
        self.universe_params = universe_params or {'kospi_n': 200, 'kosdaq_n': 50}
        
        self.start_date = pd.to_datetime(start_date)
        self.end_date = pd.to_datetime(end_date)
        
        self.initial_balance = 100_000_000 # 1억 원
        self.balance = self.initial_balance
        self.portfolio = {} # {ticker: {'qty': 0, 'avg_price': 0, 'buy_date': date}}
        
        self.universe_data = {} # {ticker: DataFrame}
        self.universe_names = {} # {ticker: name}
        self.trade_log = []
        self.equity_curve = []
        
        # 유니버스 캐싱 (매월 갱신)
        self.target_universe = [] # 현재 월의 관심 종목 (RS 상위)

    def prepare_data(self):
        """
        백테스트 시작 전 모든 데이터 로드 (속도 향상)
        """
        print("[Backtester] 전체 유니버스 데이터 로딩 시작...")
        # Tickers extraction based on mode
        mode = self.universe_params.get('mode', 'STOCK')
        kospi_n = self.universe_params.get('kospi_n', 200)
        kosdaq_n = self.universe_params.get('kosdaq_n', 50)
        
        tickers_dict = self.loader.get_universe_tickers(kospi_n=kospi_n, kosdaq_n=kosdaq_n, mode=mode)
        self.universe_names = tickers_dict
        tickers = list(tickers_dict.keys())
        
        tickers = list(tickers_dict.keys())
        
        # 1. Concurrent Preload
        # Returns dict {ticker: DataFrame}
        loaded_data = self.loader.preload_data_concurrently(tickers)
        
        # 2. Prepare Indicators
        print("[Backtester] Calculating Indicators...")
        count = 0
        for ticker, df in loaded_data.items():
            if df is not None and not df.empty:
                self.strategy.prepare_indicators(df)
                self.universe_data[ticker] = df
                count += 1
        
        print(f"[Backtester] 데이터 로드 및 지표 계산 완료. 총 {count}개 종목 확보.")

    def calculate_atr(self, df: pd.DataFrame, window=14) -> float:
        """
        ATR(Average True Range) 계산
        """
        if len(df) < window + 1:
            return 0.0
            
        high = df['High']
        low = df['Low']
        close = df['Close'].shift(1)
        
        tr1 = high - low
        tr2 = (high - close).abs()
        tr3 = (low - close).abs()
        
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr = tr.rolling(window=window).mean().iloc[-1]
        return atr

    def run(self):
        """
        백테스트 실행 메인 루프
        """
        if not self.universe_data:
            self.prepare_data()
            
        # 날짜 인덱스 생성 (전체 유니버스의 거래일 합집합 사용)
        # 특정 종목(첫번째 키)만 쓰면 그 종목이 늦게 상장된 경우 과거 기간이 통째로 날아감
        full_dates = pd.Index([])
        for df in self.universe_data.values():
            if full_dates.empty:
                full_dates = df.index
            else:
                full_dates = full_dates.union(df.index)
        
        full_dates = full_dates.sort_values()
        
        # 백테스트 기간 내의 거래일만 필터링
        trading_days = full_dates[(full_dates >= self.start_date) & (full_dates <= self.end_date)]
        
        current_month = -1
        
        for today in tqdm(trading_days, desc="Running Backtest"):
            today_str = today.strftime('%Y-%m-%d')
            
            # --- 1. 유니버스 갱신 (Daily Rebalancing) ---
            # 주도주 전략은 '그 날'의 강세 종목을 바로 잡아야 하므로 매일 갱신
            self.update_universe(today)
            
            # --- 2. 매도 (Sell) 체크 ---
            # 보유 종목에 대해 전략 확인
            # (Dictionary 크기가 변하므로 리스트로 복사해서 순회)
            for ticker in list(self.portfolio.keys()):
                # 오늘 데이터 확인
                if ticker not in self.universe_data: continue
                
                df_full = self.universe_data[ticker]
                # 미래 데이터 참조 방지 (오늘까지 슬라이싱)
                df_slice = df_full.loc[:today]
                
                if df_slice.empty: continue
                
                curr_price = df_slice['Close'].iloc[-1]
                buy_price = self.portfolio[ticker]['avg_price']
                
                # 매도 시그널 확인
                is_sell, reason = self.strategy.check_sell_signal(df_slice, buy_price=buy_price)
                if is_sell:
                    self.sell(ticker, today, curr_price, reason)
                
            
            # --- 3. 매수 (Buy) 체크 ---
            # 보유 종목 10개 미만일 때만
            if len(self.portfolio) < 10:
                # RS 점수 상위 종목 순으로 확인
                for ticker in self.target_universe:
                    if len(self.portfolio) >= 10: break
                    if ticker in self.portfolio: continue # 이미 보유중
                    if ticker not in self.universe_data: continue
                    
                    df_full = self.universe_data[ticker]
                    df_slice = df_full.loc[:today]
                    
                    if df_slice.empty: continue
                    
                    if self.strategy.check_buy_signal(df_slice):
                        self.buy(ticker, today, df_slice)

            # --- 4. 자산 평가 (Mark-to-Market) ---
            self.update_equity(today)

        return self.get_result_df()

    def update_universe(self, today):
        """
        매일 수행:
        1. 유동성 필터 적용 (20일 평균 거래대금 100억) (Optimized: Pre-calculated Amount_MA20)
        2. RS 점수 계산 및 정렬 (Optimized: Pre-calculated RS_Score_Pre)
        3. 상위 종목 선정 -> self.target_universe 갱신
        """
        candidates = []
        
        # Optimize: Loop through dict items is fast, but operations inside were slow
        # We now use O(1) lookups instead of DataFrame slicing
        for ticker, df_full in self.universe_data.items():
            # Check if 'today' exists in this stock's data
            # Use 'today' index lookup which is fast
            try:
                # 1. Liquidity Filter (Amount_MA20 >= 10 Billion)
                # Ensure we have data for today
                if today not in df_full.index:
                    continue

                avg_amount = df_full.at[today, 'Amount_MA20']
                
                # Liquidity Threshold based on mode
                mode = self.universe_params.get('mode', 'STOCK')
                min_amount = 10_000_000_000 if mode == 'STOCK' else 1_000_000_000
                
                # Check for NaN (not enough data) or Low Liquidity
                if pd.isna(avg_amount) or avg_amount < min_amount:
                    continue
                
                # 2. RS Score (RS_Score_Pre)
                rs_score = df_full.at[today, 'RS_Score_Pre']
                
                if pd.isna(rs_score):
                    continue
                    
                candidates.append((ticker, rs_score))
                
            except KeyError:
                continue
            except Exception as e:
                # print(f"Error updating universe for {ticker}: {e}")
                continue
            
        # RS 점수 역순 정렬
        candidates.sort(key=lambda x: x[1], reverse=True)
        
        # 상위 50개 등 적당히 선정하여 타겟 풀로 지정
        self.target_universe = [x[0] for x in candidates[:50]]
        # print(f"[{today.date()}] Monthly Universe Updated: {len(self.target_universe)} candidates")

    def buy(self, ticker, date, df_slice):
        curr_price = df_slice['Close'].iloc[-1]
        atr = self.calculate_atr(df_slice)
        
        # 자금 관리: ATR(변동성) 역비례 비중
        # 기본 1% Risk Rule: (Total_Equity * 0.01) / ATR = 주식 수
        # 단, 최대 비중 10% 제한
        
        risk_per_trade = self.get_total_equity() * 0.01
        
        if atr > 0:
            qty = int(risk_per_trade / atr)
        else:
            qty = 0
            
        # 최대 비중 체크 (10%)
        max_investment = self.get_total_equity() * 0.10
        cost = qty * curr_price
        
        if cost > max_investment:
            qty = int(max_investment / curr_price)
            
        if qty <= 0: return # 살 수 없음
        if (qty * curr_price) > self.balance:
            qty = int(self.balance / curr_price) # 현금 부족 시 현금만큼만
        
        if qty > 0:
            cost = qty * curr_price
            fee = cost * 0.00015 # 유관기관 수수료 등 0.015% 가정
            
            self.balance -= (cost + fee)
            self.portfolio[ticker] = {
                'qty': qty,
                'avg_price': curr_price,
                'buy_date': date,
                'cost': cost # 포트폴리오 비중 계산용
            }
            self.log_trade(date, ticker, 'BUY', curr_price, qty, fee, f"RS Rank: High, ATR: {atr:.0f}")

    def sell(self, ticker, date, price, reason):
        if ticker not in self.portfolio: return
        
        qty = self.portfolio[ticker]['qty']
        revenue = qty * price
        fee = revenue * 0.0025 # 거래세 포함 약 0.25% 가정
        
        self.balance += (revenue - fee)
        
        # 수익률 기록
        buy_price = self.portfolio[ticker]['avg_price']
        profit_pct = (price - buy_price) / buy_price * 100
        
        self.log_trade(date, ticker, 'SELL', price, qty, fee, f"{reason} (Profit: {profit_pct:.2f}%)")
        del self.portfolio[ticker]

    def update_equity(self, date):
        equity = self.balance
        for ticker, info in self.portfolio.items():
            if ticker in self.universe_data:
                # 오늘 종가 가져오기
                try:
                    curr_price = self.universe_data[ticker].loc[date]['Close']
                    equity += info['qty'] * curr_price
                except KeyError:
                    # 오늘 데이터가 없는 경우(정지 등) 어제 가격 유지 또는 매입가 활용
                    equity += info['qty'] * info['avg_price']
        
        self.equity_curve.append({'Date': date, 'TotalValue': equity})

    def get_total_equity(self):
        # 현재 추정 자산 (현금 + 보유주식 매입가 기준 근사치, 루프 안에서는 update_equity 호출 전이라 정확하지 않을 수 있음)
        # 하지만 buy 로직에서는 정확한 현재가가 중요하므로 단순 근사 사용
        equity = self.balance
        for info in self.portfolio.values():
            equity += info['cost'] # 매입가 기준 자산 (보수적)
        return equity

    def log_trade(self, date, ticker, action, price, qty, fee, note):
        name = self.universe_names.get(ticker, ticker)
        self.trade_log.append({
            'Date': date,
            'Ticker': ticker,
            'Name': name,
            'Action': action,
            'Price': price,
            'Qty': qty,
            'Fee': fee,
            'Note': note
        })

    def get_result_df(self):
        return pd.DataFrame(self.equity_curve).set_index('Date')
