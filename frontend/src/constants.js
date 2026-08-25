// 출처 문자열(core/scoring.py의 SOURCE 상수) → 사람이 검증하러 갈 수 있는 공식 사이트 링크.
// 딥링크(특정 기업 페이지)는 파라미터 형식이 불확실해 만들지 않는다 — 공식 홈페이지로만 연결.
export const SOURCE_LINKS = {
  "KIPRISPlus patUtiModInfoSearchSevice/getAdvancedSearch": "https://www.kipris.or.kr",
  "data.go.kr 중소벤처기업부_벤처기업명단(15084581)": "https://www.data.go.kr/data/15084581/openapi.do",
};

export const DART_HOME = "https://dart.fss.or.kr";

export const AXIS_LABELS = {
  technology: "기술력",
  investment: "투자이력",
  credibility: "공신력",
};

export const AXIS_DESCRIPTIONS = {
  technology: "특허 출원·등록 건수, IPC 분류 다양성, 연구개발형 벤처인증 여부",
  investment: "벤처확인유형이 '벤처투자유형'인지 여부 (금액·시기는 소스에 없어 이진 플래그로 근사)",
  credibility: "벤처확인 보유 여부 및 인증 유효기간",
};

// tier 문자열 → 배지 색상 톤. '없음' 계열은 경고색이 아니라 중립색으로 처리한다
// (CLAUDE.md 1절: 데이터 부재/미보유를 저평가로 처벌하지 않는다).
export const TIER_TONE = {
  "높음": "positive",
  "있음": "positive",
  "유효": "positive",
  "보통": "info",
  "낮음": "caution",
  "만료임박": "caution",
  "없음": "neutral",
  "정보없음": "neutral",
  "데이터없음": "neutral",
  "확인불가": "neutral",
  "만료": "negative",
};

export const FLAG_LEVEL_TONE = {
  "확인필요": "caution",
  "중립": "info",
  "판단보류": "neutral",
};

export const RULE_LABELS = {
  A1: "기술 과장 — R&D형 인증 대비 특허 정체",
  A2: "기술 과장 — 개인 명의 출원 의심",
  C1: "정합성 — 투자 인증 후 활동 정체",
  C2: "정합성 — 인증 만료·임박",
  D1: "데이터 부재 — 재무 미확보",
  D2: "데이터 부재 — 전 축 공백",
};

export const MATCH_CONFIDENCE_LABELS = {
  verified: { label: "교차검증됨", tone: "positive", desc: "벤처확인·DART 양쪽에서 동일 기업명 확인" },
  name_only: { label: "기업명 매칭", tone: "info", desc: "단일 소스에서 기업명 일치로 매칭 (동명이인 보정 없음)" },
  unmatched: { label: "매칭 실패", tone: "neutral", desc: "어느 소스에서도 기업명이 일치하지 않음" },
};
