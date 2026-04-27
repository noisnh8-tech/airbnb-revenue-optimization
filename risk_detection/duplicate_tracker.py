"""
risk_detection/duplicate_tracker.py
=====================================
중복 감지 방지 — 동일 listing_idx + 동일 규칙 조합이 쿨다운 기간 내 재감지되면
알림을 스킵합니다.

예외: 규칙 조합이 변경된 경우(악화/호전) → 재알림 허용

JSON 구조 (logs/risk_detection_history.json):
{
  "5996": {
    "last_detected": "2026-03-01T22:05:36",
    "risk_level": "HIGH",
    "rules_triggered": ["R1", "R3"],
    "alert_count": 2
  }
}
"""

import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

from risk_detection.config import DUPLICATE_HISTORY_PATH


class DuplicateTracker:
  """중복 감지 방지 트래커"""

  def __init__(self, history_path: Optional[Path] = None):
    self.history_path = history_path or DUPLICATE_HISTORY_PATH
    self._history: dict = {}
    self._load()

  # ── 내부: 파일 I/O ────────────────────────────────────────────────────────

  def _load(self):
    """히스토리 파일 로드. 없으면 빈 딕셔너리로 시작."""
    if self.history_path.exists():
      try:
        with open(self.history_path, encoding='utf-8') as f:
          self._history = json.load(f)
      except (json.JSONDecodeError, OSError):
        self._history = {}
    else:
      self._history = {}

  def _save(self):
    """히스토리를 파일에 저장."""
    self.history_path.parent.mkdir(parents=True, exist_ok=True)
    with open(self.history_path, 'w', encoding='utf-8') as f:
      json.dump(self._history, f, ensure_ascii=False, indent=2)

  # ── 공개 API ──────────────────────────────────────────────────────────────

  def is_duplicate(
    self,
    listing_idx: int,
    rules: list[str],
    cooldown_days: int = 7,
  ) -> bool:
    """
    동일 listing + 동일 규칙 조합이 쿨다운 기간 내 이미 기록됐으면 True.

    Parameters
    ----------
    listing_idx : 리스팅 ID
    rules       : 이번 스캔에서 트리거된 규칙 목록 (예: ['R1', 'R3'])
    cooldown_days : 중복 판별 기간 (기본 7일)

    Returns
    -------
    bool : True이면 중복(스킵), False이면 신규(알림 발송)
    """
    key = str(listing_idx)
    if key not in self._history:
      return False

    rec = self._history[key]
    last_dt = datetime.fromisoformat(rec['last_detected'])
    if datetime.now() - last_dt > timedelta(days=cooldown_days):
      return False  # 쿨다운 만료 → 재알림 허용

    # 규칙 조합이 달라졌으면 재알림 허용 (악화/호전 감지)
    prev_rules = sorted(rec.get('rules_triggered', []))
    curr_rules = sorted(rules)
    if prev_rules != curr_rules:
      return False

    return True  # 동일 규칙 + 쿨다운 내 → 중복

  def record(self, listing_idx: int, risk_level: str, rules: list[str]):
    """
    감지 결과를 히스토리에 기록하고 파일에 저장.

    Parameters
    ----------
    listing_idx : 리스팅 ID
    risk_level  : 'HIGH' | 'MEDIUM'
    rules       : 트리거된 규칙 목록
    """
    key = str(listing_idx)
    prev_count = self._history.get(key, {}).get('alert_count', 0)
    self._history[key] = {
      'last_detected': datetime.now().isoformat(timespec='seconds'),
      'risk_level': risk_level,
      'rules_triggered': sorted(rules),
      'alert_count': prev_count + 1,
    }
    self._save()

  def record_batch(self, risk_df):
    """
    risk_df 전체를 일괄 기록 후 파일 저장 1회 (성능 최적화).

    Parameters
    ----------
    risk_df : build_risk_report()가 반환한 DataFrame
              필요 컬럼: listing_idx, risk_level, rules_triggered
    """
    now_iso = datetime.now().isoformat(timespec='seconds')
    for _, row in risk_df.iterrows():
      key = str(int(row['listing_idx']))
      rules = _parse_rules(row.get('rules_triggered', ''))
      prev_count = self._history.get(key, {}).get('alert_count', 0)
      self._history[key] = {
        'last_detected': now_iso,
        'risk_level': str(row.get('risk_level', 'MEDIUM')),
        'rules_triggered': sorted(rules),
        'alert_count': prev_count + 1,
      }
    self._save()

  def filter_new(self, risk_df, cooldown_days: int = 7):
    """
    risk_df에서 중복 행을 제거하고 신규 행만 반환.

    Returns
    -------
    (new_df, skipped_count)
    """
    if risk_df.empty:
      return risk_df, 0

    mask = []
    for _, row in risk_df.iterrows():
      idx = int(row['listing_idx'])
      rules = _parse_rules(row.get('rules_triggered', ''))
      mask.append(not self.is_duplicate(idx, rules, cooldown_days))

    import pandas as pd
    new_df = risk_df[mask].reset_index(drop=True)
    skipped = len(risk_df) - len(new_df)
    return new_df, skipped

  def purge_old(self, days: int = 30):
    """
    days일 이상 된 기록을 히스토리에서 삭제하고 저장.

    Parameters
    ----------
    days : 보존 기간 (기본 30일)
    """
    cutoff = datetime.now() - timedelta(days=days)
    old_keys = [
      k for k, v in self._history.items()
      if datetime.fromisoformat(v['last_detected']) < cutoff
    ]
    for k in old_keys:
      del self._history[k]
    if old_keys:
      self._save()
    return len(old_keys)


# ── 유틸리티 ─────────────────────────────────────────────────────────────────

def _parse_rules(raw) -> list[str]:
  """
  rules_triggered 필드를 문자열 또는 리스트에서 파싱.
  예: "R1,R3" → ['R1', 'R3'] / ['R1', 'R3'] → ['R1', 'R3']
  """
  if isinstance(raw, list):
    return [str(r) for r in raw]
  if isinstance(raw, str):
    return [r.strip() for r in raw.split(',') if r.strip()]
  return []
