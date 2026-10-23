# ============================================================
# config.py — 서울 에어비앤비 RevPAR 분석 전역 설정
#
# 모든 노트북 첫 번째 셀에서 다음 두 줄로 전체 설정을 불러옵니다:
#   import sys; sys.path.insert(0, str(__import__('pathlib').Path.cwd().parent))
#   from config import *
#
# 자동 참조 소스:
#   - SOP_ANALYSIS.json   (분석 표준 절차)
#   - agents/*.json       (파이프라인 에이전트 결과)
#   - model_review.json   (승인된 피처 목록)
# ============================================================

import json
import platform
import warnings
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path

warnings.filterwarnings('ignore')

# ══════════════════════════════════════════════════════════════
# 1. 경로 (프로젝트 루트 기준 절대 경로)
# ══════════════════════════════════════════════════════════════
ROOT_DIR      = Path(__file__).resolve().parent
DATA_RAW      = ROOT_DIR / 'data' / 'raw'
DATA_PROC     = ROOT_DIR / 'data' / 'processed'
DATA_EXTERNAL = ROOT_DIR / 'data' / 'external'
REPORTS_DIR   = ROOT_DIR / 'reports'
AGENTS_DIR    = ROOT_DIR / 'agents'
SOP_PATH      = ROOT_DIR / 'SOP_ANALYSIS.json'

REPORTS_DIR.mkdir(exist_ok=True)
DATA_PROC.mkdir(exist_ok=True)

# 노트북별 변수명 차이를 흡수하는 별칭 (backward-compatible)
REPORT_DIR    = REPORTS_DIR          # 03_host_modeling 호환
PROCESSED_DIR = DATA_PROC            # 02, 04, 05 호환

# 데이터 파일 경로
CSV_RAW           = DATA_RAW  / 'seoul_airbnb_cleaned.csv'
CSV_GEO_MASKED    = DATA_RAW  / 'seoul_airbnb_geo_masked.csv'
CSV_FEATURES      = DATA_PROC / 'seoul_airbnb_features.csv'
CSV_DISTRICT_AGG  = DATA_PROC / 'district_aggregated.csv'
CSV_DISTRICT_CLU  = DATA_PROC / 'district_clustered.csv'
X_TRAIN_PATH      = DATA_PROC / 'X_train_host.csv'
X_TEST_PATH       = DATA_PROC / 'X_test_host.csv'
Y_TRAIN_LOG_PATH  = DATA_PROC / 'y_train_host_log.csv'
Y_TRAIN_ORIG_PATH = DATA_PROC / 'y_train_host_orig.csv'
Y_TEST_LOG_PATH   = DATA_PROC / 'y_test_host_log.csv'
Y_TEST_ORIG_PATH  = DATA_PROC / 'y_test_host_orig.csv'

# 노트북별 경로 별칭 (backward-compatible)
CSV_PATH      = CSV_RAW      # 00, 01, 04 호환
FEATURES_PATH = CSV_FEATURES  # 01, 02, 04 호환
DATA_DIR      = DATA_PROC    # 03 호환

# ══════════════════════════════════════════════════════════════
# 2. SOP 자동 로드
# ══════════════════════════════════════════════════════════════
with open(SOP_PATH, encoding='utf-8') as _f:
    SOP = json.load(_f)

# ══════════════════════════════════════════════════════════════
# 3. 재현성 & 도메인 메타
# ══════════════════════════════════════════════════════════════
RANDOM_SEED   = SOP['analysis_methodology']['reproducibility']['random_seed']  # 42
DOMAIN        = SOP['domain']                    # 'hospitality'
DOMAIN_KOREAN = SOP['domain_korean']             # '서울 에어비앤비'

np.random.seed(RANDOM_SEED)

# ══════════════════════════════════════════════════════════════
# 4. KPI 상수 (SOP + 실측값 기준)
# ══════════════════════════════════════════════════════════════
# — TTM RevPAR
KPI_REVPAR_ALL_MEDIAN       = 8_868      # 전체 32,061건 중위값 (₩)
KPI_REVPAR_ACTIVE_MEDIAN    = 47_850     # Active+Operating 14,399건 중위값 (₩)

