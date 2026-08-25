import Badge from "./Badge";
import { AXIS_DESCRIPTIONS, SOURCE_LINKS, TIER_TONE } from "../constants";

function TechnologyMetrics({ metrics }) {
  return (
    <dl className="metric-list">
      <div>
        <dt>전체 출원/등록</dt>
        <dd>{metrics.total_count}건</dd>
      </div>
      <div>
        <dt>등록</dt>
        <dd>{metrics.registered_count}건</dd>
      </div>
      <div>
        <dt>존속 중(등록+공개)</dt>
        <dd>{metrics.active_count}건</dd>
      </div>
      <div>
        <dt>IPC 분류 수</dt>
        <dd>{metrics.ipc_class_count}종{metrics.ipc_classes?.length ? ` (${metrics.ipc_classes.join(", ")})` : ""}</dd>
      </div>
      <div>
        <dt>연구개발형 벤처인증</dt>
        <dd>{metrics.is_rnd_venture_type ? "예" : "아니오"}</dd>
      </div>
    </dl>
  );
}

function InvestmentMetrics({ metrics }) {
  return (
    <dl className="metric-list">
      <div>
        <dt>벤처투자유형 여부</dt>
        <dd>
          {metrics.has_venture_investment_type === null
            ? "정보 없음"
            : metrics.has_venture_investment_type
            ? "예"
            : "아니오"}
        </dd>
      </div>
      {metrics.venture_confirm_type && (
        <div>
          <dt>벤처확인유형</dt>
          <dd>{metrics.venture_confirm_type}</dd>
        </div>
      )}
    </dl>
  );
}

function CredibilityMetrics({ metrics }) {
  if (!metrics.has_certification) {
    return <p className="metric-empty">벤처확인 데이터가 없습니다.</p>;
  }
  return (
    <dl className="metric-list">
      <div>
        <dt>인증 유형</dt>
        <dd>{metrics.cert_type}</dd>
      </div>
      <div>
        <dt>인증 기관</dt>
        <dd>{metrics.cert_agency}</dd>
      </div>
      <div>
        <dt>유효 기간</dt>
        <dd>{metrics.valid_from} ~ {metrics.valid_until}</dd>
      </div>
      {metrics.days_until_expiry !== null && (
        <div>
          <dt>만료까지</dt>
          <dd>{metrics.days_until_expiry >= 0 ? `${metrics.days_until_expiry}일 남음` : `${-metrics.days_until_expiry}일 전 만료`}</dd>
        </div>
      )}
    </dl>
  );
}

const METRIC_RENDERERS = {
  technology: TechnologyMetrics,
  investment: InvestmentMetrics,
  credibility: CredibilityMetrics,
};

export default function ScoreCard({ axisKey, score }) {
  const MetricsView = METRIC_RENDERERS[axisKey];
  const tone = TIER_TONE[score.tier] || "neutral";
  const sourceHref = SOURCE_LINKS[score.source];

  return (
    <article className="score-card">
      <header className="score-card__header">
        <h3>{score.axis}</h3>
        <Badge tone={tone}>{score.tier}</Badge>
      </header>
      <p className="score-card__desc">{AXIS_DESCRIPTIONS[axisKey]}</p>
      <MetricsView metrics={score.metrics} />
      <footer className="score-card__source">
        출처:{" "}
        {sourceHref ? (
          <a href={sourceHref} target="_blank" rel="noreferrer">
            {score.source}
          </a>
        ) : (
          score.source
        )}
      </footer>
    </article>
  );
}
