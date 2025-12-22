@echo off
chcp 65001 > nul
echo [INFO] 주도주 자동매매 시스템 환경 설정을 시작합니다...

:: 1. 파이썬 의존성 설치
echo [INFO] Python 라이브러리를 설치합니다...
pip install -r requirements.txt
pip install -r kis_mcp_server/requirements.txt

:: 2. Antigravity 규칙 설정 (GEMINI.md)
echo [INFO] Antigravity User Rules(GEMINI.md)를 설정합니다...
set "GEMINI_DIR=C:\Users\%USERNAME%\.gemini"
if not exist "%GEMINI_DIR%" (
    mkdir "%GEMINI_DIR%"
)
copy /Y "GEMINI_UPDATED.md" "%GEMINI_DIR%\GEMINI.md" > nul
if %ERRORLEVEL% EQU 0 (
    echo [OK] GEMINI.md 설정 완료!
) else (
    echo [ERROR] GEMINI.md 복사 실패!
)

:: 3. MCP 설정 파일 복사 (선택 사항)
echo [INFO] MCP 설정 파일(mcp_config.json) 업데이트를 시도합니다...
set "MCP_CONFIG_DIR=C:\Users\%USERNAME%\.gemini\antigravity"
if not exist "%MCP_CONFIG_DIR%" (
    mkdir "%MCP_CONFIG_DIR%"
)

:: 주의: 기존 파일이 있으면 백업 후 덮어쓰기
if exist "%MCP_CONFIG_DIR%\mcp_config.json" (
    copy /Y "%MCP_CONFIG_DIR%\mcp_config.json" "%MCP_CONFIG_DIR%\mcp_config.json.bak" > nul
    echo [INFO] 기존 설정은 mcp_config.json.bak으로 백업되었습니다.
)

copy /Y "mcp_config_fixed.json" "%MCP_CONFIG_DIR%\mcp_config.json" > nul
if %ERRORLEVEL% EQU 0 (
    echo [OK] MCP 설정 업데이트 완료!
) else (
    echo [ERROR] MCP 설정 복사 실패! (직접 mcp_config_fixed.json 내용을 복사해서 사용하세요.)
)

echo.
echo ========================================================
echo [완료] 모든 설정이 마무리되었습니다.
echo 프로그램을 재시작하거나 Refresh 버튼을 눌러주세요.
echo ========================================================
pause
