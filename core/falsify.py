"""
반증 엔진 v1 — 6규칙 (CLAUDE.md 3절).

red flag는 감점이 아니라 "확인 필요" 플래그다. 최종 판단은 심사역·심사위원회(사람)에게 남긴다.
모든 함수는 profile(core.normalize.resolve_entity 반환값)을 받아
플래그가 없으면 None, 있으면 {"rule", "level", "message", "question", ...근거} 를 반환한다.

CLAUDE.md 0.1/3절: 각 플래그는 "심층심사에서 물어볼 질문"(question) 형태로도 함께 출력한다.
심사역이 심층심사 질의서에 그대로 붙여 쓸 수 있는 문장이어야 한다.

[2026-08-20 W2 확정 임계값 — 실제 데이터 부족으로 인한 근사치, 추후 조정 가능]
  A1 장기 정체 기준     : 최근 출원일로부터 24개월 (R&D유형 벤처인증 유효기간 3년의 절반)
  A2 개인출원 의심 비율  : 전체 특허 중 회사명과 다른 출원인명 비율 50% 이상
  C1 투자 후 정체 기준   : 벤처유효시작일(투자 근사 시점) 이후 12개월 & 신규 출원 0건
  C2 인증 만료임박 기준  : 유효종료일까지 90일 이내 (또는 이미 만료)
"""
from __future__ import annotations

from datetime import date, datetime

from core.normalize import normalize_company_name

RULE_IDS = ["A1", "A2", "C1", "C2", "D1", "D2"]

A1_STALL_MONTHS = 24
A2_INDIVIDUAL_RATIO = 0.5
C1_STALL_MONTHS = 12
C2_EXPIRY_WARNING_DAYS = 90


def _parse_date(s: str | None) -> date | None:
    if not s:
        return None
    for fmt in ("%Y%m%d", "%Y-%m-%d"):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    return None


def _months_between(a: date, b: date) -> int:
    return (b.year - a.year) * 12 + (b.month - a.month)


def _latest_application_date(items: list[dict]) -> date | None:
    dates = [_parse_date(it.get("applicationDate")) for it in items]
    dates = [d for d in dates if d]
    return max(dates) if dates else None


def check_a1_deeptech_no_patent(profile: dict, as_of: date | None = None) -> dict | None:
    """R&D/딥테크 표방(벤처확인유형=연구개발유형) + 특허 0건 또는 장기 정체."""
    venture_row = profile.get("venture")
    if not venture_row or venture_row.get("벤처확인유형") != "연구개발유형":
        return None

    as_of = as_of or date.today()
    patent = profile.get("patent") or {}
    total_count = patent.get("totalCount", 0)

    if total_count == 0:
        return {
            "rule": "A1",
            "level": "확인필요",
            "message": "연구개발유형으로 벤처 인증을 받았으나 특허·실용신안 출원 이력이 없습니다.",
            "question": (
                "연구개발유형 벤처확인의 근거가 된 R&D 성과물(정부 R&D 과제 실적, 논문, "
                "시제품, 공인시험성적서 등)은 무엇이며, 특허·실용신안 출원 계획과 일정은 어떻게 됩니까?"
            ),
        }

    latest = _latest_application_date(patent.get("items", []))
    if latest and _months_between(latest, as_of) >= A1_STALL_MONTHS:
        return {
            "rule": "A1",
            "level": "확인필요",
            "message": (
                f"연구개발유형 벤처 인증 보유, 최근 특허 출원일({latest.isoformat()})로부터 "
                f"{A1_STALL_MONTHS}개월 이상 경과 — 기술개발 활동 정체 가능성."
            ),
            "question": (
                f"최근 특허 출원({latest.isoformat()}) 이후 {A1_STALL_MONTHS}개월 넘게 신규 출원이 "
                "없는 이유는 무엇입니까? 현재 진행 중인 R&D 과제와 향후 12개월 산출물 계획을 제시해 주십시오."
            ),
        }
    return None


def check_a2_individual_applicant(profile: dict) -> dict | None:
    """특허 출원인이 법인이 아니라 대표 개인 명의로 다수 출원된 경우."""
    items = (profile.get("patent") or {}).get("items", [])
    if not items:
        return None

    company_norm = normalize_company_name(profile.get("input_name", ""))
    mismatched = [
        it for it in items
        if normalize_company_name(it.get("applicantName", "")) != company_norm
    ]
    ratio = len(mismatched) / len(items)

    if ratio >= A2_INDIVIDUAL_RATIO:
        sample_names = sorted({it.get("applicantName", "") for it in mismatched})[:3]
        return {
            "rule": "A2",
            "level": "확인필요",
            "message": (
                f"전체 특허 {len(items)}건 중 {len(mismatched)}건({ratio:.0%})이 법인명이 아닌 "
                f"다른 출원인 명의입니다 (예: {', '.join(sample_names)}). 개인 명의 출원 여부 확인 필요."
            ),
            "question": (
                f"특허 {len(items)}건 중 {len(mismatched)}건이 법인이 아닌 개인({', '.join(sample_names)}) "
                "명의로 출원되어 있습니다. 해당 특허가 법인 소유입니까? 개인→법인 간 양도·전용실시권 "
                "계약서 등 법인 귀속을 입증할 자료를 제출해 주십시오."
            ),
        }
    return None


