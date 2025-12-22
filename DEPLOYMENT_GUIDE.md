# Streamlit Cloud 배포 가이드

## 📋 배포 전 체크리스트

### ✅ 완료된 작업
- [x] `.streamlit/config.toml` 생성 (테마 설정)
- [x] `README.md` 작성 (프로젝트 설명)
- [x] `requirements.txt` 업데이트 (yfinance 추가, MCP 제거)
- [x] `.gitignore` 확인 (`.env`, `storage.db` 제외)

### 📝 다음 단계 (사용자 수동 작업)

#### 1. GitHub 커밋 및 푸시
```bash
# 변경 파일 확인
git status

# 새 파일 추가
git add .streamlit/config.toml README.md requirements.txt

# 커밋
git commit -m "feat: Add Streamlit Cloud deployment configuration

- Add .streamlit/config.toml for theme settings
- Add comprehensive README.md
- Update requirements.txt (add yfinance, remove MCP dependencies)"

# 푸시
git push origin main
```

#### 2. Streamlit Cloud 배포

**2-1. Streamlit Cloud 접속**
1. https://share.streamlit.io 접속
2. GitHub 계정으로 로그인

**2-2. 새 앱 배포**
1. `New app` 버튼 클릭
2. 배포 설정:
   - **Repository**: `mdk72/leading-stock-strategy` (또는 변경한 저장소 이름)
   - **Branch**: `main`
   - **Main file path**: `app.py`
3. `Deploy!` 버튼 클릭

**2-3. Secrets 설정 (중요)**

배포 후 앱 설정으로 이동:
1. 앱 페이지 오른쪽 상단 `⚙️ Settings` 클릭
2. 왼쪽 메뉴에서 `Secrets` 선택
3. 아래 내용 붙여넣기:

```toml
# KIS API (한국투자증권) - 실제 값으로 교체
KIS_APP_KEY = "YOUR_APP_KEY_HERE"
KIS_SECRET_KEY = "YOUR_SECRET_KEY_HERE"
KIS_ACCOUNT_NO = "YOUR_ACCOUNT_NUMBER_HERE"
KIS_TYPE = "V"  # V: 모의, P: 실전

# Data Source Settings
RETRY_COUNT = "3"
TIMEOUT = "30"
```

4. `Save` 버튼 클릭
5. Settings → `Reboot app` 클릭하여 앱 재시작

**2-4. 배포 완료 확인**
- 앱 URL (예: `https://xxx.streamlit.app`) 접속
- 사이드바 설정이 정상적으로 표시되는지 확인
- "Run Simulation" 버튼 테스트

---

## 🔍 로컬 테스트 (선택)

배포 전 로컬에서 변경사항을 테스트하려면:

```bash
# 1. 의존성 재설치 (requirements.txt 변경됨)
pip install -r requirements.txt

# 2. 앱 실행
streamlit run app.py

# 3. 브라우저에서 http://localhost:8501 접속
```

**테스트 항목:**
- [ ] 앱이 에러 없이 시작됨
- [ ] 새 테마가 적용됨 (다크 모드)
- [ ] yfinance로 데이터 로드가 정상 작동함
- [ ] 백테스트 실행이 정상 동작함

---

## ⚠️ 주의사항

### Streamlit Cloud 무료 티어 제한
- **메모리**: 1GB RAM
- **CPU**: 공유 코어 (느릴 수 있음)
- **슬립 모드**: 7일 미사용 시 자동 슬립 (재접속 시 재시작)

### 배포 시 예상 문제 및 해결

**문제 1: "ModuleNotFoundError: No module named 'yfinance'"**
- 원인: requirements.txt에 yfinance 누락
- 해결: ✅ 이미 수정됨 (requirements.txt에 yfinance 추가)

**문제 2: 백테스트가 매우 느림**
- 원인: Streamlit Cloud 무료 티어 성능 제한
- 해결: 백테스트 기간을 짧게 설정 (예: 1~2년)

**문제 3: "Database is locked" 에러**
- 원인: SQLite는 동시 쓰기 제한
- 해결: 현재 앱은 단일 사용자 기준이므로 문제 없음

**문제 4: 재배포 시 데이터 초기화**
- 원인: Streamlit Cloud는 파일시스템이 임시 저장소
- 해결: 중요 데이터는 외부 DB (PostgreSQL 등) 사용 고려

---

## 📊 배포 후 모니터링

### 배포 로그 확인
1. Streamlit Cloud 앱 페이지
2. 우측 하단 `Manage app` 클릭
3. `Logs` 탭에서 실시간 로그 확인

### 일반적인 배포 시간
- **초기 배포**: 3~5분 (의존성 설치 포함)
- **재배포** (코드 수정 시): 1~2분

---

## 🎯 성공 기준

배포가 성공적으로 완료되면:
- ✅ 앱 URL로 접속 가능
- ✅ 사이드바에서 전략 파라미터 조정 가능
- ✅ "Run Simulation" 클릭 시 백테스트 실행됨
- ✅ 차트와 테이블이 정상 표시됨
- ✅ 4개 탭 (Overview, Portfolio, Analysis, Logs) 모두 동작

---

## 📞 추가 지원

배포 중 문제가 발생하면:
1. Streamlit Cloud 로그 확인
2. GitHub Issues에 문의
3. Streamlit Community Forum 참고: https://discuss.streamlit.io
