"""
risk_detection/sheets_sync.py
================================
Google Sheets 자동 기록 — 리스크 스캔 결과를 두 탭에 기록합니다.

탭 구성
-------
- Risk Alerts : 최신 스캔의 플래그 리스팅 전체 (매 실행마다 덮어씀)
- Scan Log    : 매 스캔 요약 1행씩 누적 추가

사전 조건
---------
1. gspread + google-auth 설치
   pip install gspread google-auth

2. 환경변수 설정
   export GOOGLE_SHEETS_ID="your-spreadsheet-id"
   export GOOGLE_CREDENTIALS_PATH="/path/to/service_account.json"

3. 서비스 계정 이메일을 Sheets 편집자로 공유
   (service_account.json 내 "client_email" 값을 Sheets 공유 대상에 추가)
"""

from datetime import datetime
from typing import Optional

from risk_detection.config import SHEETS_CONFIG


# ── 연결 헬퍼 ─────────────────────────────────────────────────────────────────

def _get_client():
  """
  Service Account JSON으로 gspread 클라이언트를 초기화.
  gspread 또는 google-auth 미설치 시 ImportError 발생.
  """
  import gspread
  from google.oauth2.service_account import Credentials

  creds_path = SHEETS_CONFIG.get('credentials_path', '')
  if not creds_path:
    raise ValueError('GOOGLE_CREDENTIALS_PATH 환경변수가 설정되지 않았습니다.')

  scopes = [
    'https://spreadsheets.google.com/feeds',
    'https://www.googleapis.com/auth/drive',
  ]
  creds = Credentials.from_service_account_file(creds_path, scopes=scopes)
  return gspread.authorize(creds)


def _is_configured() -> bool:
  """Sheets 연동에 필요한 환경변수가 모두 설정됐는지 확인."""
  return bool(
    SHEETS_CONFIG.get('spreadsheet_id') and
    SHEETS_CONFIG.get('credentials_path')
  )


# ── SheetsExporter ────────────────────────────────────────────────────────────

class SheetsExporter:
  """Google Sheets 연동 클래스"""

  # Risk Alerts 탭 컬럼 순서
  ALERT_COLUMNS = [
    'listing_idx', 'district_ko', 'risk_level', 'rules_triggered',
    'ttm_revenue', 'ttm_occupancy', 'ttm_avg_rate', 'num_reviews',
    'scanned_at',
  ]

  # Scan Log 탭 컬럼 순서
  LOG_COLUMNS = [
    'scanned_at', 'total_listings', 'total_flagged',
    'high_count', 'medium_count',
    'R1_hits', 'R2_hits', 'R3_hits', 'R4_hits', 'R5_hits',
  ]

  def __init__(self):
    self._client = None
    self._spreadsheet = None

  def _connect(self):
    """지연 초기화 — 처음 사용 시 연결."""
    if self._client is None:
      self._client = _get_client()
    if self._spreadsheet is None:
      self._spreadsheet = self._client.open_by_key(
        SHEETS_CONFIG['spreadsheet_id']
      )

  def _get_or_create_worksheet(self, title: str, rows=1000, cols=20):
    """이름으로 워크시트를 가져오거나 없으면 생성."""
    try:
      return self._spreadsheet.worksheet(title)
    except Exception:
      return self._spreadsheet.add_worksheet(title=title, rows=rows, cols=cols)

  # ── 공개 메서드 ──────────────────────────────────────────────────────────

  def sync_risk_alerts(self, risk_df, worksheet: str = 'Risk Alerts') -> bool:
    """
    최신 스캔의 플래그 리스팅 전체를 Risk Alerts 탭에 덮어씁니다.
    (헤더 + 데이터 전체 clear 후 update)

    Parameters
    ----------
    risk_df   : build_risk_report() 반환 DataFrame
    worksheet : 대상 워크시트 이름 (기본 'Risk Alerts')

    Returns
    -------
    bool : 성공 여부
    """
    self._connect()
    ws = self._get_or_create_worksheet(worksheet)
    ws.clear()

    if risk_df.empty:
      ws.update([self.ALERT_COLUMNS], 'A1')
      return True

    now_iso = datetime.now().isoformat(timespec='seconds')
    rows = [self.ALERT_COLUMNS]

    for _, row in risk_df.iterrows():
      rows.append([
        _safe(row.get('listing_idx', '')),
        _safe(row.get('district_ko', row.get('district', ''))),
        _safe(row.get('risk_level', '')),
        _safe(row.get('rules_triggered', '')),
        _safe(row.get('ttm_revenue', '')),
        _safe(row.get('ttm_occupancy', '')),
        _safe(row.get('ttm_avg_rate', '')),
        _safe(row.get('num_reviews', '')),
        now_iso,
      ])

    ws.update(rows, 'A1')
    return True

  def append_scan_log(self, scan_meta: dict, worksheet: str = 'Scan Log') -> bool:
    """
    스캔 요약 메타정보를 Scan Log 탭에 1행 추가합니다.

    Parameters
    ----------
    scan_meta : run_risk_scan()이 반환하는 meta dict
    worksheet : 대상 워크시트 이름 (기본 'Scan Log')

    Returns
    -------
    bool : 성공 여부
    """
    self._connect()
    ws = self._get_or_create_worksheet(worksheet, rows=5000, cols=20)

    # 헤더가 없으면 첫 행에 추가
    existing = ws.get_all_values()
    if not existing:
      ws.append_row(self.LOG_COLUMNS)

    rule_hits = scan_meta.get('rule_hits', {})
    row = [
      datetime.now().isoformat(timespec='seconds'),
      scan_meta.get('total_listings', 0),
      scan_meta.get('total_flagged', 0),
      scan_meta.get('high_risk_count', 0),
      scan_meta.get('medium_risk_count', 0),
      rule_hits.get('R1', 0),
      rule_hits.get('R2', 0),
      rule_hits.get('R3', 0),
      rule_hits.get('R4', 0),
      rule_hits.get('R5', 0),
    ]
    ws.append_row(row)
    return True


# ── 진입점 유틸리티 ───────────────────────────────────────────────────────────

def try_sheets_export(risk_df, scan_meta: dict) -> None:
  """
  설정이 갖춰진 경우에만 Sheets 동기화를 실행하고, 오류는 조용히 로그만 출력.
  hooks.py에서 호출합니다.
  """
  if not _is_configured():
    return

  try:
    exporter = SheetsExporter()
    exporter.sync_risk_alerts(risk_df)
    exporter.append_scan_log(scan_meta)
    print('  → Google Sheets 동기화 완료')
  except ImportError:
    print('  [경고] gspread 미설치 — pip install gspread google-auth')
  except Exception as e:
    print(f'  [경고] Sheets 동기화 실패: {e}')


# ── 내부 유틸 ─────────────────────────────────────────────────────────────────

def _safe(v):
  """Sheets API가 직렬화할 수 없는 타입을 문자열로 변환."""
  import math
  if v is None:
    return ''
  if isinstance(v, float) and math.isnan(v):
    return ''
  if hasattr(v, 'item'):
    return v.item()
  return v
