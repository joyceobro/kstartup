import { useState } from "react";
import { evaluateCompany, ApiError } from "./api";
import ProfileHeader from "./components/ProfileHeader";
import ScoreCard from "./components/ScoreCard";
import FlagList from "./components/FlagList";
import PatentList from "./components/PatentList";
import VcMatchList from "./components/VcMatchList";
import "./App.css";

const EXAMPLE_COMPANIES = ["주식회사 디플리", "삼성전자"];
const AXIS_ORDER = ["technology", "investment", "credibility"];

export default function App() {
  const [company, setCompany] = useState("");
  const [status, setStatus] = useState("idle"); // idle | loading | error | done
  const [error, setError] = useState(null);
  const [result, setResult] = useState(null);

  async function runEvaluate(name) {
    const target = name.trim();
    if (!target) return;

    setStatus("loading");
    setError(null);
    try {
      const data = await evaluateCompany(target);
      setResult(data);
      setStatus("done");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "알 수 없는 오류가 발생했습니다.");
      setStatus("error");
    }
  }

  function handleSubmit(e) {
    e.preventDefault();
    runEvaluate(company);
  }

  return (
    <div className="page">
      <header className="page__intro">
        <h1>초기 창업기업 성장성 리포트</h1>
        <p>
          공개 데이터(벤처확인·특허·DART)만을 근거로 3축 점수를 산출합니다. 점수는 AI가 매기지 않으며,
          모든 항목에 출처가 표시됩니다.
        </p>
      </header>

      <form className="search-bar" onSubmit={handleSubmit}>
        <input
          type="text"
          value={company}
          onChange={(e) => setCompany(e.target.value)}
          placeholder="기업명을 입력하세요 (예: 주식회사 디플리)"
        />
        <button type="submit" disabled={status === "loading"}>
          {status === "loading" ? "조회 중…" : "조회"}
        </button>
      </form>

      <div className="example-chips">
        {EXAMPLE_COMPANIES.map((name) => (
          <button key={name} type="button" onClick={() => { setCompany(name); runEvaluate(name); }}>
            {name}
          </button>
        ))}
      </div>

      {status === "error" && <p className="error-box">{error}</p>}

      {status === "done" && result && (
        <div className="report">
          <ProfileHeader profile={result.profile} />

          <section className="score-grid">
            {AXIS_ORDER.map((axisKey) => (
              <ScoreCard key={axisKey} axisKey={axisKey} score={result.scores[axisKey]} />
            ))}
          </section>

          <FlagList flags={result.flags} />

          <VcMatchList vcMatches={result.vc_matches} />

          <PatentList patent={result.profile.patent} />
        </div>
      )}
    </div>
  );
}
