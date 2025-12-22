import sys
import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

# src 폴더를 모듈 검색 경로에 추가
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))
sys.path.append(os.path.join(os.path.dirname(__file__)))

from src.data_loader import DataLoader
from src.backtester import Backtester
from src.utils import save_csv_safe

def calculate_mdd(equity_series):
    """MDD(Maximum Drawdown) 계산"""
    peak = equity_series.cummax()
    drawdown = (equity_series - peak) / peak
    return drawdown.min() * 100

def run():
    print("=== 김진 작가 주도주 전략 백테스트 시작 ===")
    
    # 1. 설정 (기간 확대: 2019년 ~ 2024년)
    start_date = '2019-01-01'
    end_date = '2024-12-20'
    
    # 2. 초기화
    loader = DataLoader(start_date=start_date, end_date=end_date)
    backtester = Backtester(loader, start_date=start_date, end_date=end_date)
    
    # 3. 실행
    result = backtester.run()
    
    if result.empty:
        print("[Error] 백테스트 결과가 없습니다.")
        return

    # 4. 결과 분석
    initial_val = backtester.initial_balance
    final_val = result['TotalValue'].iloc[-1]
    total_return = (final_val - initial_val) / initial_val * 100
    
    days = (pd.to_datetime(end_date) - pd.to_datetime(start_date)).days
    cagr = (final_val / initial_val) ** (365 / days) - 1
    cagr *= 100
    
    mdd = calculate_mdd(result['TotalValue'])
    
    print("\n" + "="*30)
    print(f" [백테스트 결과] {start_date} ~ {end_date}")
    print(f" 초기 자본: {initial_val:,.0f} 원")
    print(f" 최종 자본: {final_val:,.0f} 원")
    print(f" 총 수익률: {total_return:.2f} %")
    print(f" 연환산수익률(CAGR): {cagr:.2f} %")
    print(f" MDD: {mdd:.2f} %")
    print("="*30 + "\n")
    
    # 5. 로그 저장
    # logs 폴더 생성
    if not os.path.exists('logs'):
        os.makedirs('logs')
        
    log_df = pd.DataFrame(backtester.trade_log)
    if not log_df.empty:
        save_path = save_csv_safe(log_df, 'logs/trade_log.csv')
        print(f"[Save] 매매 로그 저장 완료: {save_path} ({len(log_df)}건)")
    
    save_path_equity = save_csv_safe(result.reset_index(), 'logs/equity_curve.csv')
    print(f"[Save] 자산 곡선 저장 완료: {save_path_equity}")

if __name__ == "__main__":
    run()
