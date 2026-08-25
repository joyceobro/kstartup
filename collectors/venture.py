"""
공공데이터포털 — 중소벤처기업부 벤처기업명단 API 수집기 (투자이력·공신력 축).

[2026-08-20 실측 확정] 이 데이터셋(data.go.kr 15084581)은 odcloud 표준 API 방식이다.
  Base URL : https://api.odcloud.kr/api/15084581/v1/uddi:{리소스UUID}
  UUID는 스냅샷(월별 파일)마다 다르다 — 아래 LATEST_UUID를 최신 스냅샷으로 주기적으로 갱신해야 함.
  현재 최신: uddi:47b202c9-f0bb-43b4-949c-ebe9ef56ef02 (2026-05-21 기준 데이터)

파라미터: page, perPage, returnType(JSON/XML), serviceKey,
          cond[업체명::LIKE]=검색어  ← 부분일치 필터 (실측 확인됨)

⚠️ serviceKey 함정: data.go.kr은 "Encoding"/"Decoding" 두 버전의 키를 제공한다.
   requests의 params=는 자체적으로 퍼센트 인코딩을 하므로 Encoding 키를 넣으면
   이중 인코딩되어 "등록되지 않은 인증키" 401 에러가 난다.
   → urllib.parse.unquote()로 항상 한번 디코딩해서 보낸다 (이미 디코딩된 키를
      다시 unquote해도 무해하므로 안전).

응답 필드(실측): 연번, 업체명, 대표자명(익명 마스킹, 예 "이**"), 벤처확인유형,
  지역, 주소, 업종분류(기보), 업종명(11차), 주생산품,
  벤처유효시작일, 벤처유효종료일, 벤처확인기관, 신규_재확인
  ⚠️ CLAUDE.md가 기대한 "투자유치정보"(금액/시기) 필드는 이 데이터셋에 없다.
     투자이력 축 근거는 이 소스만으로는 부족 — W2에서 대안(예: 벤처확인 유형
     "벤처투자유형" 자체를 근거로 쓰거나 다른 소스 검토) 필요.
"""
from __future__ import annotations

import os
import urllib.parse

import requests
from dotenv import load_dotenv

load_dotenv()

DATA_GO_KR_KEY = os.environ.get("DATA_GO_KR_KEY", "")
LATEST_UUID = "47b202c9-f0bb-43b4-949c-ebe9ef56ef02"  # 2026-05-21 스냅샷
VENTURE_API_ENDPOINT = os.environ.get(
    "VENTURE_API_ENDPOINT",
    f"https://api.odcloud.kr/api/15084581/v1/uddi:{LATEST_UUID}",
)


class VentureAPIError(RuntimeError):
    pass


def _service_key() -> str:
    """Encoding/Decoding 키 어느 쪽이 .env에 있어도 안전하게 디코딩된 형태로 반환."""
    if not DATA_GO_KR_KEY:
        raise VentureAPIError("DATA_GO_KR_KEY가 .env에 설정되어 있지 않습니다.")
    return urllib.parse.unquote(DATA_GO_KR_KEY)


def search_venture(company_name: str, page: int = 1, per_page: int = 20) -> list[dict]:
    """기업명(부분일치)으로 벤처기업 확인 정보를 조회한다.

    비어있으면 벤처 미확인 기업 — "없음"으로 처리하고 감점하지 않는다 (CLAUDE.md D1 원칙).
    """
    params = {
        "serviceKey": _service_key(),
        "page": page,
        "perPage": per_page,
        "returnType": "JSON",
        "cond[업체명::LIKE]": company_name,
    }
    resp = requests.get(VENTURE_API_ENDPOINT, params=params, timeout=10)
    resp.raise_for_status()
    body = resp.json()

    if "data" not in body:
        raise VentureAPIError(f"venture API 예상치 못한 응답: {body}")

    return body["data"]


if __name__ == "__main__":
    import sys

    name = sys.argv[1] if len(sys.argv) > 1 else "테스트기업"
    try:
        rows = search_venture(name)
        print(rows if rows else "벤처확인 정보 없음 (정상 케이스 — 감점 아님)")
    except VentureAPIError as e:
        print(f"[venture] {e}")
