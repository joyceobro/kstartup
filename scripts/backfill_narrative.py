"""
data/cache/*.json 의 각 항목에 LLM 근거 서술(narrative)을 채워 넣는다.

배포 데모(디플리·삼성전자 등)는 캐시 파일을 그대로 서빙하므로, LLM_API_KEY를
설정한 상태에서 이 스크립트를 한 번 돌려 캐시에 narrative를 구워두면 배포 환경에서
매 요청마다 LLM을 호출하지 않고도 종합 서술이 보인다 (CLAUDE.md 8절: 캐시 우선).
기본 프로바이더는 Google Gemini(OpenAI 호환 엔드포인트, 무료 티어) — core/narrative.py 참고.

키가 없으면 narrative 키만 null로 정규화하고 종료한다 (파이프라인·프론트는 그대로 동작).

실행:
    ./.venv/Scripts/python.exe -m scripts.backfill_narrative
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

try:  # 이 스크립트는 collector를 안 거치므로 .env를 직접 로드한다
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:  # pragma: no cover
    pass

from core import narrative  # noqa: E402

CACHE_DIR = Path(__file__).resolve().parent.parent / "data" / "cache"


def main() -> None:
    try:  # Windows 콘솔(cp949)에서도 한글 출력이 깨지지 않게
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

    has_key = bool(narrative._api_key())
    if not has_key:
        print("LLM_API_KEY 미설정 — narrative 키를 null로만 정규화합니다.")

    for path in sorted(CACHE_DIR.glob("*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))

        narr = narrative.generate_narrative(data) if has_key else None
        if narr:
            data["narrative"] = {
                "summary": narr["summary"],
                "model": narr["model"],
                "is_ai_generated": True,
            }
            refined = {q["rule"]: q["question"] for q in narr.get("questions", [])}
            for iq in data.get("interview_questions", []):
                if iq["rule"] in refined:
                    iq["question"] = refined[iq["rule"]]
                    iq["ai_refined"] = True
            status = f"narrative OK ({len(refined)} questions refined)"
        else:
            data.setdefault("narrative", None)
            status = "narrative=null"

        path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        print(f"  {path.name}: {status}")


if __name__ == "__main__":
    main()
