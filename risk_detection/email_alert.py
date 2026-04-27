"""
risk_detection/email_alert.py
==============================
Agent 3 — HTML 이메일 빌더 + SMTP TLS 발송

HIGH RISK 리스팅이 1건 이상일 때만 자동 발송합니다.
이메일 비밀번호는 환경변수 RISK_EMAIL_PASSWORD에서 읽습니다.
"""

import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime

import pandas as pd

from .config import EMAIL_CONFIG


# ── 규칙 설명 (이메일 본문에 표시) ─────────────────
RULE_DESCRIPTIONS = {
  'R1': 'Phantom Revenue — 리뷰 0건 + 연간수익 1,000만원 초과 (실제 숙박 없이 매출 발생)',
  'R2': 'Occupancy-Revenue Mismatch — 점유율 0인데 수익 발생',
  'R3': 'Rate Outlier + No Social Proof — 자치구 평균 ADR + 3σ 초과 + 리뷰 0건',
  'R4': 'Ghost Active Listing — Active+Operating 상태인데 리뷰 0건 + 수익 500만원 초과',
  'R5': 'Revenue Without Rating — 수익 1,000만원 초과 + 평점 결측 + 점유율 30% 초과',
}


def _format_won(value) -> str:
  """원화 포맷 (예: ₩1,234,567)"""
  try:
    return f'₩{int(value):,}'
  except (ValueError, TypeError):
    return 'N/A'


def _risk_badge(level: str) -> str:
  """리스크 레벨 배지 HTML"""
  colors = {
    'HIGH':   ('background:#e53935;color:white', 'HIGH'),
    'MEDIUM': ('background:#fb8c00;color:white', 'MEDIUM'),
    'NONE':   ('background:#757575;color:white', 'NONE'),
  }
  style, text = colors.get(level, colors['NONE'])
  return f'<span style="padding:2px 8px;border-radius:4px;font-size:11px;{style}">{text}</span>'


def build_html_email(risk_df: pd.DataFrame, scan_meta: dict) -> str:
  """
  색상 코딩된 HTML 이메일 본문 생성

  Parameters
  ----------
  risk_df   : build_risk_report()가 반환한 플래그된 리스팅 DataFrame
  scan_meta : 스캔 메타정보 딕셔너리

  Returns
  -------
  str : HTML 문자열
  """
  scanned_at = scan_meta.get('scanned_at', datetime.now().isoformat())
  total = scan_meta.get('total_listings', 0)
  high_count = scan_meta.get('high_risk_count', 0)
  medium_count = scan_meta.get('medium_risk_count', 0)
  rule_hits = scan_meta.get('rule_hits', {})

  # ── 헤더 섹션 ──────────────────────────────────────
  header_html = f'''
  <div style="background:#1a237e;color:white;padding:20px 24px;border-radius:8px 8px 0 0">
    <h2 style="margin:0;font-size:18px">서울 에어비앤비 리스크 탐지 알림</h2>
    <p style="margin:6px 0 0;font-size:13px;opacity:0.85">
      스캔 시각: {scanned_at} &nbsp;|&nbsp; 총 분석 건수: {total:,}개
    </p>
  </div>
  '''

  # ── 요약 배지 섹션 ─────────────────────────────────
  badges_html = f'''
  <div style="padding:16px 24px;background:#f5f5f5;border-bottom:1px solid #e0e0e0">
    <span style="background:#e53935;color:white;padding:4px 12px;border-radius:4px;
                 font-weight:bold;margin-right:8px">HIGH {high_count}건</span>
    <span style="background:#fb8c00;color:white;padding:4px 12px;border-radius:4px;
                 font-weight:bold;margin-right:8px">MEDIUM {medium_count}건</span>
    <span style="color:#555;font-size:13px;margin-left:8px">
      전체 플래그: {high_count + medium_count}건
    </span>
  </div>
  '''

  # ── 규칙별 히트 수 ─────────────────────────────────
  rule_rows = ''.join(
    f'<tr><td style="padding:6px 12px;font-weight:bold">{r}</td>'
    f'<td style="padding:6px 12px">{RULE_DESCRIPTIONS.get(r, "")}</td>'
    f'<td style="padding:6px 12px;text-align:center;font-weight:bold">'
    f'{rule_hits.get(r, 0)}건</td></tr>'
    for r in ['R1', 'R2', 'R3', 'R4', 'R5']
  )

  rules_html = f'''
  <div style="padding:16px 24px">
    <h3 style="color:#1a237e;font-size:14px;margin:0 0 10px">탐지 규칙 현황</h3>
    <table style="width:100%;border-collapse:collapse;font-size:12px">
      <thead>
        <tr style="background:#e8eaf6">
          <th style="padding:6px 12px;text-align:left;width:60px">규칙</th>
          <th style="padding:6px 12px;text-align:left">설명</th>
          <th style="padding:6px 12px;text-align:center;width:60px">히트</th>
        </tr>
      </thead>
      <tbody>{rule_rows}</tbody>
    </table>
  </div>
  '''

  # ── 리스팅 상세 테이블 ──────────────────────────────
  display_cols = [
    'listing_idx', 'district_ko', 'risk_level', 'rules_triggered',
    'ttm_revenue', 'ttm_occupancy', 'ttm_avg_rate', 'num_reviews',
    'rating_overall', 'refined_status',
  ]
  available = [c for c in display_cols if c in risk_df.columns]
  table_df = risk_df[available].head(50)  # 최대 50건 표시

  header_cells = ''.join(
    f'<th style="padding:6px 10px;text-align:left;white-space:nowrap">{c}</th>'
    for c in available
  )

  def _row_html(row):
    bg = '#fff3e0' if row.get('risk_level') == 'HIGH' else 'white'
    cells = []
    for col in available:
      val = row[col]
      if col == 'risk_level':
        cell_html = _risk_badge(str(val))
      elif col in ('ttm_revenue', 'ttm_avg_rate'):
        cell_html = _format_won(val)
      elif col == 'ttm_occupancy':
        try:
          cell_html = f'{float(val)*100:.1f}%'
        except (ValueError, TypeError):
          cell_html = 'N/A'
      else:
        cell_html = str(val) if pd.notna(val) else 'N/A'
      cells.append(f'<td style="padding:6px 10px;white-space:nowrap">{cell_html}</td>')
    return f'<tr style="background:{bg}">{"".join(cells)}</tr>'

  data_rows = ''.join(_row_html(row) for _, row in table_df.iterrows())

  listings_html = f'''
  <div style="padding:16px 24px">
    <h3 style="color:#1a237e;font-size:14px;margin:0 0 10px">
      의심 리스팅 상세 (최대 50건 표시)
    </h3>
    <div style="overflow-x:auto">
      <table style="width:100%;border-collapse:collapse;font-size:11px;
                    border:1px solid #e0e0e0">
        <thead>
          <tr style="background:#1a237e;color:white">{header_cells}</tr>
        </thead>
        <tbody>{data_rows}</tbody>
      </table>
    </div>
  </div>
  '''

  # ── 푸터 ───────────────────────────────────────────
  footer_html = '''
  <div style="padding:12px 24px;background:#f5f5f5;border-top:1px solid #e0e0e0;
              font-size:11px;color:#757575;border-radius:0 0 8px 8px">
    이 이메일은 서울 에어비앤비 Risk Management 시스템에 의해 자동 생성되었습니다.
    문의: risk-detection 모듈 관리자
  </div>
  '''

  # ── 전체 조합 ──────────────────────────────────────
  html = f'''<!DOCTYPE html>
<html lang="ko">
<head><meta charset="UTF-8"></head>
<body style="font-family:Arial,sans-serif;margin:0;padding:20px;background:#f0f0f0">
  <div style="max-width:900px;margin:0 auto;background:white;
              border-radius:8px;box-shadow:0 2px 8px rgba(0,0,0,0.1)">
    {header_html}
    {badges_html}
    {rules_html}
    {listings_html}
    {footer_html}
  </div>
</body>
</html>'''

  return html


