import os
import pandas as pd
from datetime import datetime

def save_csv_safe(df, filepath):
    """
    Pandas DataFrame을 CSV로 저장하되, PermissionError 발생 시 
    타임스탬프를 붙여서 저장을 시도하는 유틸리티 함수.
    """
    try:
        # 1. 기본 경로 시도
        df.to_csv(filepath, index=False, encoding='utf-8-sig')
        return filepath
    except PermissionError:
        # 2. 파일이 열려있는 경우 타임스탬프 추가
        base, ext = os.path.splitext(filepath)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        new_filepath = f"{base}_{timestamp}{ext}"
        print(f"[Warning] {filepath} 파일이 사용 중입니다. {new_filepath}로 저장합니다.")
        df.to_csv(new_filepath, index=False, encoding='utf-8-sig')
        return new_filepath
    except Exception as e:
        print(f"[Error] 파일 저장 중 알 수 없는 오류 발생: {e}")
        raise e
