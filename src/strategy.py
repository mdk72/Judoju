import numpy as np
import pandas as pd
from scipy.stats import linregress

class Strategy:
    def __init__(self, ma_short=20, ma_long=60, sell_slope_multiplier=1.5, rs_weights=(0.4, 0.3, 0.2, 0.1), slope_lookback=60, use_trend_break=True):
        """
        :param ma_short: 단기 이동평균 기간 (기본 20)
        :param ma_long: 장기 이동평균 기간 (기본 60)
        :param sell_slope_multiplier: 매도 시 기울기 비교 배수 (기본 1.5)
        :param rs_weights: RS 점수 가중치 (3개월, 6개월, 12개월, 1개월 순)
        :param slope_lookback: 매도 기준(Threshold) 산출을 위한 기간 (기본 60일)
        :param use_trend_break: 추세 이탈(20MA 하회) 매도 활성화 여부
        """
        self.ma_short = ma_short
        self.ma_long = ma_long
        self.sell_slope_multiplier = sell_slope_multiplier
        self.rs_weights = rs_weights
        self.slope_lookback = slope_lookback
        self.use_trend_break = use_trend_break

    def prepare_indicators(self, df: pd.DataFrame):
        """
        벡터화된 방식으로 지표를 미리 계산하여 DataFrame에 추가
        :param df: OHLCV DataFrame
        """
        # 이평선
        df['MA_Short'] = df['Close'].rolling(window=self.ma_short).mean()
        df['MA_Long'] = df['Close'].rolling(window=self.ma_long).mean()
        
        # 1. Slope Calculation (Vectorized for window=5)
        # 5일 기울기는 단기 추세용이므로 하드코딩 유지하거나 파라미터화 가능 (여기선 5일 고정)
        
        # Using rolling apply (moderately fast)
        numerator = df['Close'].rolling(window=5).apply(lambda y: 5 * np.dot(np.arange(5), y) - 10 * np.sum(y), raw=True)
        slope = numerator / 50.0
        
        df['Slope'] = slope
        
        # Normalized Slope (%)
        df['Slope_Pct'] = (slope / df['Close']) * 100
        
        # 2. Max Up Slope (Dynamic Lookback)
        # Shift(1) because we look at PREVIOUS days
        pos_slope = df['Slope_Pct'].where(df['Slope_Pct'] > 0, 0)
        df['Max_Slope_60d'] = pos_slope.rolling(window=self.slope_lookback).max().shift(1)
        
        # --- Pre-calculate Liquidity (Amount) for Optimization ---
        # Instead of calculating it 1000s of times in the loop
        if 'Amount' not in df.columns:
            df['Amount'] = df['Close'] * df['Volume']
        
        # 20-day Average Amount
        df['Amount_MA20'] = df['Amount'].rolling(window=20).mean()

        # 3. RS Score
        df['R_1m'] = df['Close'].pct_change(periods=20)
        df['R_3m'] = df['Close'].pct_change(periods=60)
        df['R_6m'] = df['Close'].pct_change(periods=120)
        df['R_12m'] = df['Close'].pct_change(periods=250)
        
        w3, w6, w12, w1 = self.rs_weights
        df['RS_Score_Pre'] = (w3 * df['R_3m']) + (w6 * df['R_6m']) + (w12 * df['R_12m']) + (w1 * df['R_1m'])
        df['RS_Score_Pre'] = df['RS_Score_Pre'] * 100

    def get_slope(self, series: pd.Series, window: int = 5) -> float:
         # Deprecated
         pass

    def calculate_rs_score(self, df: pd.DataFrame) -> float:
        """
        RS 점수 계산
        """
        # 벡터화된 점수 사용
        if 'RS_Score_Pre' in df.columns:
            score = df['RS_Score_Pre'].iloc[-1]
            if pd.isna(score): return 0.0
            return score

        if len(df) < 250:
            return 0.0

        p_now = df['Close'].iloc[-1]
        
        try:
            p_1m = df['Close'].iloc[-20]
            p_3m = df['Close'].iloc[-60]
            p_6m = df['Close'].iloc[-120]
            p_12m = df['Close'].iloc[-250]
        except IndexError:
            return 0.0

        r_1m = (p_now - p_1m) / p_1m
        r_3m = (p_now - p_3m) / p_3m
        r_6m = (p_now - p_6m) / p_6m
        r_12m = (p_now - p_12m) / p_12m

        w3, w6, w12, w1 = self.rs_weights
        rs_score = (w3 * r_3m) + (w6 * r_6m) + (w12 * r_12m) + (w1 * r_1m)
        return rs_score * 100

    def check_buy_signal(self, df: pd.DataFrame) -> bool:
        """
        매수 신호:
        1. 단기 이평선 기울기가 양수로 전환
        2. 현재 주가가 장기 이평선 위에 위치
        """
        if 'MA_Short' in df.columns and 'MA_Long' in df.columns:
            curr_price = df['Close'].iloc[-1]
            curr_ma_long = df['MA_Long'].iloc[-1]
            
            # 1. 장기 이평선 위
            if curr_price <= curr_ma_long:
                return False
                
            # 2. 단기 이평선 기울기 양수 전환
            ma_short_today = df['MA_Short'].iloc[-1]
            ma_short_prev = df['MA_Short'].iloc[-2]
            ma_short_prev2 = df['MA_Short'].iloc[-3]
            
            slope_now = ma_short_today - ma_short_prev
            slope_prev = ma_short_prev - ma_short_prev2
            
            if slope_prev <= 0 and slope_now > 0:
                return True
                
            return False

        # Fallback
        return False

    def check_sell_signal(self, df: pd.DataFrame, buy_price: float = None) -> tuple:
        """
        매도 신호:
        1. 추세 이탈 (Trend Break): 종가 < 20이동평균선
        2. 기울기 매도 (Slope Profit Protection): 하락 기울기 > 상승 기울기 * Multiplier
        """
        if df.empty: return False, ""
        
        curr_price = df['Close'].iloc[-1]
        
        # 1. Trend Break (Condition: Close < 20MA)
        if self.use_trend_break:
            if 'MA_Short' in df.columns:
                ma_short = df['MA_Short'].iloc[-1]
                if curr_price < ma_short:
                     return True, f"Trend Break (Price < 20MA)"

        # 2. Slope Logic
        if 'Slope_Pct' in df.columns and 'Max_Slope_60d' in df.columns:
            slope_current = df['Slope_Pct'].iloc[-1]
            max_up_slope = df['Max_Slope_60d'].iloc[-1]
            
            if pd.isna(slope_current) or pd.isna(max_up_slope):
                return False, ""
                
            if slope_current >= 0:
                pass # Rising
            elif max_up_slope == 0:
                pass 
            elif abs(slope_current) > (max_up_slope * self.sell_slope_multiplier):
                 return True, f"Deep Correction (Down:{slope_current:.1f} > Up:{max_up_slope:.1f}*{self.sell_slope_multiplier})"
            
        return False, ""

    def calculate_slopes(self, df: pd.DataFrame, target_date, lookback=60):
        """
        특정 날짜 기준의 상승/하락 슬로프를 계산합니다.
        """
        if 'Slope_Pct' not in df.columns:
            self.prepare_indicators(df)
            
        try:
            up_slope = df.at[target_date, 'Slope']
            slope_pct = df.at[target_date, 'Slope_Pct']
            max_up = df.at[target_date, 'Max_Slope_60d']
            return up_slope, slope_pct, max_up
        except:
            return 0.0, 0.0, 0.0
