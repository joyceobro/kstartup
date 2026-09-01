"""
"근거" — 초기 벤처기업 심사 스크리닝 엔진 API (기관 심사역용). CLAUDE.md 5절 MVP 스코프:
기업명(+주소) 입력 → 3소스 수집 → 3축 근거형 팩트시트 → 반증 플래그 → 심층심사 질의 문항
→ LLM 종합 근거 서술(선택, LLM_API_KEY 있을 때. 기본 Gemini OpenAI 호환).

실행: uvicorn main:app --reload
"""
import os

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from core.pipeline import evaluate

app = FastAPI(title="근거 — 초기 벤처기업 심사 스크리닝 엔진 API", version="0.2.0")

# CORS_ORIGINS="https://foo.vercel.app,https://bar.com" 형태로 배포 환경에서 좁힐 것.
# 미설정 시 "*" (로컬 개발 기본값).
_cors_origins_env = os.environ.get("CORS_ORIGINS", "").strip()
_allow_origins = [o.strip() for o in _cors_origins_env.split(",") if o.strip()] or ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_allow_origins,
    allow_methods=["GET"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/api/evaluate")
def api_evaluate(company: str, refresh: bool = False) -> dict:
    company = company.strip()
    if not company:
        raise HTTPException(status_code=400, detail="company 파라미터가 필요합니다.")

    result = evaluate(company, refresh=refresh)

    if result["profile"]["match_confidence"] == "unmatched" and result["scores"]["technology"]["metrics"]["total_count"] == 0:
        raise HTTPException(
            status_code=404,
            detail=f"'{company}'에 대한 벤처확인·특허·DART 데이터를 찾을 수 없습니다.",
        )

    return result


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
