"""
risk_detection/config.py
========================
단일 진실 원천 — 모든 임계값·이메일·자치구 매핑을 여기서 관리합니다.
다른 모듈은 이 파일에서 상수를 import해서 사용합니다.
"""

import os
import pathlib
import sys as _sys

_BASE = pathlib.Path(__file__).parent.parent  # 프로젝트 루트
_sys.path.insert(0, str(_BASE))
from shared.constants import DISTRICT_KO  # noqa: E402

# ──────────────────────────────────────────────
# 탐지 규칙 임계값
# ──────────────────────────────────────────────
THRESHOLDS = {
  # R1: Phantom Revenue — 리뷰 없이 고수익
  'R1_revenue_min': 10_000_000,   # 연간 수익 1,000만원 초과

  # R2: Occupancy-Revenue Mismatch — 점유율 0인데 수익 발생
  'R2_revenue_min': 0,            # 수익 > 0

  # R3: Rate Outlier + No Social Proof — 자치구 평균 + 3σ 초과
  'R3_sigma': 3,                  # 표준편차 배수

  # R4: Ghost Active Listing — Active+Operating인데 활동 없음
  'R4_revenue_min': 5_000_000,   # 연간 수익 500만원 초과

  # R5: Revenue Without Rating — 평점 없이 고수익 + 고점유율
  'R5_revenue_min': 10_000_000,  # 연간 수익 1,000만원 초과
  'R5_occupancy_min': 0.3,       # 점유율 30% 초과

  # 복합 HIGH RISK 기준
  'high_risk_rule_count': 2,     # 2개 이상 규칙 동시 충족

  # 통계 이상치 기준
  'iqr_multiplier': 1.5,         # IQR × 1.5
  'zscore_threshold': 3.0,       # |Z-score| > 3
}

# ──────────────────────────────────────────────
# 이메일 설정
# ──────────────────────────────────────────────
# 실제 운영 시 recipients 목록을 담당 부서 이메일로 교체하세요.
EMAIL_CONFIG = {
  'smtp_host': 'smtp.gmail.com',
  'smtp_port': 587,
  'sender': 'jmjung950312@gmail.com',
  'password': os.environ.get('RISK_EMAIL_PASSWORD', ''),  # 환경변수에서 읽음
  'recipients': [
    'jmjung950312@gmail.com',
  ],
  'subject_prefix': '[서울 에어비앤비 리스크 알림]',
}

# ──────────────────────────────────────────────
# 데이터 경로
# ──────────────────────────────────────────────

DATA_PATH = _BASE / 'data' / 'raw' / 'seoul_airbnb_cleaned.csv'
FEATURES_PATH = _BASE / 'data' / 'processed' / 'seoul_airbnb_features.csv'
REPORT_PATH = _BASE / 'reports' / 'risk_alerts.json'

# 중복 감지 방지 — 히스토리 파일 경로
DUPLICATE_HISTORY_PATH = _BASE / 'logs' / 'risk_detection_history.json'

# ──────────────────────────────────────────────
# Google Sheets 연동 설정
# ──────────────────────────────────────────────
SHEETS_CONFIG = {
  'spreadsheet_id': os.environ.get('GOOGLE_SHEETS_ID', ''),
  'credentials_path': os.environ.get('GOOGLE_CREDENTIALS_PATH', ''),
}
