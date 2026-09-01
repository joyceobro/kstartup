"""
LLM 근거 서술 레이어 — CLAUDE.md 1절 "LLM은 딱 필요한 곳에만".

생성형 AI의 역할은 딱 두 가지다:
  1. 결정론적 3축 팩트시트 + 6규칙 플래그를 심사역용 자연어 "종합 근거 서술"로 옮긴다.
  2. 각 반증 플래그를 해당 기업 맥락을 반영한 "심층심사 질의 문항"으로 다듬는다.

절대 하지 않는 것 (CLAUDE.md 1절 Non-self-grading):
  - 점수·등급·투자적격 판정. tier/score를 바꾸거나 재해석하지 않는다.
  - JSON에 없는 사실 생성. 데이터 부재를 결점으로 서술.

무료 LLM(기본: Google Gemini의 OpenAI 호환 엔드포인트)을 쓴다. openai SDK 하나로
base_url만 바꾸면 Groq·OpenRouter·Cerebras 등 다른 무료 프로바이더로도 교체 가능하다.

  LLM_API_KEY   활성화 스위치 (미설정 시 서술 레이어 off → None)
  LLM_BASE_URL  기본 https://generativelanguage.googleapis.com/v1beta/openai/
  LLM_MODEL     기본 gemini-3.6-flash

키 미설정 또는 API 오류 시 None을 반환한다 — 배포 URL 생존이 최우선이므로(CLAUDE.md 8절)
서술 레이어 실패가 결정론 파이프라인을 막지 않는다.
"""
from __future__ import annotations

import json
import os

try:  # SDK가 없더라도 결정론 파이프라인은 그대로 동작해야 한다
    from openai import OpenAI
except ImportError:  # pragma: no cover
    OpenAI = None

_DEFAULT_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/openai/"
_DEFAULT_MODEL = "gemini-3.6-flash"


def _api_key() -> str | None:
    return os.environ.get("LLM_API_KEY") or os.environ.get("GEMINI_API_KEY")


def _model() -> str:
    return os.environ.get("LLM_MODEL", _DEFAULT_MODEL)


_SYSTEM = """당신은 정책금융·기술보증기금/신용보증기금·은행 여신 심사역을 보조하는 분석 도우미다.
입력으로 '결정론적으로 집계된' 초기 벤처기업 팩트시트(3축 tier + 6규칙 확인필요 플래그)를 JSON으로 받는다.

역할은 다음 두 가지뿐이다:
1) summary: 팩트시트를 심사의견서에 그대로 첨부 가능한 건조한 실무체 국문 3~5문장으로 요약한다.
   - 이미 집계된 tier·수치를 인용만 하고 재판정·재해석하지 않는다.
   - 심사역이 심층심사에서 추가로 확인하면 좋을 지점을 사실 기반으로 짚는다.
2) questions: 입력 flags[] 각 항목을 해당 기업 상황을 반영한 심층심사 질의 문항 한 문장으로 다듬는다.
   - 입력 플래그의 rule 값을 그대로 유지한다. flags가 비면 빈 배열.

엄격한 금지사항:
- 점수·등급·투자적격 여부를 새로 판정하거나 바꾸지 않는다("성장성 높음", "투자 부적격" 등 금지).
- 입력 JSON에 없는 사실(매출액·고용·경쟁사 등)을 지어내지 않는다.
- 재무·특허 데이터 부재를 결점으로 서술하지 않는다. 초기 기업에는 정상이다.
- 확인이 필요한 사항은 단정하지 말고 "확인 필요"로 명시한다."""

_SCHEMA_HINT = """반드시 아래 형태의 JSON 객체 '하나만' 출력한다. 코드블록·해설·서두 금지.
{
  "summary": "심사의견서용 건조한 실무체 국문 3~5문장",
  "questions": [
    {"rule": "<입력 flags[].rule 문자열 그대로>", "question": "심층심사 질의 문항 한 문장"}
  ]
}
입력 flags가 비어 있으면 "questions"는 빈 배열([])."""


def _compact_input(result: dict) -> dict:
    """토큰 절약 + 프롬프트 인젝션 표면 축소를 위해 원천값만 추린다."""
    profile = result.get("profile", {})
    venture = profile.get("venture")
    dart = profile.get("dart") or {}
    overview = dart.get("overview", {}) if isinstance(dart, dict) else {}
    scores = result.get("scores", {})
    return {
        "company": profile.get("input_name"),
        "match_confidence": profile.get("match_confidence"),
        "venture_confirmation": venture,
        "dart_overview": (
            {k: overview.get(k) for k in ("corp_name", "est_dt", "induty_code")}
            if dart
            else None
        ),
        "scores": {
            axis: {
                "tier": s.get("tier"),
                "metrics": s.get("metrics"),
                "source": s.get("source"),
            }
            for axis, s in scores.items()
        },
        "flags": [
            {"rule": f.get("rule"), "level": f.get("level"), "message": f.get("message")}
            for f in result.get("flags", [])
        ],
    }


def _extract_json(text: str):
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start, end = text.find("{"), text.rfind("}")
        if 0 <= start < end:
            try:
                return json.loads(text[start : end + 1])
            except json.JSONDecodeError:
                return None
    return None


def _create(client, model, messages, *, json_mode):
    kwargs = dict(model=model, max_tokens=4000, temperature=0.2, messages=messages)
    if json_mode:
        kwargs["response_format"] = {"type": "json_object"}
    return client.chat.completions.create(**kwargs)


def generate_narrative(result: dict) -> dict | None:
    key = _api_key()
    if OpenAI is None or not key:
        return None

    model = _model()
    payload = json.dumps(_compact_input(result), ensure_ascii=False, indent=2)
    messages = [
        {"role": "system", "content": _SYSTEM + "\n\n" + _SCHEMA_HINT},
        {"role": "user", "content": payload},
    ]

    try:
        client = OpenAI(
            api_key=key,
            base_url=os.environ.get("LLM_BASE_URL", _DEFAULT_BASE_URL),
        )
    except Exception:  # SDK 초기화 실패 — 서술만 건너뛴다
        return None

    # json_object 미지원 프로바이더/모델도 있으므로 강제 모드 → 일반 모드 순으로 시도.
    response = None
    for json_mode in (True, False):
        try:
            response = _create(client, model, messages, json_mode=json_mode)
            break
        except Exception:  # 네트워크·인증·레이트리밋·파라미터 비호환 등 무엇이든
            continue
    if response is None:
        return None

    try:
        text = (response.choices[0].message.content or "").strip()
    except (AttributeError, IndexError):
        return None
    data = _extract_json(text)
    if not isinstance(data, dict) or not data.get("summary"):
        return None

    raw_questions = data.get("questions")
    questions = [
        {"rule": q.get("rule"), "question": str(q.get("question", "")).strip()}
        for q in (raw_questions if isinstance(raw_questions, list) else [])
        if isinstance(q, dict) and q.get("rule") and q.get("question")
    ]
    return {
        "summary": str(data["summary"]).strip(),
        "questions": questions,
        "model": model,
        "is_ai_generated": True,
    }
