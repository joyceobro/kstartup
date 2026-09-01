# 진행 상황 (2026-08-31 기준)

> CLAUDE.md의 설계 원칙은 그대로 유효. 이 문서는 W1~W2에서 실제로 구현·검증된 내용과
> 실측 과정에서 CLAUDE.md 원 설계와 달라진 부분을 기록한다. 다음 세션은 이 문서 →
> CLAUDE.md → 코드 순으로 보면 빠르게 복귀 가능.

## 완료된 것 (W1 + W2)

### 프로젝트 스캐폴딩
- git 저장소 초기화, `.gitignore`(.env, .venv, data/corp_code.xml, data/cache/ 제외)
- `.env.example`, `requirements.txt`(requests, python-dotenv, lxml, fastapi, uvicorn)
- `.venv` 가상환경 구성 (Python 3.9 — `from __future__ import annotations` 필수, `X | None` 문법 런타임 평가 안 됨)

### 수집기 (collectors/) — 전부 실제 키로 검증 완료
| 파일 | 상태 | 비고 |
|---|---|---|
| `dart.py` | ✅ | corpCode(zip→xml 캐싱), fnlttSinglAcnt(재무), company.json(사업자/법인번호) |
| `venture.py` | ✅ | odcloud 방식, `cond[업체명::LIKE]` 필터로 부분검색 |
| `patent.py` | ✅ | 2단계 중 getAdvancedSearch만 승인됨. CommonSearchApplicantInfo는 미승인 → 기업명 직접 검색 폴백 |

### 핵심 로직 (core/)
- `normalize.py` — 개체 연결: 기업명 정규화(주식회사/㈜ 제거) + 완전일치. DART 매칭 시 사업자/법인번호 부가 노출
- `scoring.py` — 3축 결정론적 집계, 축마다 출처(source) 명시
- `falsify.py` — 6규칙(A1/A2/C1/C2/D1/D2) 전부 구현, 임계값 확정
- `pipeline.py` — 전체 오케스트레이션 + `data/cache/`(기업명별 JSON) 파일 캐싱

### 백엔드
- `main.py` — FastAPI, `GET /api/evaluate?company=`, `GET /health`
- 실행: `uvicorn main:app --reload`

## 실측하며 CLAUDE.md 원 설계와 달라진 부분 (중요)

1. **투자이력 축**: 원 설계는 "투자유치 금액·시기"를 벤처기업명단 API에서 가져오는 것이었으나,
   실제 응답엔 그 필드가 없음. → **벤처확인유형이 "벤처투자유형"인지 이진 플래그**로 재정의 (사용자 확정, 2026-08-20).
2. **개체 연결(정규화)**: 원 설계는 사업자/법인번호 기준 매칭이었으나, 벤처기업명단 API에도
   KIPRIS 응답에도 사업자/법인번호가 없음(DART에만 있고, DART는 초기기업 대부분 미등록).
   → **기업명+주소 근사매칭**을 기본 전략으로 채택 (사용자 확정, 2026-08-20). DART 매칭된 경우만 보너스로 번호 확보.
3. **공신력 축**: 원 설계는 "벤처/이노비즈/메인비즈 다층 보유"였으나, CLAUDE.md 4절에 확정된 데이터
   소스는 벤처기업명단 API뿐 — 이노비즈/메인비즈 API는 소스 목록에 없음. 현재는 벤처확인 단일
   소스로만 판정 (`core/scoring.py` 상단 주석에 명시). 필요하면 소스 추가 탐색 여지 있음.
4. **KIPRIS 인증키**: KIPRIS Plus는 회원가입만으로 전체 API가 열리지 않고, **오퍼레이션 단위로
   개별 활용신청·승인**이 필요함(data.go.kr과 유사). `getAdvancedSearch`는 승인받아 정상 동작 중.
   `CommonSearchApplicantInfo`(기업명→특허고객번호 정방향 검색)는 아직 미승인 — 필요시
   KIPRIS Plus에서 정확히 이 이름으로 재신청 필요. 지금은 기업명 직접 검색으로 폴백해 동작함
   (동명이인 보정 없음 — 알려진 한계).
