import Badge from "./Badge";

// LLM이 생성한 자연어 종합 근거 서술 (기본: Google Gemini, 무료 티어).
// 점수·등급은 결정론 집계(ScoreCard)가 담당하고, 여기는 그 팩트를 심사역용 문장으로 옮긴 것.
export default function NarrativeSummary({ narrative }) {
  if (!narrative || !narrative.summary) return null;

  return (
    <section className="narrative-section">
      <div className="narrative-section__head">
        <h3>종합 근거 서술</h3>
        <Badge tone="info">AI 생성</Badge>
      </div>
      <p className="narrative-section__note">
        아래 문단은 위 3축 팩트시트와 확인 필요 플래그를 {narrative.model || "생성형 AI"}가 심사의견서용
        문장으로 옮긴 것입니다. 점수·등급은 결정론적 집계 결과이며 AI가 판정하지 않습니다.
      </p>
      <p className="narrative-section__body">{narrative.summary}</p>
    </section>
  );
}
