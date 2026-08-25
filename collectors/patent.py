"""
KIPRISPlus(plus.kipris.or.kr) 2단계 특허 수집기 — 기술력 축.

1단계 — 공통 REST 출원인 검색 (CommonSearchService/CommonSearchApplicantInfo)
  입력: searchName(기업명), searchAddress(동명이인 보정용)
  출력: PersonNumber(특허고객번호) ← 2단계 조회 키

2단계 — 특허·실용 항목별검색 전체검색 (patUtiModInfoSearchSevice/getAdvancedSearch)
  입력: applicant(PersonNumber 또는 출원인명), lastvalue(권리상태),
        applicationDate(YYYYMMDD~YYYYMMDD), patent/utility, numOfRows, sortSpec, descSort
  출력: totalCount, registerStatus, ipcNumber, applicationDate, applicantName ...

⚠️ 인증키 파라미터명이 오퍼레이션마다 다르다:
   - CommonSearchApplicantInfo → accessKey (KIPRIS Plus 자체 발급키)
   - getAdvancedSearch         → ServiceKey (공공데이터포털 방식)
   둘 다 .env의 KIPRIS_KEY 값을 그대로 쓰되, 파라미터명만 다르게 보낸다.
   실제 계정으로 최초 호출 시 401/에러가 나면 이 부분부터 의심할 것 (CLAUDE.md 4절 경고).

⚠️ 폐기예정 getWordSearch는 쓰지 않는다.
⚠️ 개발단계 계정은 트래픽 한도가 있으므로 데모 기업 결과는 상위에서 캐싱한다.

[2026-08-20 실측] KIPRIS_KEY로 실제 호출 검증 결과:
  - getAdvancedSearch          : 승인됨, 정상 동작 (ServiceKey=KIPRIS_KEY, "삼성전자"로 실데이터 확인)
  - CommonSearchApplicantInfo  : 미승인 (resultCode 30, AccessKey&ServiceID Is Not Registerd Error)
    → KIPRIS Plus 마이페이지에서 "출원인정보" 계열 오퍼레이션 개별 활용신청 필요.
    → 승인 전까지는 get_patent_summary()가 기업명을 applicant로 바로 넘겨 2단계만으로 동작(아래 폴백).
    → 동명이인 보정이 안 되므로 승인 후 반드시 PersonNumber 경로로 전환할 것.
"""
from __future__ import annotations

import os
from xml.etree import ElementTree as ET

import requests
from dotenv import load_dotenv

load_dotenv()

KIPRIS_KEY = os.environ.get("KIPRIS_KEY", "")

APPLICANT_INFO_URL = "http://plus.kipris.or.kr/openapi/rest/CommonSearchService/CommonSearchApplicantInfo"
ADVANCED_SEARCH_URL = "http://plus.kipris.or.kr/kipo-api/kipi/patUtiModInfoSearchSevice/getAdvancedSearch"

REGISTER_STATUS = {
    "등록": "R",
    "공개": "A",
    "소멸": "F",
    "무효": "I",
    "거절": "J",
}


class PatentAPIError(RuntimeError):
    pass


def _xml_items_to_dicts(xml_text: str) -> list[dict]:
    root = ET.fromstring(xml_text)
    items = []
    for item in root.findall(".//item"):
        items.append({child.tag: (child.text or "").strip() for child in item})
    return items


def _xml_total_count(xml_text: str) -> int:
    root = ET.fromstring(xml_text)
    count_text = root.findtext(".//totalCount") or root.findtext(".//count") or "0"
    try:
        return int(count_text)
    except ValueError:
        return 0


def search_applicant_person_number(company_name: str, address: str | None = None) -> list[dict]:
    """기업명(+주소)으로 특허고객번호(PersonNumber) 후보를 조회한다."""
    if not KIPRIS_KEY:
        raise PatentAPIError("KIPRIS_KEY가 .env에 설정되어 있지 않습니다.")

    params = {"accessKey": KIPRIS_KEY, "searchName": company_name}
    if address:
        params["searchAddress"] = address

    resp = requests.get(APPLICANT_INFO_URL, params=params, timeout=10)
    resp.raise_for_status()
    return _xml_items_to_dicts(resp.text)


def search_patents(
    applicant: str,
    last_value: str | None = None,
    application_date: str | None = None,
    patent: bool = True,
    utility: bool = True,
    num_of_rows: int = 100,
    sort_spec: str = "AD",
    desc_sort: bool = True,
) -> dict:
    """출원인(PersonNumber 또는 출원인명)으로 특허·실용신안 전체검색.

    application_date: "YYYYMMDD~YYYYMMDD" 형식.
    반환: {"totalCount": int, "items": [...]}
    """
    if not KIPRIS_KEY:
        raise PatentAPIError("KIPRIS_KEY가 .env에 설정되어 있지 않습니다.")

    params = {
        "ServiceKey": KIPRIS_KEY,
        "applicant": applicant,
        "patent": str(patent).lower(),
        "utility": str(utility).lower(),
        "numOfRows": num_of_rows,
        "sortSpec": sort_spec,
        "descSort": str(desc_sort).lower(),
    }
    if last_value:
        params["lastvalue"] = last_value
    if application_date:
        params["applicationDate"] = application_date

    resp = requests.get(ADVANCED_SEARCH_URL, params=params, timeout=10)
    resp.raise_for_status()
    return {"totalCount": _xml_total_count(resp.text), "items": _xml_items_to_dicts(resp.text)}


def get_patent_summary(company_name: str, address: str | None = None) -> dict:
    """1단계(PersonNumber 조회) → 2단계(전체 특허 조회)를 이어서 실행하는 편의 함수.

    PersonNumber를 못 찾으면 기업명으로 바로 2단계를 시도한다 (동명이인 리스크 있음 → 로그만 남김).
    """
    candidates = search_applicant_person_number(company_name, address)
    applicant_key = candidates[0].get("PersonNumber") if candidates else company_name

    result = search_patents(applicant_key)
    return {
        "applicant_key": applicant_key,
        "matched_by_person_number": bool(candidates),
        "totalCount": result["totalCount"],
        "items": result["items"],
    }


if __name__ == "__main__":
    import sys

    name = sys.argv[1] if len(sys.argv) > 1 else "테스트기업"
    try:
        summary = get_patent_summary(name)
        print(f"applicant_key={summary['applicant_key']} totalCount={summary['totalCount']}")
    except PatentAPIError as e:
        print(f"[patent] {e}")