# — 슈퍼호스트
KPI_SUPERHOST_REVPAR_MEDIAN = 61_205     # 슈퍼호스트 중위 RevPAR (₩)
KPI_NON_SH_REVPAR_MEDIAN    = 31_825     # 일반 호스트 중위 RevPAR (₩)
KPI_SUPERHOST_PREMIUM       = 0.831      # 슈퍼호스트 프리미엄 비율 (+83.1%, 평균 RevPAR 기준 ₩79,087 vs ₩43,201)

# 노트북 기존 변수명 별칭
SUPERHOST_REVPAR_MEDIAN     = KPI_SUPERHOST_REVPAR_MEDIAN
NON_SUPERHOST_REVPAR_MEDIAN = KPI_NON_SH_REVPAR_MEDIAN

# — 시장 구조
KPI_ACTIVE_RATIO   = 0.449   # Active+Operating 비율 (14,399/32,061)
KPI_DORMANT_RATE   = 0.543   # Dormant 비율 (시장 건전성 리스크)
KPI_DORMANT_RATIO  = KPI_DORMANT_RATE  # 04_platform_eda 호환 별칭

# — 모델링
PRIMARY_KPI   = SOP['analysis_methodology']['primary_metric']    # 'ttm_revpar'
SECONDARY_KPI = SOP['analysis_methodology']['secondary_metric']  # 'l90d_revpar'
REVPAR_MAX    = 2_000_000  # 예측값 합리성 검증 상한 (₩)
TARGET        = 'ttm_revpar'   # 원본 스케일 타겟 (02_host_preprocessing 호환)
TARGET_COL    = 'log_target'   # log1p 변환 타겟 컬럼명 (03_host_modeling 호환)

# — 클러스터링
N_CLUSTERS = 4
CLUSTER_NAMES = {
    0: '프리미엄 관광거점',
    1: '성장형 주거상권',
    2: '중가 균형시장',
    3: '가격민감 외곽형',
}
CLUSTER_COLORS = {
    '프리미엄 관광거점': '#1565C0',
    '성장형 주거상권':   '#2E7D32',
    '중가 균형시장':     '#FF8F00',
    '가격민감 외곽형':   '#C62828',
}

# ══════════════════════════════════════════════════════════════
# 5. 컬럼 목록 (SOP + model_review.json 기준)
# ══════════════════════════════════════════════════════════════

# 분석 전체에서 제외 (상수 or 23.9% 결측)
EXCLUDE_COLS = ['exng', 'ttm_exng', 'nearest_poi_image']

# 데이터 누수 피처 (모델링 시 반드시 제외)
LEAKAGE_COLS = [
    'revpar_vs_district_median',   # CRITICAL: ttm_revpar 직접 파생
    'revpar_trend',                # HIGH: ttm_revpar 구성요소
    'price_efficiency',            # MEDIUM: avg_rate/occupancy
    'ttm_occupancy', 'ttm_avg_rate', 'ttm_revenue',
    'l90d_revpar', 'l90d_occupancy', 'l90d_avg_rate', 'l90d_revenue',
    'revpar_percentile', 'log_ttm_revpar',
    'exng', 'ttm_exng',
]

# 호스트 관점 승인 피처 (원본 컬럼명 — model_review.json APPROVED)
HOST_FEATURES = [
    'room_type', 'superhost', 'instant_book',
    'bedrooms_group', 'baths_group', 'guests_group',
    'min_nights', 'extra_guest_fee_policy',
    'rating_overall', 'photos_count', 'num_reviews',
    'nearest_poi_dist_km', 'nearest_poi_type_name',
    'photos_tier', 'review_rate', 'poi_dist_category',
]

# 전처리 후 모델 입력 피처 (district 컨텍스트 포함, 21개)
APPROVED_FEATURES = HOST_FEATURES + [
    'district_listing_count',
    'district_superhost_rate',
    'district_operating_rate',
    'district_entire_home_rate',
    'ttm_pop',
]

# 플랫폼 관점 피처
PLATFORM_FEATURES = [
    'district', 'district_listing_count', 'district_superhost_rate',
    'district_operating_rate', 'district_entire_home_rate', 'ttm_pop',
]

# SOP 관점 피처 참조
HOST_FOCUS     = SOP['analysis_methodology']['host_perspective_focus']
PLATFORM_FOCUS = SOP['analysis_methodology']['platform_perspective_focus']

