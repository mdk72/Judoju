import sys
import os
import pandas as pd

# 프로젝트 루트 경로 추가
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.backtester import JudojuBacktester

def main():
    print("="*50)
    print("동적 리밸런싱 검증 테스트 (3개월)")
    print("="*50)

    tester = JudojuBacktester(initial_capital=100000000)

    # 짧은 기간 설정 (2024.01 ~ 2024.03) -> 1, 2, 3월 리밸런싱 확인
    start_date = "20240101"
    end_date = "20240331"
    
    try:
        results = tester.run_backtest(start_date, end_date)
        
        print("\n" + "="*50)
        print("백테스트 결과 요약")
        print("="*50)
        metrics = results['metrics']
        for k, v in metrics.items():
            if 'Val' in k or 'Cap' in k:
                print(f"{k:20}: {v:,.0f} KRW")
            else:
                print(f"{k:20}: {v}")
        
        print("\n[검증 포인트]")
        print("1. '리밸런싱 진행' 로그가 매월(1, 2, 3월) 출력되었는가?")
        print("2. 오류 없이 완료되었는가?")

    except Exception as e:
        print(f"\n백테스트 중 오류 발생: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