5. **data.go.kr serviceKey 함정**: "Encoding"/"Decoding" 두 버전 키 중 Encoding을 그대로
   `requests.params`에 넣으면 이중 인코딩되어 401 남. `venture.py`가 `urllib.parse.unquote()`로
   항상 방어적으로 디코딩하도록 처리해둠 — 다른 data.go.kr API 추가할 때도 이 패턴 재사용할 것.

## 실제 테스트 결과 (참고용)

- **주식회사 디플리** (초기 벤처): 벤처확인 있음(혁신성장유형), 특허 10건(기술력 "보통"),
  DART 미등록(D1 중립), 벤처인증 만료(C2 플래그 — 오늘 기준 75일 초과)
- **삼성전자**: 특허 다수(기술력 "높음"), DART 매칭됨(사업자/법인번호 확보), 벤처 미해당
- **가상의 존재하지 않는 기업명**: D1+D2 동시 트리거, "근거 불충분, 판단보류"

## W3 진행 (2026-08-21)

### React 리포트 UI — ✅ 1차 완료
- `frontend/` — Vite + React(JS) 스캐폴딩. 무거운 UI 라이브러리 없이 순수 CSS.
- `src/api.js` — `GET /api/evaluate?company=` 호출, `VITE_API_BASE_URL` 환경변수로 백엔드 주소 분리
  (`.env.example` 참고, 기본값 `http://localhost:8000`).
- `src/constants.js` — 출처 문자열 → 공식 사이트 링크 매핑, tier/flag 색상 톤, 반증 규칙 라벨.
  ⚠️ 특허 개별 건이나 DART 기업 페이지로의 딥링크는 만들지 않음(정확한 URL 파라미터 형식을 확신할 수
  없어 만들지 않기로 함) — 축 단위로 KIPRIS/data.go.kr/DART 공식 홈페이지에만 연결.
- 화면 구성: 검색창 + 예시 기업 칩(디플리/삼성전자) → ProfileHeader(매칭 신뢰도) → 3축 ScoreCard →
  FlagList(반증 결과, "확인필요"=주의색이지 위험색 아님) → PatentList(접이식 표).
- **디자인 원칙 반영**: tier "없음"/"정보없음"류는 회색(neutral)로 처리, 빨간색(negative)은 "만료"처럼
  실제로 확인이 필요한 상태에만 사용 — CLAUDE.md 1절 "데이터 부재를 처벌하지 않는다" 원칙을 UI 색상에도
  적용한 것.
- 브라우저로 3가지 케이스(디플리/삼성전자/존재하지 않는 기업) 직접 조회해 렌더링 확인 완료.
  `npm run build`, `npx oxlint src` 통과.
- 아직 안 한 것: 반응형(모바일) 점검, 로딩 스피너 개선, 배포 설정.

### VC 매칭 데모 — ✅ 1차 완료
- `core/matching.py` — CLAUDE.md 5절 "룰 기반 데모 수준" 그대로 구현. 3축 점수(scoring.py)와 달리
  이건 결정론적 집계가 아니라 **데모**임을 응답에 `is_demo_data: true` + note로 명시.
- `data/vc_seed.json` — VC 8곳, 전부 **가상 시드 데이터**(실제 VC 투자 성향 조사 아님). 실존 VC 이름을
  쓰면 근거 없는 투자 성향을 사실처럼 보이게 할 위험이 있어 의도적으로 가상 이름 사용.
- 태그 유도 로직 (profile에서 결정론적으로 계산, 별도 API 호출 없음):
  - 단계 — 벤처확인유형(예비벤처/벤처투자/그 외)에서 3단계로 근사
  - 업종 — 벤처확인 공시의 업종분류(기보)·업종명(11차) 그대로 사용
  - 테마 — 특허 IPC 4자리 코드 → 기술 테마 매핑(`_IPC_THEME_MAP`, core/matching.py 상단)
