#!/bin/zsh
# ============================================================
# setup_cron.sh
# 서울 에어비앤비 리스크 탐지 자동화 설정 스크립트
# 새 Mac에서 한 번만 실행하면 됩니다.
# ============================================================

set -e

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
PYTHON=$(which python3)

echo "======================================"
echo " 서울 에어비앤비 리스크 탐지 셋업"
echo "======================================"
echo "프로젝트 경로: $PROJECT_DIR"
echo "Python 경로:   $PYTHON"
echo ""

# ── 1. 패키지 설치 ─────────────────────────────────────────
echo "[1/3] 필요 패키지 설치 중..."
$PYTHON -m pip install --quiet pandas numpy scikit-learn lightgbm
echo "  → 완료"

# ── 2. 환경변수 등록 ───────────────────────────────────────
echo ""
echo "[2/3] Gmail 앱 비밀번호 설정"
echo "  Google 계정 → 보안 → 앱 비밀번호에서 발급한 16자리를 입력하세요."
echo -n "  앱 비밀번호 입력: "
read -s APP_PASSWORD
echo ""

ZSHRC="$HOME/.zshrc"
if grep -q 'RISK_EMAIL_PASSWORD' "$ZSHRC" 2>/dev/null; then
  # 기존 항목 교체
  sed -i '' "s|export RISK_EMAIL_PASSWORD=.*|export RISK_EMAIL_PASSWORD=\"$APP_PASSWORD\"|" "$ZSHRC"
  echo "  → ~/.zshrc 기존 항목 업데이트"
else
  echo "export RISK_EMAIL_PASSWORD=\"$APP_PASSWORD\"" >> "$ZSHRC"
  echo "  → ~/.zshrc에 새로 추가"
fi

export RISK_EMAIL_PASSWORD="$APP_PASSWORD"

# ── 3. crontab 등록 ────────────────────────────────────────
echo ""
echo "[3/3] crontab 등록 (매주 월요일 오전 8시)..."

LOG_DIR="$PROJECT_DIR/logs"
mkdir -p "$LOG_DIR"

CRON_CMD="0 8 * * 1 RISK_EMAIL_PASSWORD=\"$APP_PASSWORD\" $PYTHON $PROJECT_DIR/risk_detection/hooks.py --trigger manual >> $LOG_DIR/cron_risk_scan.log 2>&1"

# 중복 방지: 기존 항목 제거 후 추가
( crontab -l 2>/dev/null | grep -v 'hooks.py'; echo "$CRON_CMD" ) | crontab -
echo "  → 등록 완료"

# ── 완료 ──────────────────────────────────────────────────
echo ""
echo "======================================"
echo " 설정 완료!"
echo "======================================"
echo ""
echo "  테스트 실행:"
echo "  python3 $PROJECT_DIR/risk_detection/hooks.py --trigger manual"
echo ""
echo "  로그 확인:"
echo "  tail -f $LOG_DIR/cron_risk_scan.log"
echo ""
echo "  새 터미널을 열거나 'source ~/.zshrc' 를 실행해야"
echo "  환경변수가 현재 세션에 적용됩니다."
