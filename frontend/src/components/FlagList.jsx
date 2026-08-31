import Badge from "./Badge";
import { FLAG_LEVEL_TONE, RULE_LABELS } from "../constants";

export default function FlagList({ flags }) {
  if (!flags.length) {
    return (
      <section className="flag-section">
        <h3>확인 필요 플래그 (반증 엔진)</h3>
        <p className="metric-empty">
          자기서술과 공개 기록 사이에서 트리거된 규칙이 없습니다. 추가로 확인이 필요한 모순은 발견되지 않았습니다.
        </p>
      </section>
    );
  }

  return (
    <section className="flag-section">
      <h3>확인 필요 플래그 (반증 엔진)</h3>
      <p className="flag-section__note">
        아래 항목은 감점이 아니라 "자기서술이 공개 기록과 맞는지 심사역이 더 확인해야 한다"는 신호입니다.
        각 플래그에는 심층심사 질의서에 그대로 붙여 쓸 수 있는 질문이 함께 생성됩니다. 최종 판단은 심사역·심사위원회의 몫입니다.
      </p>
      <ul className="flag-list">
        {flags.map((flag) => (
          <li key={flag.rule} className="flag-item">
            <div className="flag-item__head">
              <Badge tone={FLAG_LEVEL_TONE[flag.level] || "neutral"}>{flag.level}</Badge>
              <span className="flag-item__rule">{RULE_LABELS[flag.rule] || flag.rule}</span>
            </div>
            <p className="flag-item__message">{flag.message}</p>
            {flag.question && (
              <p className="flag-item__question">
                <span className="flag-item__question-label">심층심사 질문</span>
                {flag.question}
              </p>
            )}
          </li>
        ))}
      </ul>
    </section>
  );
}
