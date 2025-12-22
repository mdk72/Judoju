# 주도주 퀀트 매매 전략 백테스터

[![Streamlit App](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://your-app-url.streamlit.app)

한국 주식시장에서 주도주(Leading Stock) 모멘텀 전략을 백테스팅하고 시각화하는 Streamlit 대시보드입니다.

## 주요 기능

### 📊 백테스팅 시스템
- **기간 설정**: 사용자 정의 백테스팅 기간 (2014년 이후)
- **유니버스 필터링**: KOSPI/KOSDAQ 시가총액 상위 종목 자동 선정
- **모멘텀 점수**: RS(Relative Strength) 기반 주도주 선정

### 📈 전략 로직
- **매수 조건**: 정배열(20MA/60MA) + RS 점수 상위 10위
- **매도 조건**: 추세 이탈 / 기울기 급락 / 주도주 탈락
- **리스크 관리**: 하락 기울기 > 상승 기울기 * 배수 시 손절

### 🎨 시각화
- **Overview**: 자본 곡선, 누적 수익률, 최대 낙폭(MDD)
- **Portfolio**: 현재 보유 종목 및 개별 차트 분석
- **Analysis**: 월별/종목별 수익률 히트맵
- **Logs**: 전체 거래 내역 및 필터링

---

## 로컬 실행 방법

### 1. 저장소 클론
```bash
git clone https://github.com/mdk72/leading-stock-strategy.git
cd leading-stock-strategy
```

### 2. 의존성 설치
```bash
pip install -r requirements.txt
```

### 3. 환경변수 설정 (선택)
`.env` 파일 생성 (한국투자증권 API 사용 시):
```env
KIS_APP_KEY=YOUR_APP_KEY
KIS_SECRET_KEY=YOUR_SECRET_KEY
KIS_ACCOUNT_NO=YOUR_ACCOUNT_NUMBER
KIS_TYPE=V  # V: 모의, P: 실전
```

### 4. 앱 실행
```bash
streamlit run app.py
```

브라우저에서 `http://localhost:8501` 접속

---

## Streamlit Cloud 배포

### 배포 절차

1. **저장소 준비**
   - GitHub에 프로젝트 업로드
   - `app.py`, `requirements.txt`, `.streamlit/config.toml` 확인

2. **Streamlit Cloud 배포**
   - https://share.streamlit.io 접속
   - `New app` → 저장소 선택 → `app.py` 지정
   - `Deploy` 클릭

3. **Secrets 설정** (API 사용 시)
   - 배포 후 Settings → Secrets
   - 아래 내용 붙여넣기:
   ```toml
   KIS_APP_KEY = "YOUR_APP_KEY"
   KIS_SECRET_KEY = "YOUR_SECRET_KEY"
   KIS_ACCOUNT_NO = "YOUR_ACCOUNT_NUMBER"
   KIS_TYPE = "V"
   ```

4. **앱 재시작**
   - Settings → Reboot app

---

## 프로젝트 구조

```
주도주매매/
├── app.py                   # Streamlit 앱 엔트리포인트
├── requirements.txt         # Python 의존성
├── .streamlit/
│   └── config.toml         # Streamlit 설정 (테마, 서버)
├── src/
│   ├── data_loader.py      # 주가 데이터 로더 (yfinance)
│   ├── strategy.py         # 주도주 전략 로직
│   ├── backtester.py       # 백테스팅 엔진
│   ├── database.py         # SQLite DB 관리
│   └── ui/                 # UI 모듈 (styles, overview, portfolio 등)
├── tests/                  # 테스트 스크립트
└── storage.db              # SQLite 데이터베이스 (로컬)
```

---

## 기술 스택

- **웹 프레임워크**: Streamlit
- **데이터 분석**: Pandas, NumPy
- **시각화**: Plotly
- **데이터 소스**: yfinance (Yahoo Finance)
- **통계 분석**: SciPy
- **데이터베이스**: SQLite

---

## 주의사항

### Streamlit Cloud 무료 티어 제한
- **메모리**: 1GB
- **CPU**: 공유 코어
- **슬립 모드**: 7일 미사용 시 자동 슬립

### 권장 사항
- 대용량 백테스트(10년 이상)는 로컬에서 실행
- 초기 데이터 로딩 시간 약 30초~1분 소요 가능
- DB 파일(`storage.db`)은 재배포 시 초기화됨

---

## 라이선스

이 프로젝트는 개인 학습 및 연구 목적으로 제작되었습니다.

**면책 조항**: 이 프로그램은 교육용이며, 실제 투자 권유가 아닙니다. 투자 손실에 대한 책임은 사용자에게 있습니다.

---

## 참고 자료

- [Streamlit Documentation](https://docs.streamlit.io)
- [yfinance GitHub](https://github.com/ranaroussi/yfinance)
- 주도주 퀀트 전략 (김진 작가)