- `core/pipeline.py`의 `evaluate()` 응답에 `vc_matches` 키 추가. 기존 캐시 2건(디플리/삼성전자)도
  라이브 API 재호출 없이 오프라인으로 `vc_matches`만 백필함(KIPRIS 트래픽 한도 보호).
- 프론트: `VcMatchList.jsx` — 추정 태그 + 매칭 VC 카드(점수·근거) 표시. 브라우저로 두 케이스 확인
  (삼성전자는 벤처확인이 없어 "정보없음" 단계 + 테마 태그만으로 매칭되는 것까지 확인함).
- 이 기능 자체가 CLAUDE.md 1절의 "AI가 점수를 판정하지 않는다" 원칙과는 별개 트랙임 — VC 매칭은
  원래부터 명시적으로 "데모"로 스코프됨. 3축 점수/반증 플래그에는 이 원칙이 그대로 유지됨.

## 배포 플랫폼 결정 (2026-08-24)

- **백엔드**: Render (무료 웹서비스)
- **프론트엔드**: Vercel

결정 이유: 둘 다 무료 티어 + git push 기반 자동배포. Render 무료 티어는 15분 미사용 시
슬립되어 첫 요청에 콜드스타트(수십 초) 발생 — 대회 생존 구간(9/7 11:00~9/11 23:59) 동안
접속이 "안 됨"으로 보이진 않지만 느릴 수 있음. 필요시 무료 외부 uptime 핑 서비스(UptimeRobot,
cron-job.org 등)로 15분 간격 헬스체크를 걸어 슬립을 방지하는 것을 권장 (별도 계정 필요, 미설정 상태).

### 배포 전 준비 완료 (이번 세션)

- `.gitignore`에서 `data/cache/` 제외 조항 삭제 — Render는 git 기반 배포라 런타임에 쓴 파일은
  재시작 시 사라짐. 데모 기업 캐시(`data/cache/*.json`)가 **커밋되어 있어야** 재배포/슬립 후
  기상 시에도 KIPRIS 실시간 호출 없이 즉시 응답 가능 (CLAUDE.md 8절 취지 그대로).
  `data/corp_code.xml`(29MB, DART에서 자동 재다운로드됨)과 `.env`는 계속 제외.
- `main.py`의 CORS를 `CORS_ORIGINS` 환경변수(콤마 구분)로 좁힐 수 있게 변경. 미설정 시 `"*"` 유지
  (로컬 개발 기본값 그대로 동작).
- `render.yaml` 추가 (Render Blueprint) — `uvicorn main:app --host 0.0.0.0 --port $PORT`,
  헬스체크 `/health`, `PYTHON_VERSION=3.9.12`(로컬 .venv와 동일 버전 고정).
  `KIPRIS_KEY`/`DATA_GO_KR_KEY`/`DART_KEY`/`CORS_ORIGINS`는 `sync: false`로 선언만 해둠 —
  실제 값은 Render 대시보드에서 직접 입력해야 함(레포에 커밋 안 됨).

### 배포 완료 (2026-08-25)

- [x] git 첫 커밋 (`27b3304`) — `.env`, `data/corp_code.xml` 제외 확인 완료
- [x] GitHub push — `github.com/joyceobro/kstartup` (origin은 기존에 SSH 별칭으로 이미 설정되어 있었음)
- [x] Render Blueprint 배포 — 서비스명 `kstartup-api`, URL `https://kstartup-api.onrender.com`
      (`KIPRIS_KEY`/`DATA_GO_KR_KEY`/`DART_KEY` 대시보드에 입력 완료, `/health` 200 확인)
- [x] Vercel 배포 — Root Directory `frontend`, Framework Preset을 Vite로 수동 지정
      (⚠️ 처음엔 저장소 루트의 `main.py`를 보고 Vercel이 FastAPI로 잘못 자동감지함 → Root Directory
      설정 후에도 Framework Preset은 수동으로 Vite로 바꿔줘야 했음).
      환경변수 `VITE_API_BASE_URL=https://kstartup-api.onrender.com` 설정.
      **최종 URL은 `https://kstartupcopy.vercel.app`** — 프로젝트 이름을 `kstartup`으로 바꿨지만
      `kstartup.vercel.app` 서브도메인은 이미 타 사용자가 선점 중이라(.vercel.app은 전역 유일)
      기존 자동생성 도메인(`kstartupcopy`)을 그대로 씀. 프로젝트 이름과 도메인이 다른 상태.
