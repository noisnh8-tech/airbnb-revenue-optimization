"""
risk_detection/scorer.py
========================
Agent 2 — 통계 이상치 탐지 + 복합 리스크 레벨 분류

IQR 기반 자치구별 수익 이상치 + Z-score 기반 전체 ADR 이상치를 결합하여
HIGH / MEDIUM 리스크 레벨을 부여합니다.
"""

import pandas as pd
import numpy as np
from datetime import datetime

from .config import THRESHOLDS, DATA_PATH
from .detector import load_data, compute_district_rate_stats, apply_rules, get_flagged


def compute_statistical_anomalies(df: pd.DataFrame) -> pd.DataFrame:
  """
  두 가지 통계 이상치 지표를 추가합니다.

  1. iqr_anomaly  : 자치구별 ttm_revenue IQR × 1.5 초과 여부 (bool)
  2. adr_zscore   : 전체 ttm_avg_rate Z-score
  3. adr_zscore_anomaly : |adr_zscore| > 임계값 여부 (bool)
  """
  iqr_mult = THRESHOLDS['iqr_multiplier']
  z_thresh = THRESHOLDS['zscore_threshold']

  # ── 1. 자치구별 수익 IQR 이상치 ─────────────────
  # apply() 대신 transform()으로 벡터화 처리 (FutureWarning 방지)
  q1 = df.groupby('district')['ttm_revenue'].transform('quantile', 0.25)
  q3 = df.groupby('district')['ttm_revenue'].transform('quantile', 0.75)
  iqr = q3 - q1
  upper_fence = q3 + iqr_mult * iqr
  df['iqr_anomaly'] = df['ttm_revenue'] > upper_fence

  # ── 2. 전체 ADR Z-score ──────────────────────────
  adr_mean = df['ttm_avg_rate'].mean()
  adr_std = df['ttm_avg_rate'].std()

  # std가 0인 경우 방어 처리
  if adr_std > 0:
    df['adr_zscore'] = (df['ttm_avg_rate'] - adr_mean) / adr_std
  else:
    df['adr_zscore'] = 0.0

  df['adr_zscore_anomaly'] = df['adr_zscore'].abs() > z_thresh

  return df


def compute_risk_level(df: pd.DataFrame) -> pd.DataFrame:
  """
  각 리스팅에 리스크 레벨을 부여합니다.

  HIGH   : rule_count >= 2 (복합 신호)
  MEDIUM : rule_count == 1 OR 통계 이상치(iqr_anomaly 또는 adr_zscore_anomaly)
  NONE   : 플래그 없음
  """
  high_threshold = THRESHOLDS['high_risk_rule_count']

  conditions = [
    df['rule_count'] >= high_threshold,
    (df['rule_count'] == 1) |
    df.get('iqr_anomaly', pd.Series(False, index=df.index)) |
    df.get('adr_zscore_anomaly', pd.Series(False, index=df.index)),
  ]
  choices = ['HIGH', 'MEDIUM']

  df['risk_level'] = np.select(conditions, choices, default='NONE')

  return df


def build_risk_report(csv_path=None) -> tuple[pd.DataFrame, dict]:
  """
  전체 파이프라인 실행 → (risk_df, scan_meta) 반환

  risk_df   : 플래그된 리스팅만 포함, risk_level 내림차순 + rule_count 내림차순
  scan_meta : 스캔 메타정보 딕셔너리 (시각, 건수 등)

  Parameters
  ----------
  csv_path : str | Path | None
      None이면 config 기본 경로 사용
  """
  # ── 데이터 로드 ──────────────────────────────────
  df = load_data(csv_path)
  total_listings = len(df)

  # ── 자치구 ADR 통계 계산 ─────────────────────────
  df = compute_district_rate_stats(df)

  # ── 규칙 적용 ────────────────────────────────────
  df = apply_rules(df)

  # ── 통계 이상치 추가 ─────────────────────────────
  df = compute_statistical_anomalies(df)

  # ── 리스크 레벨 부여 ─────────────────────────────
  df = compute_risk_level(df)

  # ── 플래그된 리스팅 추출 ─────────────────────────
  risk_df = get_flagged(df)

  # risk_level 정렬: HIGH → MEDIUM
  level_order = {'HIGH': 0, 'MEDIUM': 1, 'NONE': 2}
  risk_df = risk_df.copy()
  risk_df['_sort_key'] = risk_df['risk_level'].map(level_order)
  risk_df = risk_df.sort_values(['_sort_key', 'rule_count'], ascending=[True, False])
  risk_df = risk_df.drop(columns=['_sort_key'])

  # ── 스캔 메타정보 ────────────────────────────────
  scan_meta = {
    'scanned_at': datetime.now().isoformat(),
    'total_listings': total_listings,
    'total_flagged': len(risk_df),
    'high_risk_count': int((risk_df['risk_level'] == 'HIGH').sum()),
    'medium_risk_count': int((risk_df['risk_level'] == 'MEDIUM').sum()),
    'rule_hits': {
      'R1': int(df['flag_R1'].sum()),
      'R2': int(df['flag_R2'].sum()),
      'R3': int(df['flag_R3'].sum()),
      'R4': int(df['flag_R4'].sum()),
      'R5': int(df['flag_R5'].sum()),
    },
  }

  return risk_df, scan_meta
