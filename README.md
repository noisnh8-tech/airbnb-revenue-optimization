[🚀 대시보드 바로가기](https://seoul-airbnb-dashboard-knwh4rregjlk2kappoqjfw4.streamlit.app/)

# 서울 에어비앤비 RevPAR 수익 최적화 가이드

서울 Airbnb 32,061개 리스팅을 분석해 RevPAR 왜곡 구조를 정량화하고,  
점유율 기반 수익 전략을 실행 가능한 대시보드로 구현한 의사결정 분석 프로젝트

---

## 1. 문제 정의

전체 리스팅의 54.3%는 비활성(Dormant/Ghost) 숙소다.  
→ RevPAR 중위값이 ₩8,868로 왜곡되어 나타남 (운영 기준 ₩47,850)

→ 왜곡된 지표 기반으로 가격 중심 의사결정이 반복되는 구조

**핵심 질문:**
> 가격이 아니라 점유율이 수익을 결정하는가?

분석 대상: Active+Operating 14,399개 (전체 32,061개 중 44.7%)

---

## 2. 핵심 인사이트

| 발견 | 결론 | 수치 |
|------|------|------|
| RevPAR 기여 구조 분해 | ✅ 점유율이 수익을 결정 | 점유율 **58.2%** / ADR **37.5%** |
| 가격 인하 효과 | ❌ 가격 인하 ≠ 점유율 상승 | 두 변수 독립적 관계 |
| 호스트 통제 변수 최우선 레버 | ✅ 슈퍼호스트 전환 | +**83.1%** RevPAR |
| 비활성 구조 | ✅ 시장 지표 왜곡 확인 | Dormant **54.3%** |

**분석이 전환된 순간:**  
"가격을 어떻게 설정할까" → **"점유율을 어떻게 방어할까"**

---

## 3. 분석 및 실행 파이프라인 (End-to-End)

RevPAR를 '점유율 기여 vs ADR 기여'로 분해하기 위해 다음 단계를 순차적으로 설계했습니다.

| 단계 | 파일 | 왜 필요한가 |
|------|------|------------|
| 01 | `01_eda_and_problem_definition.ipynb` | 비활성 리스팅의 지표 왜곡을 시각화하고, H1~H8 가설로 핵심 변수를 특정 |
| 02 | `02_data_preprocessing.ipynb` | 결측치·이상치 처리 및 외부 데이터(관광지·생활인구) 병합으로 피처 기반 마련 |
| 03 | `03_data_preparation.ipynb` | 데이터 누수 차단 + 타겟 정규화(log1p) → 모델 입력 데이터 완성 **(실행 시작점)** |
| 04 | `04_modeling.ipynb` | LightGBM + SHAP으로 RevPAR 예측 및 호스트 액션 우선순위 도출 |
| 05 | `05_market_segmentation.ipynb` | 25개 자치구를 4개 군집으로 구분 → 지역별 전략 차별화 근거 확보 |
| 06 | `06_strategy.ipynb` | 군집 특성에 따른 실행 가능한 전략 인사이트 도출 |
| 07 | `07_simulation.ipynb` | H1~H8 결과를 결합해 호스트별 액션 시나리오 수익 시뮬레이션 |
| 08 | `08_executive_summary.ipynb` | 전체 분석을 KPI 기반 의사결정 요약으로 통합 |

> 01 → 02: 가설 기반으로 수집해야 할 피처 결정  
> 02 → 03: 정제된 데이터 기반으로 모델 입력 설계  
> 03 → 04: 누수 없는 분할 데이터로 예측 모델 훈련  
> 04 → 05~07: SHAP 변수 중요도가 전략·시뮬레이션 설계의 기준  
> 07 → 08: 시뮬레이션 결과가 경영 요약의 핵심 근거

---

### 실행 방법

```bash
pip install -r requirements.txt
```
notebooks 01~08 순차 실행 (`03_data_preparation.ipynb`부터 실행 가능)

```bash
streamlit run dashboard/app.py
```

**리스크 자동 감지 (수동 실행):**
```bash
python3 risk_detection/hooks.py --trigger manual
```

**cron 자동화 설정 (Mac):**
```bash
bash setup_cron.sh
```
→ 매주 월요일 오전 8시 자동 스캔 + 이메일 알림

> ### ⚠️ 실행 안내 및 데이터 공지
>
> 1. **원본 데이터**
>    - raw 데이터 미포함 (보안 및 용량 문제)

> 2. **전처리 단계 (01~02)**
>    - raw 기반 작성으로 실행 불가 (로직 확인용)

> 3. **실행 가능 지점**
>    - `03_data_preparation.ipynb`부터 즉시 실행 가능
>    - `data/processed/` 데이터셋 사용

---

## 4. 고객/시장 분석

**가설 검증 (H1~H8):**

| 가설 | 결론 | 핵심 수치 |
|------|------|---------|
| H1: 슈퍼호스트 프리미엄 | ✅ 채택 | +83.1% RevPAR |
| H2: 숙소 유형별 RevPAR 차이 | ✅ 채택 | entire_home >> private_room (2-3배) |
| H3: 사진·평점 정상관 | ✅ 채택 | 21-35장 최적 구간 |
| H4: min_nights 2-3박 최적 | ✅ 채택 | 1박·7박+ 대비 RevPAR 우위 |
| H5: 추가요금 정책 효과 | ⚠️ 조건부 | 대형 숙소(2+ 침실)에서 효과 뚜렷 |
| H6: 공급 과잉 → RevPAR 압박 | ⚠️ 약한 지지 | 마포구 최다 공급, 약한 음의 상관 |
| H7: POI 근접성 효과 | ⚠️ 약한 지지 | 거리 증가 시 RevPAR 감소 경향 |
| H8: 인구 구조 × RevPAR | ✅ 채택 | 관광형 > 업무형 > 혼합형 > 주거형 |

**자치구 군집 분석 (K-Means k=4):**

| 군집 유형 | 자치구 특성 | 핵심 전략 |
|---------|-----------|---------|
| 관광형 고수익 | 외국인 비율 높음, RevPAR 최상위 | 가격 방어 + 콘텐츠 최적화 |
| 업무형 안정 | 주야간 인구비 높음, 안정적 점유율 | min_nights 2-3박 유지 |
| 혼합형 성장 | 공급 과잉, 슈퍼호스트 비율 낮음 | 슈퍼호스트 전환 집중 |
| 주거형 저수익 | Dormant 비율 높음, RevPAR 최하위 | 운영 상태 전환 우선 |

→ 슈퍼호스트 전환 + 사진 최적화 + min_nights 2-3박 설정이 군집 무관 공통 우선 전략

---

## 5. 결과

| KPI | 값 | 해석 |
|-----|----|------|
| TTM RevPAR 중위값 (전체) | ₩8,868 | 비활성 포함 시 왜곡 수치 |
| TTM RevPAR 중위값 (Active+Operating) | ₩47,850 | 실제 운영 기준 시장 수준 |
| Active+Operating 비율 | 44.7% | 분석 유효 리스팅 |
| Dormant/Ghost 비율 | 54.3% | 지표 왜곡 원인 |
| 점유율 RevPAR 기여 | 58.2% | ADR(37.5%) 대비 핵심 드라이버 |
| 슈퍼호스트 RevPAR 프리미엄 | +83.1% | 즉시 실행 가능한 최상위 레버 |

**모델링 성과:**

| 항목 | 내용 |
|------|------|
| 모델 | LightGBM, RandomForest, Ridge (5-Fold CV) |
| 타겟 | `log1p(ttm_revpar)` — skewness=3.76 보정 |
| 주요 피처 | `room_type`, `superhost`, `photos_count`, `rating_overall`, `min_nights` |
| 해석 도구 | SHAP — 피처별 기여도 분해 및 호스트 액션 우선순위 도출 |

---

## 6. 폴더 구조

```
airbnb-revpar-optimization/
├── notebooks/
│   ├── 01_eda_and_problem_definition.ipynb
│   ├── 02_data_preprocessing.ipynb
│   ├── 03_data_preparation.ipynb
│   ├── 04_modeling.ipynb
│   ├── 05_market_segmentation.ipynb
│   ├── 06_strategy.ipynb
│   ├── 07_simulation.ipynb
│   └── 08_executive_summary.ipynb
├── data/
│   ├── processed/
│   │   ├── seoul_airbnb_features.csv
│   │   ├── X_train_host.csv / X_test_host.csv
│   │   ├── y_train_host_log.csv / y_test_host_log.csv
│   │   ├── district_aggregated.csv / district_clustered.csv
│   │   └── cluster_listings_ao.csv
│   └── external/
│       ├── monthly_population.csv
│       └── seoul_tourism_all.csv
├── models/
│   ├── adr_lgbm.pkl / occupancy_lgbm.pkl
│   ├── isotonic_calibrator.pkl / label_encoders.pkl
│   └── feature_config.json
├── dashboard/
│   └── app.py
├── src/
│   └── predict_utils.py
├── risk_detection/
│   ├── hooks.py
│   ├── scorer.py
│   ├── email_alert.py
│   ├── duplicate_tracker.py
│   ├── sheets_sync.py
│   └── config.py
├── outputs/
│   ├── reports/
│   │   └── kpi_benchmark.md
│   └── simulation_results/
│       └── revpar_scenario_summary.csv
├── setup_cron.sh
├── requirements.txt
└── README.md
```

---

## 7. 담당 역할

- **외부 데이터 결합 및 분석 범위 확장** — 생활인구·관광지 데이터를 결합하여 지역별 수요 특성을 반영
- **데이터 정제 및 운영 기준 재정의** — Active+Operating 기준으로 분석 데이터셋을 재구성하고 시장 왜곡 구조(54.3%) 제거
- **RevPAR 구조 분석 및 핵심 변수 도출** — ADR × 점유율 구조로 수익을 분해하고, 호스트 통제 변수 중심 인사이트 도출
- **분석 흐름 설계 (End-to-End)** — 시장 분석 → 수익 진단 → 전략 도출 → 시뮬레이션까지 연결되는 분석 구조 설계
- **비즈니스 관점 결과 재구성 및 전달** — 분석 결과를 실제 의사결정(가격·점유율 전략)으로 연결되는 형태로 정리

---

*데이터: Inside Airbnb — 서울 리스팅 (2024-10-01 ~ 2025-09-30, TTM 12개월)*


