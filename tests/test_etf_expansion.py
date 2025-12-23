import sys
import os
import pandas as pd

# 프로젝트 루트 경로 추가
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.data_loader import DataLoader
from src.strategy import Strategy

def test_etf_logic():
    print("=== ETF Logic Verification ===")
    
    # 1. DataLoader & Universe Test
    loader = DataLoader(start_date='2024-01-01', end_date='2024-03-31')
    etf_universe = loader.get_universe_tickers(mode='ETF')
    
    assert len(etf_universe) > 0, "ETF 유니버스가 비어있습니다."
    print(f"[OK] ETF Universe Loaded: {len(etf_universe)} items")
    
    # 2. Mode Switching Logic
    stock_universe = loader.get_universe_tickers(mode='STOCK', kospi_n=10, kosdaq_n=5)
    assert len(stock_universe) == 15, f"Stock Universe size mismatch: {len(stock_universe)}"
    print("[OK] Mode Switching (STOCK/ETF) Success")
    
    # 3. Liquidity Filter Test (Mocking data for one ETF)
    ticker = "133690" # TIGER 미국나스닥100
    mock_df = pd.DataFrame({
        'Close': [10000] * 30,
        'Volume': [100000] * 30, # 10억
        'High': [10100] * 30,
        'Low': [9900] * 30
    }, index=pd.date_range('2024-01-01', periods=30))
    
    df_dict = {ticker: mock_df}
    filtered = loader.apply_liquidity_filter(df_dict, min_amount=500_000_000) # 5억
    assert 'Amount_MA20' in filtered[ticker].columns, "Amount_MA20 컬럼이 생성되지 않았습니다."
    print("[OK] Liquidity Filter Logic Success")
    
    # 4. Strategy RS & Slope Test
    strategy = Strategy()
    strategy.prepare_indicators(filtered[ticker])
    
    rs_score = strategy.calculate_rs_score(filtered[ticker])
    up_slope, slope_pct, max_up = strategy.calculate_slopes(filtered[ticker], filtered[ticker].index[-1])
    
    print(f"[OK] RS Score calculated: {rs_score}")
    print(f"[OK] Slopes calculated: Up={up_slope}, Pct={slope_pct}, MaxUp={max_up}")
    
    # 5. PDF Data Test
    pdf = loader.get_etf_pdf(ticker)
    assert len(pdf) == 10, "PDF Top 10 데이터 로드 실패"
    print(f"[OK] ETF PDF (Top 10) Mock Data Loaded: {pdf[0]['name']}")

if __name__ == "__main__":
    try:
        test_etf_logic()
        print("\n[SUCCESS] All ETF expansion logic tests passed.")
    except Exception as e:
        print(f"\n[FAILED] Test failed: {e}")
        sys.exit(1)
