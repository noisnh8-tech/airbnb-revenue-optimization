# airbnb-revenue-optimization
Airbnb revenue optimization analysis using RevPAR decomposition and simulation
## 📌 프로젝트 목적
서울 Airbnb 데이터를 기반으로 RevPAR(객실당 수익)에 영향을 미치는 핵심 요인을 분석하고,
호스트 의사결정을 위한 데이터 기반 도구 설계

## 🔍 문제 정의
- 비활성 숙소 54.3% → 시장 왜곡
- 점유율이 수익의 핵심 변수 (58.2%)
- 가격 중심 전략 한계

## ⚙️ 분석 내용
- RevPAR 분해 (ADR × 점유율)
- 핵심 변수 도출 (슈퍼호스트, 사진 등)
- 시장 유형 클러스터링
- 수익 시뮬레이션 모델 구축

## 📊 주요 결과
- 점유율 기반 의사결정 구조 전환
- 수익 영향 요인 정량화
- 예측 모델 (R² 0.85)

## 🛠️ 사용 기술
Python, Pandas, LightGBM, SHAP, K-Means, Streamlit