# 순서형 인코딩 맵 (02_host_preprocessing)
ORDINAL_MAPS = {
    'bedrooms_group':    ['스튜디오', '1B', '2B', '3B', '4B+'],
    'baths_group':       ['0.5', '1', '1.5', '2', '2.5', '3+'],
    'guests_group':      ['1', '2', '3-4', '5-6', '7+'],
    'photos_tier':       ['하', '중하', '중상', '상'],
    'poi_dist_category': ['초근접', '근접', '보통', '원거리'],
}
BINARY_COLS = ['superhost', 'instant_book', 'extra_guest_fee_policy']
ONEHOT_COLS = ['room_type', 'nearest_poi_type_name']

# ══════════════════════════════════════════════════════════════
# 6. 시각화 표준 (SOP 자동 적용)
# ══════════════════════════════════════════════════════════════
_VIZ = SOP['visualization_standards']

# 플랫폼별 폰트 자동 감지
def _get_font():
    if platform.system() == 'Darwin':
        return 'AppleGothic'
    elif platform.system() == 'Windows':
        return 'Malgun Gothic'   # 맑은 고딕
    else:
        return 'NanumGothic'     # Linux (나눔고딕)

_FONT = _VIZ.get('font_family', _get_font())

plt.rcParams['font.family']        = _FONT
plt.rcParams['axes.unicode_minus'] = False  # 음수 기호 깨짐 방지 (필수)
plt.rcParams['figure.dpi']         = _VIZ['save_dpi']
sns.set_style('whitegrid')

PALETTE     = _VIZ['color_palette']        # 'Set2'
FIGSIZE_MAX = tuple(_VIZ['max_figsize'])   # (14, 8)
SAVE_DPI    = _VIZ['save_dpi']            # 100

# ══════════════════════════════════════════════════════════════
# 7. 이름 규칙 (SOP 기준)
# ══════════════════════════════════════════════════════════════
FEAT_PREFIX = SOP['naming_conventions']['feature_prefix']   # 'feat_'
KPI_PREFIX  = SOP['naming_conventions']['kpi_prefix']       # 'kpi_'
DIST_PREFIX = SOP['naming_conventions']['district_prefix']  # 'dist_'

# ══════════════════════════════════════════════════════════════
# 8. agents/ JSON 헬퍼
# ══════════════════════════════════════════════════════════════
def load_agent(name: str) -> dict:
    """
    agents/{name}.json 로드.

    사용 예:
        hyp  = load_agent('hypotheses')
        feat = load_agent('feature_engineering')
        rev  = load_agent('model_review')
    """
    path = AGENTS_DIR / f'{name}.json'
    if not path.exists():
        raise FileNotFoundError(f'agents/{name}.json 파일 없음')
    with open(path, encoding='utf-8') as f:
        return json.load(f)

# ══════════════════════════════════════════════════════════════
# 9. 데이터 로드 헬퍼
# ══════════════════════════════════════════════════════════════
def load_raw(active_only: bool = False) -> pd.DataFrame:
    """
    원본 데이터 로드.
    active_only=True → refined_status=='Active' & operation_status=='Operating' 서브셋
    """
    df = pd.read_csv(CSV_RAW)
    if active_only:
        mask = (df['refined_status'] == 'Active') & (df['operation_status'] == 'Operating')
        return df[mask].copy()
    return df


def load_features(active_only: bool = False) -> pd.DataFrame:
    """피처 엔지니어링 완료 데이터(seoul_airbnb_features.csv) 로드."""
    df = pd.read_csv(CSV_FEATURES)
    if active_only:
        mask = (df['refined_status'] == 'Active') & (df['operation_status'] == 'Operating')
        return df[mask].copy()
    return df


def load_train_test() -> tuple:
    """
    호스트 모델링용 train/test 데이터 일괄 로드.

    반환: (X_train, X_test, y_train, y_test, y_train_orig, y_test_orig)
    """
    X_train = pd.read_csv(X_TRAIN_PATH, index_col='Unnamed: 0')
    X_test  = pd.read_csv(X_TEST_PATH,  index_col='Unnamed: 0')
    y_train = pd.read_csv(Y_TRAIN_LOG_PATH,  index_col='Unnamed: 0')[TARGET_COL]
    y_test  = pd.read_csv(Y_TEST_LOG_PATH,   index_col='Unnamed: 0')[TARGET_COL]
    y_train_orig = pd.read_csv(Y_TRAIN_ORIG_PATH, index_col='Unnamed: 0').squeeze()
    y_test_orig  = pd.read_csv(Y_TEST_ORIG_PATH,  index_col='Unnamed: 0').squeeze()
    # bool → int (LightGBM 호환)
    for _df in (X_train, X_test):
        _bool_cols = _df.select_dtypes('bool').columns
        _df[_bool_cols] = _df[_bool_cols].astype(int)
    return X_train, X_test, y_train, y_test, y_train_orig, y_test_orig


