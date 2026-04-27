"""
risk_detection/hooks.py
========================
PostToolUse 훅 진입점 + 전체 파이프라인 통합

Claude Code가 파일을 수정할 때마다 자동 호출됩니다.
관련 데이터 파일(seoul_airbnb_cleaned.csv, features.csv)이 변경된
경우에만 리스크 스캔을 실행합니다.

사용법
------
  # 훅 자동 트리거 (Claude Code가 내부적으로 호출)
  python3 hooks.py --trigger postToolUse --file path/to/file.csv

  # 수동 트리거
  python3 hooks.py --trigger manual
"""

import argparse
import json
import sys
from pathlib import Path
from datetime import datetime

# 패키지 루트를 sys.path에 추가 (훅에서 직접 실행 시 필요)
_PKG_ROOT = Path(__file__).parent.parent
if str(_PKG_ROOT) not in sys.path:
  sys.path.insert(0, str(_PKG_ROOT))

from risk_detection.scorer import build_risk_report
from risk_detection.email_alert import send_alert_email, build_html_email
from risk_detection.config import REPORT_PATH, DATA_PATH
from risk_detection.duplicate_tracker import DuplicateTracker
from risk_detection.sheets_sync import try_sheets_export


# ── 트리거 조건 ──────────────────────────────────────
_TRIGGER_KEYWORDS = [
  'seoul_airbnb_cleaned.csv',
  'seoul_airbnb_features.csv',
]


def should_trigger(file_path: str) -> bool:
  """
  변경된 파일이 리스크 스캔 대상인지 판별

  Parameters
  ----------
  file_path : str
      Write/Edit 훅에서 전달된 파일 경로

  Returns
  -------
  bool
  """
  if not file_path:
    return False
  for keyword in _TRIGGER_KEYWORDS:
    if keyword in file_path:
      return True
  return False


def run_risk_scan(csv_path=None) -> dict:
  """
  전체 리스크 파이프라인 실행

  1. 데이터 로드 + 규칙 적용 + 통계 이상치 + 리스크 레벨 부여
  2. reports/risk_alerts.json 저장
  3. HIGH >= 1건이면 이메일 발송

  Parameters
  ----------
  csv_path : str | Path | None
      None이면 config 기본 경로 사용

  Returns
  -------
  dict : scan_meta
  """
  print(f'[{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}] 리스크 스캔 시작...')

  # ── 파이프라인 실행 ──────────────────────────────
  try:
    risk_df, scan_meta = build_risk_report(csv_path)
  except Exception as e:
    print(f'[오류] 파이프라인 실행 실패: {e}')
    return {}

  # ── 결과 요약 출력 ───────────────────────────────
  print(f'  → 총 분석: {scan_meta["total_listings"]:,}건')
  print(f'  → 플래그: {scan_meta["total_flagged"]}건 '
        f'(HIGH {scan_meta["high_risk_count"]}건, '
        f'MEDIUM {scan_meta["medium_risk_count"]}건)')

  rule_hits = scan_meta.get('rule_hits', {})
  for rule, cnt in rule_hits.items():
    if cnt > 0:
      print(f'  → {rule}: {cnt}건')

  # ── 중복 필터: 7일 이내 동일 규칙 조합 스킵 ────────
  tracker = DuplicateTracker()
  tracker.purge_old(days=30)  # 30일 이상 된 기록 자동 삭제

  new_risk_df, skipped = tracker.filter_new(risk_df, cooldown_days=7)
  if skipped > 0:
    print(f'  → 중복 스킵: {skipped}건 (7일 내 동일 규칙 조합)')
  if not new_risk_df.empty:
    tracker.record_batch(new_risk_df)

  # ── JSON 저장 ────────────────────────────────────
  REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)

  # DataFrame을 JSON 직렬화 가능하도록 변환
  if not risk_df.empty:
    # bool 컬럼 → Python bool로 변환
    risk_records = risk_df.to_dict(orient='records')
    # numpy 타입 처리
    risk_records = _convert_types(risk_records)
  else:
    risk_records = []

  report = {
    'scan_meta': scan_meta,
    'flagged_listings': risk_records,
  }

  with open(REPORT_PATH, 'w', encoding='utf-8') as f:
    json.dump(report, f, ensure_ascii=False, indent=2)

  print(f'  → 저장: {REPORT_PATH}')

  # ── 이메일 발송 (신규 건만) ───────────────────────
  send_alert_email(new_risk_df, scan_meta)

  # ── Google Sheets 동기화 ──────────────────────────
  try_sheets_export(risk_df, scan_meta)

  return scan_meta


def _convert_types(records: list) -> list:
  """
  JSON 직렬화를 위해 numpy/pandas 타입을 Python 기본 타입으로 변환
  """
  import numpy as np
  import math

  def _convert_value(v):
    if isinstance(v, bool):
      return v
    if isinstance(v, (int, float)) and math.isnan(v):
      return None
    if hasattr(v, 'item'):  # numpy scalar
      return v.item()
    return v

  return [
    {k: _convert_value(val) for k, val in record.items()}
    for record in records
  ]


def _parse_args():
  parser = argparse.ArgumentParser(
    description='서울 에어비앤비 리스크 탐지 훅'
  )
  parser.add_argument(
    '--trigger',
    default='manual',
    help='트리거 유형 (postToolUse | manual)'
  )
  parser.add_argument(
    '--file',
    default='',
    help='변경된 파일 경로 (postToolUse 시 전달됨)'
  )
  return parser.parse_args()


if __name__ == '__main__':
  args = _parse_args()

  if args.trigger == 'postToolUse':
    # 훅에서 자동 호출 — 관련 파일인 경우에만 스캔
    if should_trigger(args.file):
      print(f'[훅] 관련 파일 변경 감지: {args.file}')
      run_risk_scan()
    else:
      # 무관한 파일 — 조용히 종료
      sys.exit(0)
  else:
    # 수동 트리거 — 항상 스캔 실행
    print('[수동 트리거] 리스크 스캔 실행 중...')
    run_risk_scan()
