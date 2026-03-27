# airbnb-revenue-optimization
Airbnb revenue optimization analysis using RevPAR decomposition and simulation
## 📌 프로젝트 목적
서울 Airbnb 데이터를 기반으로 RevPAR(객실당 수익)에 영향을 미치는 핵심 요인을 분석하고,
호스트 의사결정을 위한 데이터 기반 도구 설계

## 🔍 문제 정의
- 비활성 숙소 54.3% → 시장 왜곡
- 점유율이 수익의 핵심 변수 (58.2%)
- 가격 중심 전략 한계

## ⚙️ 분석 및 전략 도출
- RevPAR(ADR × 점유율) 분해를 통한 수익 구조 재정의
- 점유율 중심 호스트가 바로 바꿀 수 있는 핵심 변수 5개도출 및 수익 영향 정량화
- 수익 개선을 위한 핵심 액션 도출 및 적용 기준 정립
- 시장 유형 클러스터링을 통한 자치구별 전략 차별화
- 가격 변화에 따른 RevPAR·순이익 시뮬레이션 기반 의사결정 지원

## 📊 주요 결과
- 점유율이 RevPAR의 58.2% 영향 → 가격 중심 전략 한계 규명 및 의사결정 구조 전환
- 수익 직결 5가지 핵심 액션 도출 (슈퍼호스트 +83.1%, 최대 +148%)
- 예측 모델 기반 End-to-End 의사결정 도구 구축 (R² 0.85)
- Freemium 구조 설계를 통한 호스트–플랫폼 수익 선순환 구조 제시

## 🛠️ 사용 기술
Python, Pandas, LightGBM, SHAP, K-Means, Streamlit,Claude AI Agent 