def load_district_agg() -> pd.DataFrame:
    """자치구 집계 데이터 로드 (04_platform_eda 출력물)."""
    return pd.read_csv(CSV_DISTRICT_AGG)


def load_district_clustered() -> pd.DataFrame:
    """자치구 클러스터 결과 로드 (05_platform_clustering 출력물)."""
    return pd.read_csv(CSV_DISTRICT_CLU)

# ══════════════════════════════════════════════════════════════
# 10. SOP 파생 변수 공식
# ══════════════════════════════════════════════════════════════
def add_kpi_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    SOP 필수 파생 변수 일괄 추가 (feature_engineering.json 기준).

    추가 컬럼:
        revpar_trend        — 최근 90일 RevPAR 성장 추세
        log_ttm_revpar      — log1p 정규화 RevPAR
        is_active_operating — 실제 운영 여부 플래그
    """
    df = df.copy()
    df['revpar_trend']        = (
        (df['l90d_revpar'] - df['ttm_revpar'] / 4)
        / (df['ttm_revpar'] / 4 + 1e-6)
    )
    df['log_ttm_revpar']      = np.log1p(df['ttm_revpar'])
    df['is_active_operating'] = (
        (df['refined_status'] == 'Active') & (df['operation_status'] == 'Operating')
    )
    return df

# ══════════════════════════════════════════════════════════════
# 11. 시각화 헬퍼
# ══════════════════════════════════════════════════════════════
def savefig(fig_id: str, suffix: str = '') -> Path:
    """
    현재 figure를 reports/fig_{fig_id}_{suffix}.png 로 저장.

    사용 예:
        savefig('01', 'superhost_revpar')   → reports/fig_01_superhost_revpar.png
        savefig('03_shap_bar')              → reports/fig_03_shap_bar.png
    """
    name = f'fig_{fig_id}_{suffix}.png' if suffix else f'fig_{fig_id}.png'
    path = REPORTS_DIR / name
    plt.savefig(path, dpi=SAVE_DPI, bbox_inches='tight')
    print(f'저장: reports/{name}')
    return path


def ko_fmt(x, _=None):
    """matplotlib axis formatter — 원화 단위 한국식 표기."""
    if x >= 1_000_000:
        return f'₩{x/1_000_000:.1f}M'
    elif x >= 1_000:
        return f'₩{x/1_000:.0f}K'
    return f'₩{x:.0f}'


def small_sample_warn(df_group: pd.DataFrame, col: str, n_min: int = 10):
    """
    소표본 자치구/그룹 경고 출력 (model_review 권고 반영).

    사용 예:
        small_sample_warn(district_agg, 'total_listings', n_min=10)
    """
    small = df_group[df_group[col] < n_min]
    if not small.empty:
        print(f'⚠️  소표본 경고 (n<{n_min}): {small.index.tolist()} → 해석 주의')

# ══════════════════════════════════════════════════════════════
# 12. 가설 참조 헬퍼
# ══════════════════════════════════════════════════════════════
def get_hypothesis(hid: str) -> dict:
    """
    hypotheses.json에서 특정 가설 반환.

    사용 예:
        h1 = get_hypothesis('H1')
        print(h1['title'])
    """
    hyp_data = load_agent('hypotheses')
    for h in hyp_data['hypotheses']:
        if h['id'] == hid:
            return h
    raise KeyError(f'가설 {hid} 없음')

# ══════════════════════════════════════════════════════════════
# 로드 완료 메시지
# ══════════════════════════════════════════════════════════════
_agent_cnt = len(list(AGENTS_DIR.glob('*.json')))
print(
    f'✅ config 로드 완료 | '
    f'RANDOM_SEED={RANDOM_SEED} | '
    f'SOP v{SOP["version"]} | '
    f'agents {_agent_cnt}개 | '
    f'font={_FONT}'
)
