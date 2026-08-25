"""
기업명 입력 → 3소스 수집 → 개체 연결 → 3축 점수 → 반증 플래그.
CLAUDE.md 5절 MVP 스코프의 핵심 파이프라인. main.py(API)와 CLI 양쪽에서 재사용한다.

CLAUDE.md 8절: KIPRIS 개발단계 계정은 트래픽 한도가 있고, 배포 기간 중 API가
막혀도 데모가 죽지 않아야 한다 — 결과를 data/cache/에 파일로 캐싱한다.
"""
from __future__ import annotations

import json
from pathlib import Path

import requests

from collectors import dart, patent, venture
from core import falsify, matching, normalize, scoring

# 수집기가 던지는 예상 가능한 실패만 흡수한다 (네트워크/키미설정/데이터없음).
# 그 외 예외(코딩 버그 등)는 그대로 전파되어야 조용히 묻히지 않는다.
_COLLECTOR_ERRORS = (
    venture.VentureAPIError,
    dart.DartAPIError,
    patent.PatentAPIError,
    requests.RequestException,
)

CACHE_DIR = Path(__file__).resolve().parent.parent / "data" / "cache"


def evaluate(company_name: str, use_cache: bool = True, refresh: bool = False) -> dict:
    cache_path = CACHE_DIR / f"{normalize.normalize_company_name(company_name)}.json"

    if use_cache and not refresh and cache_path.exists():
        return json.loads(cache_path.read_text(encoding="utf-8"))

    result = _evaluate_live(company_name)

    if use_cache:
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        cache_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")

    return result


def _evaluate_live(company_name: str) -> dict:
    venture_rows = _safe(venture.search_venture, company_name, default=[])
    dart_candidates = _safe(dart.find_corp_code, company_name, default=[])
    patent_summary = _safe(
        patent.get_patent_summary, company_name,
        default={"applicant_key": company_name, "matched_by_person_number": False, "totalCount": 0, "items": []},
    )

    profile = normalize.resolve_entity(company_name, venture_rows, dart_candidates, patent_summary)

    dart_result = None
    if profile.get("dart"):
        dart_result = _safe(
            dart.get_financial_summary, profile["dart"]["corp_code"], bsns_year=str(_latest_bsns_year()),
            default=None,
        )

    return {
        "profile": profile,
        "scores": scoring.score_all(profile),
        "flags": falsify.run_all(profile, dart_result=dart_result),
        "vc_matches": matching.match_vcs(profile),
    }


def _latest_bsns_year() -> int:
    from datetime import date
    # DART 사업보고서는 익년에 공시되므로 전년도가 가장 최근 확정 데이터
    return date.today().year - 1


def _safe(fn, *args, default=None, **kwargs):
    try:
        return fn(*args, **kwargs)
    except _COLLECTOR_ERRORS:
        return default