- [x] Render `CORS_ORIGINS=https://kstartupcopy.vercel.app` 설정 후 재배포, 정상 동작 확인
- [x] 배포된 URL로 디플리(Vercel→Render CORS 좁힌 뒤)·삼성전자(Vercel 초기 배포 직후) 확인 완료

## 재정의(2026-08-27) 코드 반영 (2026-08-31)

CLAUDE.md가 08-27에 "성장성 평가 & VC매칭" → **"기관 심사역용 심사 스크리닝 엔진"**으로
재정의됨. 08-21 시점 코드는 옛 프레이밍 기준이었어서 이번 세션에 아래를 반영:

- `core/falsify.py` — 6규칙 각 플래그에 **`question` 필드**(심층심사 질의 문항) 추가.
  `to_interview_questions(flags)` 헬퍼 신설 → `[{rule, title, level, question}]` 반환.
- `core/pipeline.py` — `evaluate()` 응답에 **`interview_questions`** 키 추가 (`flags`와 별개).
- `main.py` — FastAPI title/독스트링을 "근거 — 심사 스크리닝 엔진" 톤으로.
- `frontend/`:
  - `App.jsx` — 헤더 타이틀·소개문을 심사역 보조 톤으로. VcMatchList를 리포트 **맨 아래**로 이동.
  - `components/FlagList.jsx` — 각 플래그 아래 "심층심사 질문" 콜아웃 렌더, 섹션 제목/문구 변경.
  - `components/InterviewQuestionList.jsx` (**신규**) — "심층심사 질의서 시드 (자동 생성)" 섹션.
    질문 목록 + "전체 복사"(navigator.clipboard) 버튼. `interview_questions` 비면 렌더 안 함.
  - `components/VcMatchList.jsx` — 제목 "참고: … 힌트 (부가 데모)"로 격하, 부가 데모임을 note에 명시.
  - `App.css` — `.flag-item__question`, `.iq-section` 등 스타일 추가.
  - `index.html` — `<title>` 변경.
- `data/cache/*.json` (6건) — 오프라인 재생성. 저장된 profile로 `scoring.score_all` +
  `falsify.run_all`(dart_result는 `profile.dart.overview.status`로 합성) 재실행 후
  `interview_questions` 추가, 누락돼 있던 `vc_matches` 백필. 플래그 rule 셋은 재생성 전후 동일.
  ⚠️ `as_of`가 오늘로 바뀌어 디플리 C2 메시지 "75일 전"→"86일 전"으로 갱신됨 (의도된 변화).
- 검증: `compileall`, `pipeline.evaluate` 3케이스, `npm run build`, `npx oxlint src` 통과.
  로컬 백엔드+프론트 띄워 디플리 케이스 브라우저 렌더 확인 (플래그 콜아웃 + 질의서 시드 섹션 정상).
### 배포 반영 (2026-08-31)

- 커밋 `36a9e37`(재정의 반영) + `a1c406d`(빈 커밋, 배포 트리거) push 완료.
- **Render**: `36a9e37` 자동배포 확인 (openapi title v0.2.0, `/api/evaluate`에 `interview_questions`,
  CORS `access-control-allow-origin: https://kstartupcopy.vercel.app` 정상).