def check_c1_investment_activity_stall(profile: dict, as_of: date | None = None) -> dict | None:
    """투자유치(벤처투자유형) 확인 이후 특허 활동이 정체된 경우.

    ⚠️ 근사치: 실제 투자 시점 데이터가 없어 벤처유효시작일을 근사 기준으로 쓴다
    (collectors/venture.py 상단 주석, MEMORY investment_axis_gap 참고).
    """
    venture_row = profile.get("venture")
    if not venture_row or venture_row.get("벤처확인유형") != "벤처투자유형":
        return None

    start = _parse_date(venture_row.get("벤처유효시작일"))
    if not start:
        return None
    as_of = as_of or date.today()
    if _months_between(start, as_of) < C1_STALL_MONTHS:
        return None  # 아직 판단하기엔 이르다

    items = (profile.get("patent") or {}).get("items", [])
    activity_after = [it for it in items if (_parse_date(it.get("applicationDate")) or date.min) >= start]

    if not activity_after:
        return {
            "rule": "C1",
            "level": "확인필요",
            "message": (
                f"벤처투자유형 인증({start.isoformat()} 시작) 이후 {C1_STALL_MONTHS}개월 이상 "
                f"경과했으나 그 기간 신규 특허 출원이 없습니다."
            ),
            "question": (
                f"벤처투자유형 인증({start.isoformat()}) 이후 신규 특허 출원이 확인되지 않습니다. "
                "같은 기간의 투자금 집행 내역과 R&D·사업화 성과(매출, 고객 확보, 제품 출시 등)를 "
                "무엇으로 확인할 수 있습니까?"
            ),
        }
    return None


def check_c2_certification_expiring(profile: dict, as_of: date | None = None) -> dict | None:
    """벤처 인증 만료·임박 여부 (기준: 90일 이내 또는 이미 만료)."""
    venture_row = profile.get("venture")
    if not venture_row:
        return None

    as_of = as_of or date.today()
    valid_until = _parse_date(venture_row.get("벤처유효종료일"))
    if not valid_until:
        return None

    days_left = (valid_until - as_of).days
    if days_left < 0:
        return {
            "rule": "C2",
            "level": "확인필요",
            "message": f"벤처 인증이 {-days_left}일 전({valid_until.isoformat()})에 만료되었습니다.",
            "question": (
                f"벤처기업 인증이 {valid_until.isoformat()}자로 만료된 상태입니다. 현재 홍보물·"
                "제출서류에 '벤처기업'으로 표기하고 있다면 근거는 무엇입니까? 재확인 신청 진행 상황과 "
                "유효한 인증서 사본을 제출해 주십시오."
            ),
        }
    if days_left <= C2_EXPIRY_WARNING_DAYS:
        return {
            "rule": "C2",
            "level": "확인필요",
            "message": f"벤처 인증이 {days_left}일 후({valid_until.isoformat()}) 만료됩니다.",
            "question": (
                f"벤처기업 인증 만료일({valid_until.isoformat()})이 {days_left}일 앞으로 다가왔습니다. "
                "재확인(갱신) 신청을 진행 중입니까? 신청 접수증 또는 예정 일정을 확인해 주십시오."
            ),
        }
    return None


def check_d1_no_financials(dart_result: dict | None) -> dict | None:
    """DART status가 013(조회 데이터 없음)이거나 DART 미등록이면 중립 표기."""
    if not dart_result or dart_result.get("status") == "013":
        return {
            "rule": "D1",
            "level": "중립",
            "message": "초기단계, 공시의무 없음 (DART 미등록 또는 재무 데이터 없음)",
            "question": (
                "외부감사·공시 대상이 아닌 초기 단계로 확인됩니다(재무 미확보는 감점 사유가 아님). "
                "심층심사를 위해 최근 3개년 재무제표 또는 결산서·부가가치세 신고서 등 매출·자본 확인 "
                "자료를 제출해 주십시오."
            ),
        }
    return None


def check_d2_all_axes_empty(profile: dict) -> dict | None:
    """벤처확인·특허·DART 세 축이 전부 공백인 경우."""
    has_venture = bool(profile.get("venture"))
    has_patent = (profile.get("patent") or {}).get("totalCount", 0) > 0
    has_dart = bool(profile.get("dart"))

    if not has_venture and not has_patent and not has_dart:
        return {
            "rule": "D2",
            "level": "판단보류",
            "message": "벤처확인·특허·DART 세 축 모두 공백 — 근거 불충분, 판단 보류.",
            "question": (
                "공개 데이터(벤처확인·특허·DART) 어느 축에서도 이 기업의 기록을 확인할 수 없습니다. "
                "사업자등록증, 주요 매출·계약 증빙, 보유 기술·인증 자료 일체를 제출해 주십시오. "
                "제출 전까지 스크리닝 결과는 '판단 보류'입니다."
            ),
        }
    return None


# 각 플래그를 심사역이 심층심사 질의서에 붙여 쓸 수 있는 문항 형태로 뽑아낸다 (CLAUDE.md 0.1/3절).
_RULE_TITLES = {
    "A1": "기술 근거 확인",
    "A2": "특허 법인 귀속 확인",
    "C1": "투자 후 활동 확인",
    "C2": "인증 유효성 확인",
    "D1": "재무 자료 요청",
    "D2": "기초 자료 요청",
}


def to_interview_questions(flags: list[dict]) -> list[dict]:
    """run_all() 결과 → [{"rule", "title", "level", "question"}] 심층심사 질의서 시드."""
    out = []
    for f in flags:
        q = f.get("question")
        if not q:
            continue
        out.append({
            "rule": f["rule"],
            "title": _RULE_TITLES.get(f["rule"], f["rule"]),
            "level": f.get("level"),
            "question": q,
        })
    return out


def run_all(profile: dict, dart_result: dict | None = None, as_of: date | None = None) -> list[dict]:
    checks = [
        check_a1_deeptech_no_patent(profile, as_of),
        check_a2_individual_applicant(profile),
        check_c1_investment_activity_stall(profile, as_of),
        check_c2_certification_expiring(profile, as_of),
        check_d1_no_financials(dart_result),
        check_d2_all_axes_empty(profile),
    ]
    return [c for c in checks if c]
