import os
import logging
from fastmcp import FastMCP
from dotenv import load_dotenv

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("kis-mcp-server")

# 환경 변수 로드
load_dotenv()

# MCP 서버 초기화
mcp = FastMCP("kis-mcp")

# KIS API 관련 상수 (환경 변수에서 로드 예정)
APP_KEY = os.getenv("KIS_APP_KEY", "")
APP_SECRET = os.getenv("KIS_APP_SECRET", "")
ACCOUNT_NO = os.getenv("KIS_ACCOUNT", "")
IS_VIRTUAL = os.getenv("KIS_VIRTUAL", "true").lower() == "true"

BASE_URL = "https://openapivts.koreainvestment.com:29443" if IS_VIRTUAL else "https://openapi.koreainvestment.com:9443"

@mcp.tool()
def get_account_balance(account_number: str = "") -> str:
    """
    계좌 잔고를 조회합니다.
    
    Args:
        account_number: 조회할 계좌번호 (기본값: 환경변수 설정값)
    """
    target_acc = account_number if account_number else ACCOUNT_NO
    logger.info(f"Checking balance for account: {target_acc}")
    
    # [Mocking Mode] 실제 API 연결 전 테스트용
    return f"""
    [MOCK Data] 계좌 잔고 조회 결과
    --------------------------------
    계좌번호: {target_acc}
    예수금: 10,000,000 원
    총 평가 금액: 10,000,000 원
    보유 종목: 없음
    --------------------------------
    (현재는 API 연결 테스트를 위한 가짜 데이터입니다.)
    """

@mcp.tool()
def get_current_price(ticker: str) -> str:
    """
    주식의 현재가를 조회합니다.
    
    Args:
        ticker: 종목 코드 (예: 005930)
    """
    logger.info(f"Checking price for ticker: {ticker}")
    
    # [Mocking Mode]
    mock_price = "70,000" if ticker == "005930" else "15,000"
    return f"종목 {ticker}의 현재가(Mock): {mock_price} 원"

if __name__ == "__main__":
    logger.info("Starting KIS MCP Server...")
    # stdio 모드로 실행 (MCP 클라이언트와 통신)
    mcp.run()
