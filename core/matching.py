"""
VC 매칭 — CLAUDE.md 5절 MVP 스코프: "룰 기반 데모 수준 (단계·업종·테마 태그 정합, 규모 최소)".

⚠️ CLAUDE.md 4절에 확정된 데이터 소스 중 VC 데이터베이스는 없다. 여기서 쓰는 data/vc_seed.json은
실존 VC의 투자 성향을 조사한 자료가 아니라 매칭 로직을 시연하기 위한 가상 시드 데이터다
(falsify.py의 6규칙, scoring.py의 3축과 달리 "출처가 붙는 결정론적 집계"가 아님 — 별도 기능임을
API 응답의 is_demo_data로 명시한다).

태그는 profile(core.normalize.resolve_entity 반환값)에서 결정론적으로 유도한다:
  단계   — 벤처확인유형 (예비벤처유형/벤처투자유형/그 외)
  업종   — 벤처확인 공시의 업종분류(기보)·업종명(11차)
  테마   — 특허 IPC 분류 → 기술 테마 매핑 (아래 _IPC_THEME_MAP)
"""
from __future__ import annotations

import json
from pathlib import Path

VC_SEED_PATH = Path(__file__).resolve().parent.parent / "data" / "vc_seed.json"

_IPC_THEME_MAP = {
    "G06N": "AI/머신러닝",
    "G06F": "소프트웨어·컴퓨팅",
    "G06T": "컴퓨터비전",
    "G06V": "컴퓨터비전",
    "G10L": "음성·오디오",
    "H04R": "음성·오디오",
    "H04S": "음성·오디오",
    "H04L": "네트워크·통신",
    "H04W": "네트워크·통신",
    "H04M": "네트워크·통신",
    "H04B": "네트워크·통신",
    "H04N": "영상통신·디스플레이",
    "G09G": "영상통신·디스플레이",
    "G01N": "센서·계측",
    "G01K": "센서·계측",
    "G01R": "센서·계측",
    "G02B": "센서·계측",
    "B25J": "로보틱스",
    "B60W": "모빌리티",
    "G05D": "제어시스템",
    "G16Y": "IoT",
    "G11C": "반도체",
    "H10B": "반도체",
    "H10D": "반도체",
    "H10K": "반도체",
    "H10N": "반도체",
    "H10P": "반도체",
    "H10W": "반도체",
    "A61B": "바이오·헬스케어",
    "A61K": "바이오·헬스케어",
    "A61P": "바이오·헬스케어",
    "A61N": "바이오·헬스케어",
}


def _load_vc_seed() -> list[dict]:
    return json.loads(VC_SEED_PATH.read_text(encoding="utf-8"))


def _infer_stage_tag(profile: dict) -> str:
    venture_row = profile.get("venture")
    if not venture_row:
        return "정보없음"
    confirm_type = venture_row.get("벤처확인유형")
    if confirm_type == "예비벤처유형":
        return "예비창업"
    if confirm_type == "벤처투자유형":
        return "투자유치이력있음"
    return "초기(투자전)"


def _infer_industry_tags(profile: dict) -> set[str]:
    venture_row = profile.get("venture") or {}
    return {
        tag
        for tag in (venture_row.get("업종분류(기보)"), venture_row.get("업종명(11차)"))
        if tag
    }


def _infer_theme_tags(profile: dict) -> set[str]:
    items = (profile.get("patent") or {}).get("items", [])
    themes = set()
    for it in items:
        for code in (it.get("ipcNumber") or "").split("|"):
            code = code.strip()[:4]
            if code in _IPC_THEME_MAP:
                themes.add(_IPC_THEME_MAP[code])
    return themes


def match_vcs(profile: dict, top_n: int = 5) -> dict:
    stage_tag = _infer_stage_tag(profile)
    industry_tags = _infer_industry_tags(profile)
    theme_tags = _infer_theme_tags(profile)

    candidates = []
    for vc in _load_vc_seed():
        reasons = []
        score = 0

        if stage_tag in vc.get("stage_tags", []):
            score += 2
            reasons.append(f"단계 일치: {stage_tag}")

        industry_overlap = industry_tags & set(vc.get("industry_tags", []))
        if industry_overlap:
            score += 2 * len(industry_overlap)
            reasons.append(f"업종 일치: {', '.join(sorted(industry_overlap))}")

        theme_overlap = theme_tags & set(vc.get("theme_tags", []))
        if theme_overlap:
            score += len(theme_overlap)
            reasons.append(f"테마 일치: {', '.join(sorted(theme_overlap))}")

        if score > 0:
            candidates.append({
                "vc_name": vc["name"],
                "match_score": score,
                "reasons": reasons,
                "vc_tags": {
                    "stage_tags": vc.get("stage_tags", []),
                    "industry_tags": vc.get("industry_tags", []),
                    "theme_tags": vc.get("theme_tags", []),
                },
            })

    candidates.sort(key=lambda c: c["match_score"], reverse=True)

    return {
        "is_demo_data": True,
        "note": "룰 기반 데모입니다. VC 목록은 실제 투자 성향 조사가 아닌 가상 시드 데이터입니다.",
        "inferred_tags": {
            "stage": stage_tag,
            "industry": sorted(industry_tags),
            "theme": sorted(theme_tags),
        },
        "matches": candidates[:top_n],
    }