- **Vercel**: 8/25 이후 자동배포가 한 번도 안 걸려 있었음. 원인 = 프로젝트가 `joyceobro/kstartup`이
  아닌 다른 저장소(`kstartup_copy`)에 연결돼 있었고, 8/25 배포는 루트를 Python으로 오감지한 것.
  조치: 저장소를 `joyceobro/kstartup`으로 재연결 + `VITE_API_BASE_URL=https://kstartup-api.onrender.com`
  env var(Production) 설정 + `a1c406d` 빈 커밋으로 트리거. 이번엔 Vite 빌드 정상 (번들 `index-GXUvU7H1.js`,
  title "근거 …", `심층심사 질의서 시드` 문구 포함, `kstartup-api.onrender.com` 하드코딩됨).
  - Vercel 팀/프로젝트 slug: `inwhites-projects` / `kstartup` (도메인은 여전히 `kstartupcopy.vercel.app`).

## LLM 근거 서술 레이어 (2026-08-31 신설 → 2026-09-01 Gemini 전환)

대회 필수항목(기획서 5번 "생성형 AI 모델 적용 방안") 대응. 기존 코드엔 LLM 호출이 전혀
없었음 → 단일 LLM 호출 레이어 추가. **핵심 원칙 유지: 점수·등급은 결정론 집계 그대로,
LLM은 서술·문장화만** (CLAUDE.md 1절 Non-self-grading).

> 2026-09-01: 유료 Claude API → **무료 LLM(기본 Google Gemini `gemini-3.6-flash`,
> OpenAI 호환 엔드포인트)**로 전환. `openai` SDK 하나로 `LLM_BASE_URL`만 바꾸면
> Groq·OpenRouter·Cerebras 등으로도 교체 가능. 반환 스키마·파이프라인·프론트 계약 불변.
> 아래 서술은 전환 후 현재 상태 기준. (구현 이력: 커밋 `27224ae`가 Claude 버전, 이후 커밋에서 전환.)
> ※ `gemini-2.0-flash`/`2.5-flash`는 신규 사용자에게 종료(404) → `gemini-3.6-flash` 사용.
> 무료 등급 키(AI Studio, `AQ.Ab8…` 형식)로 실호출 검증 완료.

- `core/narrative.py` — `generate_narrative(result)`:
  - 입력: 결정론 결과 JSON에서 원천값만 추림(`_compact_input`).
  - 출력: `{summary(종합 서술 3~5문장), questions[{rule, question}](플래그별 질의문항 다듬기), model, is_ai_generated}`.
  - `openai` SDK, `client.chat.completions.create(model=<LLM_MODEL>, temperature=0.2, max_tokens=4000,
    response_format={"type":"json_object"})`. JSON 스키마는 `_SCHEMA_HINT`로 프롬프트에 명시.
    `json_object` 미지원 프로바이더 대비 → 강제 모드 실패 시 일반 모드 재시도 → `_extract_json` 폴백.
  - **`LLM_API_KEY`(또는 `GEMINI_API_KEY`) 미설정 / SDK 없음 / API 오류 → None 반환.** 파이프라인·배포 URL 생존 불변.
  - 환경변수: `LLM_API_KEY`(활성화 스위치), `LLM_BASE_URL`(기본 Gemini OpenAI 호환),
    `LLM_MODEL`(기본 `gemini-3.6-flash`).
- `core/pipeline.py` — `_attach_narrative()`: `evaluate()` 응답에 `narrative` 키 추가. LLM이 다듬은
  질의문항은 `interview_questions[].question`을 rule 단위로 덮어쓰고 `ai_refined: true` 표시(원본은 fallback). (전환과 무관, 그대로.)
- `scripts/backfill_narrative.py` — `data/cache/*.json`에 narrative를 구워넣는 1회성 스크립트.
  `.env` 직접 로드(collector 미경유). 키 없으면 `narrative: null`로만 정규화.
  **2026-09-01 실키로 실행 완료 → 데모 6건 전부 `narrative OK`** (디플리·문와쳐·파인하우스·존재하지않는… 2건씩,
  몬스터라이엇 1건, 삼성전자 0건 refine).