def send_alert_email(risk_df: pd.DataFrame, scan_meta: dict) -> bool:
  """
  HIGH RISK >= 1건일 때만 SMTP TLS로 이메일 발송

  Parameters
  ----------
  risk_df   : 플래그된 리스팅 DataFrame
  scan_meta : 스캔 메타정보

  Returns
  -------
  bool : 발송 성공 여부
  """
  high_count = scan_meta.get('high_risk_count', 0)

  # HIGH RISK 없으면 발송 스킵
  if high_count < 1:
    print(f'[알림 스킵] HIGH RISK 0건 — 이메일 발송 생략')
    return False

  # 비밀번호 확인
  password = EMAIL_CONFIG.get('password', '')
  if not password:
    print('[경고] RISK_EMAIL_PASSWORD 환경변수가 없습니다. 이메일을 발송하지 않습니다.')
    print('       export RISK_EMAIL_PASSWORD="your-password" 로 설정하세요.')
    return False

  # HTML 본문 생성
  html_body = build_html_email(risk_df, scan_meta)

  # MIME 메시지 구성
  msg = MIMEMultipart('alternative')
  scanned_at = scan_meta.get('scanned_at', '')[:19].replace('T', ' ')
  msg['Subject'] = (
    f"{EMAIL_CONFIG['subject_prefix']} "
    f"HIGH {high_count}건 탐지 — {scanned_at}"
  )
  msg['From'] = EMAIL_CONFIG['sender']
  msg['To'] = ', '.join(EMAIL_CONFIG['recipients'])

  msg.attach(MIMEText(html_body, 'html', 'utf-8'))

  # SMTP 발송
  try:
    with smtplib.SMTP(EMAIL_CONFIG['smtp_host'], EMAIL_CONFIG['smtp_port']) as server:
      server.ehlo()
      server.starttls()
      server.login(EMAIL_CONFIG['sender'], password)
      server.sendmail(
        EMAIL_CONFIG['sender'],
        EMAIL_CONFIG['recipients'],
        msg.as_string()
      )
    print(f'[성공] 이메일 발송 완료 → {EMAIL_CONFIG["recipients"]}')
    return True
  except Exception as e:
    print(f'[오류] 이메일 발송 실패: {e}')
    return False
