import Badge from "./Badge";
import { FLAG_LEVEL_TONE, RULE_LABELS } from "../constants";

export default function FlagList({ flags }) {
  if (!flags.length) {
    return (
      <section className="flag-section">
        <h3>반증 엔진 결과</h3>
        <p className="metric-empty">트리거된 규칙이 없습니다 (확인 필요 사항 없음).</p>
      </section>
    );
  }

  return (
    <section className="flag-section">
      <h3>반증 엔진 결과</h3>
      <p className="flag-section__note">
        아래 항목은 감점이 아니라 "확인이 필요하다"는 신호입니다. 최종 판단은 검토자의 몫입니다.
      </p>
      <ul className="flag-list">
        {flags.map((flag) => (
          <li key={flag.rule} className="flag-item">
            <div className="flag-item__head">
              <Badge tone={FLAG_LEVEL_TONE[flag.level] || "neutral"}>{flag.level}</Badge>
              <span className="flag-item__rule">{RULE_LABELS[flag.rule] || flag.rule}</span>
            </div>
            <p className="flag-item__message">{flag.message}</p>
          </li>
        ))}
      </ul>
    </section>
  );
}
