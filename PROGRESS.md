# 진행 상황 (2026-08-21 기준)

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

### 다음 세션 시작점 — 실제 배포 작업 (사용자 계정 필요, 직접 진행)

- [ ] git 첫 커밋 (아직 커밋 이력 없음 — `git add` 전 `git status`로 무엇이 올라가는지 확인,
      특히 `.env`가 안 들어가는지 재확인할 것)
- [ ] GitHub 원격 저장소 생성 + push
- [ ] Render: New → Blueprint → 위 저장소 연결 → `render.yaml` 자동 인식 확인 →
      `KIPRIS_KEY`/`DATA_GO_KR_KEY`/`DART_KEY` 대시보드에서 입력 → 배포 → 발급된 URL 확인
- [ ] Vercel: New Project → 저장소 연결 → Root Directory를 `frontend`로 지정 →
      환경변수 `VITE_API_BASE_URL` = 위 Render URL로 설정 → 배포
- [ ] Render `CORS_ORIGINS` 환경변수에 확정된 Vercel 도메인 입력 후 재배포(현재 `*`로 열려있어
      기능은 되지만, 도메인 확정되면 좁히는 게 원칙적으로 맞음)
- [ ] 배포된 URL로 디플리/삼성전자/존재하지 않는 기업 3케이스 재확인 (캐시 히트라 API 호출 없이 응답되어야 함)
- [ ] (선택) UptimeRobot 등으로 Render 슬립 방지 핑 설정
- [ ] 기획서·기능명세서 PDF 마무리
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
