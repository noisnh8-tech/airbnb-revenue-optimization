[🚀 대시보드 바로가기](https://seoul-airbnb-dashboard-knwh4rregjlk2kappoqjfw4.streamlit.app/)

# 서울 에어비앤비 RevPAR 수익 최적화 가이드

서울 Airbnb 32,061개 리스팅 중 운영 중인 14,399개의 RevPAR 결정 구조를 정량화하고,  
점유율 기반 수익 전략을 실행 가능한 대시보드로 구현한 의사결정 분석 프로젝트

---

## 1. 문제 정의

전체 등록 리스팅의 54.3%(17,399개)는 리뷰는 있으나 최근 90일 예약이 없는 Dormant 숙소다.  
→ 전체 RevPAR 중위값 ₩8,868은 등록 숙소 전체의 현황이고, 운영 중인 숙소 기준으로는 ₩47,850이다 (5.4배).  
→ 두 집단을 함께 분석하면 운영 중단 여부와 운영 특성에 따른 수익 차이가 섞이므로, 최근 운영이 확인된 숙소로 분석 범위를 좁혔다.

**핵심 질문:**
> 가격이 아니라 점유율이 수익을 결정하는가?

분석 대상: Active+Operating 14,399개 (전체 32,061개 중 44.9%) — 리뷰가 있고 최근 90일 점유율이 0보다 큰 숙소

> Operating 조건(수익·가동 지표 8개가 모두 0이 아님)은 교차 확인용이며, Active 숙소는 전부 Operating이라 이 조건으로 추가 제외된 숙소는 없다.

---

## 2. 핵심 인사이트

| 발견 | 결론 | 수치 |
|------|------|------|
| RevPAR 분산 분해 (log) | ✅ 점유율이 RevPAR 차이를 더 많이 설명 | 점유율 **58.2%** / ADR **37.5%** |
| 가격 인하 효과 | ❌ 가격 인하 ≠ 점유율 상승 | 두 변수 독립적 관계 |
| 호스트 통제 변수 최우선 레버 | ✅ 슈퍼호스트 전환 | +**92.3%** RevPAR (중위값) |
| 운영 상태 구조 | ✅ 등록 숙소 절반 이상이 최근 90일 예약 없음 | Dormant **54.3%** |

**분석이 전환된 순간:**  
"가격을 어떻게 설정할까" → **"점유율을 어떻게 방어할까"**

---

## 3. 분석 및 실행 파이프라인 (End-to-End)

RevPAR를 '점유율 기여 vs ADR 기여'로 분해하기 위해 다음 단계를 순차적으로 설계했습니다.

| 단계 | 파일 | 왜 필요한가 |
|------|------|------------|
| 01 | `01_eda_and_problem_definition.ipynb` | 등록 숙소 전체와 운영 숙소의 RevPAR 분포 차이를 확인하고, H1~H8 가설로 핵심 변수를 특정 |
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
| H1: 슈퍼호스트 프리미엄 | ✅ 채택 | +92.3% RevPAR (중위값 ₩61,205 vs ₩31,825) |
| H2: 숙소 유형별 RevPAR 차이 | ✅ 채택 | entire_home >> private_room (2-3배) |
| H3: 사진·평점 정상관 | ✅ 채택 | 정상관 확인, 사진 수 구간 간 RevPAR 차이 유의 (Kruskal-Wallis p<0.001). 21-35장 이후에도 감소하지 않아 '최적 상한'은 아님 |
| H4: min_nights 2-3박 최적 | ✅ 채택 | 1박·7박+ 대비 RevPAR 우위 |
| H5: 추가요금 정책 효과 | ❌ 기각 | 부과 숙소 RevPAR 더 낮음 (₩34,973 vs ₩50,387) |
| H6: 공급 과잉 → RevPAR 압박 | ⚠️ 약한 지지 | 마포구 최다 공급, 약한 음의 상관 |
| H7: POI 근접성 효과 | ⚠️ 약한 지지 | 거리 증가 시 RevPAR 감소 경향 |
| H8: 인구 구조 × RevPAR | ✅ 채택 | 관광형 > 업무형 > 혼합형 > 주거형 |

**자치구 군집 분석 (K-Means k=4):**

| 군집 | 소속 자치구 · 특성 | 핵심 전략 |
|---------|-----------|---------|
| 핫플 수익형 | 강남·종로·중구·마포·용산 — 리스팅 최다, RevPAR 최상위 | 고급화 유지 + 슈퍼호스트 비율 유지 |
| 프리미엄 비즈니스 | 서초·송파·영등포·성동·노원·도봉·중랑 — RevPAR 2위, Dormant 비율 높음 | 슈퍼호스트 전환 + 즉시예약 + Dormant 재활성화 |
| 로컬 주거형 | 강동·강서·양천·은평·강북·성북·광진 — Dormant 최저, 슈퍼호스트 비율 최고 | 품질·사진·평점 개선 |
| 가성비 신흥형 | 관악·구로·금천·동작·동대문·서대문 — RevPAR 최하위, Dormant 최고 | Dormant 정리 + 비수기 프로모션 |

> H8의 관광형·업무형·혼합형·주거형은 인구 구조 기준 분류로, 위 K-Means 군집과는 별개다.

→ 슈퍼호스트 전환 + 사진 보강 + min_nights 2-3박 설정이 군집 무관 공통 우선 전략

---

## 5. 결과

| KPI | 값 | 해석 |
|-----|----|------|
| TTM RevPAR 중위값 (전체) | ₩8,868 | 등록 숙소 전체 기준 (Dormant 포함) |
| TTM RevPAR 중위값 (Active+Operating) | ₩47,850 | 실제 운영 기준 시장 수준 |
| Active+Operating 비율 | 44.9% | 분석 대상 리스팅 |
| Dormant 비율 | 54.3% | 리뷰 있음 + 최근 90일 예약 없음 (Ghost 포함 시 54.5%) |
| 점유율의 RevPAR 분산 설명 비중 | 58.2% | ADR 37.5% (log RevPAR 분산 분해) |
| 슈퍼호스트 RevPAR 프리미엄 | +92.3% | 중위값 기준 (평균 기준 +83.1%) |

**모델링 성과:**

| 항목 | 내용 |
|------|------|
| 모델 | LightGBM, RandomForest, Ridge (5-Fold CV) |
| 타겟 | `log1p(ttm_revpar)` — skewness=3.17 보정 |
| 성능 | LightGBM 5-Fold CV R² 0.847 (log 스케일), Test MAE ₩19,554 |
| 주요 피처 (SHAP 상위) | `num_reviews`, `room_type`, `rating_overall`, `district_listing_count`, `photos_count` |
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


*데이터: Inside Airbnb — 서울 리스팅 (2024-10-01 ~ 2025-09-30, TTM 12개월)*


