"""
OpenDART(opendart.fss.or.kr) 수집기 — 재무(보조) 축.

1) download_corp_code(): 고유번호(corp_code) 전체를 최초 1회 내려받아
   data/corp_code.xml 에 캐싱한다 (공식 문서: 응답은 zip 안에 CORPCODE.xml).
2) find_corp_code(): 기업명으로 8자리 corp_code를 찾는다.
3) get_financial_summary(): 단일회사 주요계정을 조회한다.

status "013"(조회된 데이터가 없습니다)은 에러가 아니라
CLAUDE.md의 D1 규칙 그대로 "초기단계, 공시의무 없음" 중립 표기 대상이다.
"""
from __future__ import annotations

import io
import os
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

import requests
from dotenv import load_dotenv

load_dotenv()

DART_KEY = os.environ.get("DART_KEY", "")
DATA_DIR = Path(__file__).resolve().parent.parent / "data"
CORP_CODE_PATH = DATA_DIR / "corp_code.xml"

CORP_CODE_URL = "https://opendart.fss.or.kr/api/corpCode.xml"
FNLTT_SINGL_ACNT_URL = "https://opendart.fss.or.kr/api/fnlttSinglAcnt.json"
COMPANY_URL = "https://opendart.fss.or.kr/api/company.json"

NO_DATA_STATUS = "013"  # 조회된 데이터가 없습니다 → D1 중립 표기 대상


class DartAPIError(RuntimeError):
    pass


def download_corp_code(force: bool = False) -> Path:
    """전체 고유번호 목록을 받아 data/corp_code.xml 로 캐싱한다."""
    if CORP_CODE_PATH.exists() and not force:
        return CORP_CODE_PATH
    if not DART_KEY:
        raise DartAPIError("DART_KEY가 .env에 설정되어 있지 않습니다.")

    resp = requests.get(CORP_CODE_URL, params={"crtfc_key": DART_KEY}, timeout=30)
    resp.raise_for_status()

    with zipfile.ZipFile(io.BytesIO(resp.content)) as zf:
        inner_name = next(n for n in zf.namelist() if n.upper().endswith(".XML"))
        xml_bytes = zf.read(inner_name)

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    CORP_CODE_PATH.write_bytes(xml_bytes)
    return CORP_CODE_PATH


_corp_code_cache: list[dict] | None = None


def load_corp_code_map() -> list[dict]:
    """[{corp_code, corp_name, corp_eng_name, stock_code, modify_date}, ...]"""
    global _corp_code_cache
    if _corp_code_cache is not None:
        return _corp_code_cache

    path = download_corp_code()
    root = ET.parse(path).getroot()
    result = []
    for el in root.findall(".//list"):
        result.append(
            {
                "corp_code": (el.findtext("corp_code") or "").strip(),
                "corp_name": (el.findtext("corp_name") or "").strip(),
                "corp_eng_name": (el.findtext("corp_eng_name") or "").strip(),
                "stock_code": (el.findtext("stock_code") or "").strip(),
                "modify_date": (el.findtext("modify_date") or "").strip(),
            }
        )
    _corp_code_cache = result
    return result


def find_corp_code(company_name: str) -> list[dict]:
    """기업명 부분일치로 후보를 반환한다 (동명이인 가능 → 여러 건일 수 있음)."""
    name = company_name.strip()
    return [row for row in load_corp_code_map() if name in row["corp_name"]]


def get_financial_summary(corp_code: str, bsns_year: str, reprt_code: str = "11011") -> dict:
    """단일회사 주요계정 조회.

    reprt_code: 11011=사업보고서, 11012=반기보고서, 11013=1분기, 11014=3분기
    반환: {"status": "000"/"013"/..., "accounts": [...]}
    status가 013이면 초기 기업 정상 케이스 — D1 중립 표기로 처리할 것.
    """
    if not DART_KEY:
        raise DartAPIError("DART_KEY가 .env에 설정되어 있지 않습니다.")

    params = {
        "crtfc_key": DART_KEY,
        "corp_code": corp_code,
        "bsns_year": bsns_year,
        "reprt_code": reprt_code,
    }
    resp = requests.get(FNLTT_SINGL_ACNT_URL, params=params, timeout=10)
    resp.raise_for_status()
    body = resp.json()

    status = body.get("status")
    if status == NO_DATA_STATUS:
        return {"status": status, "accounts": []}
    if status != "000":
        raise DartAPIError(f"DART API error {status}: {body.get('message')}")

    return {"status": status, "accounts": body.get("list", [])}


def get_company_overview(corp_code: str) -> dict:
    """기업개황 조회 — 사업자등록번호(bizr_no)/법인등록번호(jurir_no) 확보용.

    core/normalize.py의 개체 연결 교차검증에 쓴다. DART 미등록 기업은 애초에
    corp_code가 없으므로 이 함수 자체를 호출할 일이 없다 (find_corp_code 실패 시 스킵).
    """
    if not DART_KEY:
        raise DartAPIError("DART_KEY가 .env에 설정되어 있지 않습니다.")

    resp = requests.get(COMPANY_URL, params={"crtfc_key": DART_KEY, "corp_code": corp_code}, timeout=10)
    resp.raise_for_status()
    body = resp.json()

    if body.get("status") != "000":
        raise DartAPIError(f"DART API error {body.get('status')}: {body.get('message')}")
    return body


if __name__ == "__main__":
    import sys

    name = sys.argv[1] if len(sys.argv) > 1 else "삼성전자"
    for candidate in find_corp_code(name)[:5]:
        print(candidate)
