"""
3축 결정론적 집계.

CLAUDE.md 1절 원칙: 점수는 LLM 판단이 아니라 공개 데이터 원천값의
결정론적 집계다. LLM은 이 점수를 자연어로 "설명"만 한다 (판정 아님).
모든 결과에는 출처(source)가 딸려 나와야 한다.

축:
  기술력  — 특허 등록/출원 건수, IPC 분류 다양성, 벤처확인 "연구개발유형" 여부
  투자이력 — [2026-08-20 설계결정] 벤처확인유형이 "벤처투자유형"인지 이진 플래그
             (원 기획의 금액·시기 데이터는 이 API에 없음 — collectors/venture.py 상단 주석 참고)
  공신력  — 벤처확인 보유 여부 + 유효기간 임박도
             [알려진 제약] CLAUDE.md는 "벤처/이노비즈/메인비즈 다층 보유"를 상정했으나
             확정된 데이터 소스(4절)엔 벤처기업명단 API만 있고 이노비즈/메인비즈 API는
             없다. 현재는 벤처확인 단일 소스로만 판정한다.
  (보조) 재무 — DART, 없으면 D1 중립 표기 (falsify.py에서 처리)
"""
from __future__ import annotations

from datetime import date, datetime

VENTURE_SOURCE = "data.go.kr 중소벤처기업부_벤처기업명단(15084581)"
PATENT_SOURCE = "KIPRISPlus patUtiModInfoSearchSevice/getAdvancedSearch"

REGISTERED_STATUSES = {"등록"}
ACTIVE_STATUSES = {"등록", "공개"}  # 소멸/무효/거절/취하 제외한 '살아있는' 권리


def _parse_date(s: str | None) -> date | None:
    if not s:
        return None
    for fmt in ("%Y%m%d", "%Y-%m-%d"):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    return None


def score_technology(profile: dict) -> dict:
    """기술력 축. profile은 core.normalize.resolve_entity()의 반환값."""
    patent = profile.get("patent") or {}
    items = patent.get("items", [])
    venture_row = profile.get("venture")

    total_count = patent.get("totalCount", 0)
    registered_count = sum(1 for it in items if it.get("registerStatus") in REGISTERED_STATUSES)
    active_count = sum(1 for it in items if it.get("registerStatus") in ACTIVE_STATUSES)

    ipc_classes = set()
    for it in items:
        for code in (it.get("ipcNumber") or "").split("|"):
            code = code.strip()
            if code:
                ipc_classes.add(code[:4])  # 대분류 수준 (예: G06N)

    is_rnd_type = bool(venture_row) and venture_row.get("벤처확인유형") == "연구개발유형"

    if total_count == 0:
        tier = "데이터없음"
    elif registered_count >= 5 or total_count >= 20:
        tier = "높음"
    elif registered_count >= 1 or total_count >= 5:
        tier = "보통"
    else:
        tier = "낮음"

    return {
        "axis": "기술력",
        "tier": tier,
        "metrics": {
            "total_count": total_count,
            "registered_count": registered_count,
            "active_count": active_count,
            "ipc_class_count": len(ipc_classes),
            "ipc_classes": sorted(ipc_classes),
            "is_rnd_venture_type": is_rnd_type,
        },
        "source": PATENT_SOURCE,
    }


def score_investment(profile: dict) -> dict:
    """투자이력 축 — 벤처투자유형 이진 플래그 (2026-08-20 설계결정, MEMORY 참고)."""
    venture_row = profile.get("venture")

    if not venture_row:
        return {
            "axis": "투자이력",
            "tier": "정보없음",
            "metrics": {"has_venture_investment_type": None},
            "source": VENTURE_SOURCE,
        }

    has_investment_type = venture_row.get("벤처확인유형") == "벤처투자유형"
    return {
        "axis": "투자이력",
        "tier": "있음" if has_investment_type else "없음",
        "metrics": {
            "has_venture_investment_type": has_investment_type,
            "venture_confirm_type": venture_row.get("벤처확인유형"),
        },
        "source": VENTURE_SOURCE,
    }


def score_credibility(profile: dict, as_of: date | None = None) -> dict:
    """공신력 축 — 벤처확인 보유 여부 + 유효기간 임박도.

    [알려진 제약] 이노비즈/메인비즈는 확정 데이터 소스가 없어 미반영 (scoring.py 상단 주석 참고).
    """
    venture_row = profile.get("venture")
    as_of = as_of or date.today()

    if not venture_row:
        return {
            "axis": "공신력",
            "tier": "정보없음",
            "metrics": {"has_certification": False},
            "source": VENTURE_SOURCE,
        }

    valid_until = _parse_date(venture_row.get("벤처유효종료일"))
    days_left = (valid_until - as_of).days if valid_until else None

    if days_left is None:
        tier = "확인불가"
    elif days_left < 0:
        tier = "만료"
    elif days_left <= 90:
        tier = "만료임박"
    else:
        tier = "유효"

    return {
        "axis": "공신력",
        "tier": tier,
        "metrics": {
            "has_certification": True,
            "cert_type": venture_row.get("벤처확인유형"),
            "cert_agency": venture_row.get("벤처확인기관"),
            "valid_from": venture_row.get("벤처유효시작일"),
            "valid_until": venture_row.get("벤처유효종료일"),
            "days_until_expiry": days_left,
        },
        "source": VENTURE_SOURCE,
    }


def score_all(profile: dict) -> dict:
    return {
        "technology": score_technology(profile),
        "investment": score_investment(profile),
        "credibility": score_credibility(profile),
    }
