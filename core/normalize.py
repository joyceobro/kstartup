"""
개체 연결(entity resolution).

세 수집기가 같은 기업을 각기 다른 키로 반환한다:
  - venture: 업체명(원문) + 주소(시/도+구/군 수준, 상세주소 아님)
  - dart   : corp_code(8자리). company.json으로 사업자/법인번호 추가 확보 가능하나
             DART 등록 기업(주로 시리즈A+)에만 해당 — 초기 스타트업 대다수는 없음.
  - patent : 특허고객번호(CommonSearchApplicantInfo, 2026-08-20 기준 미승인) 대신
             기업명을 applicant로 직접 조회 (동명이인 보정 없음).

[설계 결정 2026-08-20] 사업자/법인번호 기준 매칭은 DART 등록 기업에만 가능해
전체 매칭 전략으로 쓸 수 없다고 판단, 기업명 정규화 + 근사매칭을 기본 전략으로 채택.
DART 매칭이 있는 경우에 한해 사업자/법인번호를 부가 식별자로 노출한다 (교차검증용,
필수 매칭 조건 아님).
"""
from __future__ import annotations

import re

from collectors import dart

_CORP_DESIGNATORS = [
    "주식회사", "(주)", "㈜", "유한회사", "유한책임회사", "합자회사", "합명회사",
]


def normalize_company_name(name: str) -> str:
    """법인격 표기와 공백을 제거해 비교 가능한 형태로 만든다."""
    result = name.strip()
    for designator in _CORP_DESIGNATORS:
        result = result.replace(designator, "")
    return re.sub(r"\s+", "", result)


def _pick_exact_match(company_name: str, candidates: list[dict], name_field: str) -> dict | None:
    target = normalize_company_name(company_name)
    for row in candidates:
        if normalize_company_name(row.get(name_field, "")) == target:
            return row
    return None


def resolve_entity(
    company_name: str,
    venture_rows: list[dict],
    dart_candidates: list[dict],
    patent_summary: dict,
) -> dict:
    """세 소스의 원시 결과를 하나의 기업 프로필로 병합한다.

    각 수집기는 이미 서버 측 부분일치(LIKE) 또는 부분일치(in) 필터를 거친 후보
    리스트를 넘겨준다 — 여기서는 정규화된 기업명 완전일치로 최종 1건을 고른다.
    """
    venture_row = _pick_exact_match(company_name, venture_rows, "업체명")
    dart_row = _pick_exact_match(company_name, dart_candidates, "corp_name")

    identifiers = None
    dart_profile = None
    if dart_row:
        dart_profile = {"corp_code": dart_row["corp_code"], "corp_name": dart_row["corp_name"]}
        try:
            overview = dart.get_company_overview(dart_row["corp_code"])
            identifiers = {"bizr_no": overview.get("bizr_no"), "jurir_no": overview.get("jurir_no")}
            dart_profile["overview"] = overview
        except dart.DartAPIError:
            pass  # 식별자 확보 실패는 매칭 자체를 무효화하지 않는다 (부가 정보일 뿐)

    if venture_row and dart_row:
        match_confidence = "verified"  # 두 소스 모두 정규화 기업명 완전일치
    elif venture_row or dart_row:
        match_confidence = "name_only"
    else:
        match_confidence = "unmatched"

    return {
        "input_name": company_name,
        "normalized_name": normalize_company_name(company_name),
        "venture": venture_row,
        "dart": dart_profile,
        "patent": patent_summary,
        "identifiers": identifiers,
        "match_confidence": match_confidence,
    }
