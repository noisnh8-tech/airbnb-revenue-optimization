"""
risk_detection/detector.py
==========================
Agent 1 — R1~R5 규칙 엔진

각 규칙은 독립적인 boolean 컬럼(flag_R1 ~ flag_R5)으로 추가됩니다.
복수 규칙 충족 시 rule_count와 rules_triggered로 집계됩니다.
"""

import pandas as pd
import numpy as np
from pathlib import Path

from .config import DATA_PATH, THRESHOLDS, DISTRICT_KO


def load_data(csv_path: str | Path | None = None) -> pd.DataFrame:
  """
  CSV 로드 + listing_idx 대리 ID + district_ko 한글 자치구명 추가

  Parameters
  ----------
  csv_path : str | Path | None
      None이면 config의 기본 경로 사용
  """
  path = Path(csv_path) if csv_path else DATA_PATH
  df = pd.read_csv(path)

  # listing_id 없음 → 인덱스를 대리 ID로 사용
  df = df.reset_index().rename(columns={'index': 'listing_idx'})

  # 자치구 한글명 추가
  df['district_ko'] = df['district'].map(DISTRICT_KO).fillna(df['district'])

  return df


def compute_district_rate_stats(df: pd.DataFrame) -> pd.DataFrame:
  """
  R3 규칙용: 자치구별 ADR(ttm_avg_rate) 평균·표준편차 계산 후 원본 df에 merge

  반환: district_adr_mean, district_adr_std 컬럼이 추가된 df
  """
  # ADR > 0인 리스팅만으로 기준통계 산출 (0원은 비활성 매물)
  active_mask = df['ttm_avg_rate'] > 0
  dist_stats = (
    df[active_mask]
    .groupby('district')['ttm_avg_rate']
    .agg(district_adr_mean='mean', district_adr_std='std')
    .reset_index()
  )

  df = df.merge(dist_stats, on='district', how='left')

  # std가 NaN인 경우(자치구 내 1개 리스팅) → 0으로 대체
  df['district_adr_std'] = df['district_adr_std'].fillna(0)

  return df


def apply_rules(df: pd.DataFrame) -> pd.DataFrame:
  """
  R1~R5 규칙 적용 → boolean flag 컬럼 + rule_count + rules_triggered 추가

  규칙 설명
  ---------
  R1  Phantom Revenue       : 리뷰 0건 + 연간수익 > 1,000만원
  R2  Occupancy-Revenue Mismatch : 수익 > 0 AND 점유율 == 0
  R3  Rate Outlier + No Social Proof : ADR > 자치구평균+3σ AND 리뷰 0건
  R4  Ghost Active Listing  : Active+Operating AND 리뷰 0건 AND 수익 > 500만원
  R5  Revenue Without Rating: 수익 > 1,000만원 AND rating_overall 결측 AND 점유율 > 0.3
  """
  t = THRESHOLDS

  # ── R1: Phantom Revenue ──────────────────────
  df['flag_R1'] = (
    (df['num_reviews'] == 0) &
    (df['ttm_revenue'] > t['R1_revenue_min'])
  )

  # ── R2: Occupancy-Revenue Mismatch ───────────
  df['flag_R2'] = (
    (df['ttm_revenue'] > t['R2_revenue_min']) &
    (df['ttm_occupancy'] == 0)
  )

  # ── R3: Rate Outlier + No Social Proof ───────
  # compute_district_rate_stats()가 선행 실행되어야 함
  if 'district_adr_mean' not in df.columns:
    df = compute_district_rate_stats(df)

  sigma = t['R3_sigma']
  adr_threshold = df['district_adr_mean'] + sigma * df['district_adr_std']

  df['flag_R3'] = (
    (df['ttm_avg_rate'] > adr_threshold) &
    (df['num_reviews'] == 0)
  )

  # ── R4: Ghost Active Listing ─────────────────
  is_active_operating = (
    (df['refined_status'] == 'Active') &
    (df['operation_status'] == 'Operating')
  )
  df['flag_R4'] = (
    is_active_operating &
    (df['num_reviews'] == 0) &
    (df['ttm_revenue'] > t['R4_revenue_min'])
  )

  # ── R5: Revenue Without Rating ────────────────
  # rating_overall 결측치가 현재 데이터에서는 0건이지만
  # 데이터 갱신 시나리오 대비용으로 유지
  df['flag_R5'] = (
    (df['ttm_revenue'] > t['R5_revenue_min']) &
    df['rating_overall'].isna() &
    (df['ttm_occupancy'] > t['R5_occupancy_min'])
  )

  # ── 복합 집계 ─────────────────────────────────
  rule_cols = ['flag_R1', 'flag_R2', 'flag_R3', 'flag_R4', 'flag_R5']
  rule_names = ['R1', 'R2', 'R3', 'R4', 'R5']

  df['rule_count'] = df[rule_cols].sum(axis=1)

  # 발동된 규칙명을 쉼표 구분 문자열로 기록 (벡터화)
  rule_flags = df[rule_cols].values.astype(bool)
  rule_name_arr = np.array(rule_names)
  df['rules_triggered'] = [
      ', '.join(rule_name_arr[flags]) for flags in rule_flags
  ]

  return df


def get_flagged(df: pd.DataFrame) -> pd.DataFrame:
  """
  rule_count > 0인 의심 리스팅만 추출

  Returns
  -------
  pd.DataFrame : 플래그된 리스팅, rule_count 내림차순 정렬
  """
  flagged = df[df['rule_count'] > 0].copy()
  flagged = flagged.sort_values('rule_count', ascending=False)
  return flagged


def rule_hit_summary(df: pd.DataFrame) -> dict:
  """
  규칙별 히트 수 요약 딕셔너리 반환 (로깅·출력용)
  """
  return {
    'R1_phantom_revenue': int(df['flag_R1'].sum()),
    'R2_occ_revenue_mismatch': int(df['flag_R2'].sum()),
    'R3_rate_outlier': int(df['flag_R3'].sum()),
    'R4_ghost_active': int(df['flag_R4'].sum()),
    'R5_no_rating_revenue': int(df['flag_R5'].sum()),
    'total_flagged': int((df['rule_count'] > 0).sum()),
    'high_risk': int((df['rule_count'] >= THRESHOLDS['high_risk_rule_count']).sum()),
  }