- `requirements.txt`: `openai>=1.40,<2` (anthropic 제거. .venv/Render 모두 Python 3.9 — openai 1.x는 3.8+ 지원).
- `.env.example` / `render.yaml`: `LLM_API_KEY` (sync:false). `ANTHROPIC_API_KEY`는 삭제.
- 프론트: `NarrativeSummary.jsx`("종합 근거 서술" 섹션 + "AI 생성" 배지, model 폴백 문구 `"생성형 AI"`),
  App.jsx에서 ProfileHeader 아래 배치. InterviewQuestionList에 ✎(AI 다듬음) 마커.
- 검증(2026-09-01): `py_compile`, 키 없는 경로(`None` / `narrative=null`) + **`gemini-3.6-flash` 실호출**
  (디플리 케이스 summary 323자 + C2/D1 질의문항 2건 생성) 모두 확인.
- 커밋 `c59a29a`(Claude→Gemini 전환) push 완료. 이후 모델명 `gemini-3.6-flash` 수정 + 캐시 backfill 커밋 진행.

## 기획서 초안 (2026-08-31, 미완)

- `docs/기획서.md` 작성 완료 (커밋 안 함). hwpx 양식 7개 항목에 1:1 대응. 실제 구현 근거로 작성.
- **내일 할 일**:
  - `<<팀명>>` `<<팀장 성명>>` 채우기
  - 검토: ① 항목 3 "금융 고객 = 기관 심사역(B2B)" 프레이밍이 템플릿 retail 예시와 달라도 괜찮은지
    ② 항목 5 후반 "비정형 데이터 분석"을 "향후 적용"으로 명시한 톤 — 심사 약점으로 보일지
  - 확정 후 한글(.hwpx) 양식에 항목 번호·소제목 그대로 옮겨넣기 → PDF
  - 기능명세서(별도 문서) 착수

### 배포 전 남은 일 (LLM 서술)

- [x] Gemini 전환 코드 커밋·push (`c59a29a`).
- [x] AI Studio 무료 키 발급 → 로컬 `.env`에 `LLM_API_KEY=...`.
- [x] `scripts.backfill_narrative` 실행 → 데모 캐시 6건 narrative 구움. (모델명 수정분과 함께 커밋 진행)
- [ ] **Render 대시보드 → Environment → `LLM_API_KEY` 추가 / 기존 `ANTHROPIC_API_KEY` 삭제** (비캐시 기업 라이브 조회용).
- [ ] 배포 URL에서 디플리 케이스에 "종합 근거 서술" 섹션 뜨는지 확인.
      (캐시 서빙이라 Render 키 없어도 데모는 서술 보임. Render 키는 비캐시 기업 라이브 조회 때만 필요.)

### 다음 세션 시작점 (내일)

- [ ] `docs/기획서.md` 검토·팀명 채우기·확정 → 한글 양식 이관 → PDF (위 "기획서 초안" 절 참고)
- [ ] 기능명세서 착수
- [ ] Render Environment에 `LLM_API_KEY` 추가 (`ANTHROPIC_API_KEY` 삭제) — 위 "배포 전 남은 일" 참고
- [ ] (선택) UptimeRobot 등으로 Render 슬립 방지 핑 설정
- [ ] (여유 있으면) KIPRIS `CommonSearchApplicantInfo` 승인받아 동명이인 보정 강화
- [ ] (여유 있으면) 공신력 축 — 이노비즈/메인비즈 소스 추가 조사
- [ ] (여유 있으면) 반응형(모바일) 점검, 로딩 스피너 개선

## 실행 방법 (재개 시)

```bash
cd kstartup
./.venv/Scripts/python.exe -m uvicorn main:app --reload
# 또는 직접 파이프라인만 테스트:
./.venv/Scripts/python.exe -c "from core.pipeline import evaluate; print(evaluate('기업명'))"

# 프론트엔드 (별도 터미널)
cd frontend
npm run dev   # http://localhost:5173, 백엔드는 8000번 포트에 떠 있어야 함
```

`.env`에 KIPRIS_KEY/DATA_GO_KR_KEY/DART_KEY 세팅 완료된 상태 (내용은 커밋 안 됨, 로컬에만 존재).
아직 git commit은 하지 않은 상태 — 사용자가 명시적으로 요청하면 진행.
