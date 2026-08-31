function TagRow({ label, values }) {
  if (!values || (Array.isArray(values) ? values.length === 0 : !values)) return null;
  const text = Array.isArray(values) ? values.join(", ") : values;
  return (
    <div className="vc-tags__row">
      <dt>{label}</dt>
      <dd>{text}</dd>
    </div>
  );
}

export default function VcMatchList({ vcMatches }) {
  if (!vcMatches) return null;
  const { note, inferred_tags: tags, matches } = vcMatches;

  return (
    <section className="vc-section">
      <h3>참고: 관심 가질 만한 투자자·후속 지원사업 힌트 (부가 데모)</h3>
      <p className="vc-section__note">
        MVP 주력 기능이 아닌 부가 데모입니다. {note}
      </p>

      <dl className="vc-tags">
        <TagRow label="추정 단계" values={tags.stage} />
        <TagRow label="업종 태그" values={tags.industry} />
        <TagRow label="테마 태그" values={tags.theme} />
      </dl>

      {matches.length === 0 ? (
        <p className="metric-empty">태그가 일치하는 VC가 없습니다.</p>
      ) : (
        <ul className="vc-list">
          {matches.map((m) => (
            <li key={m.vc_name} className="vc-item">
              <div className="vc-item__head">
                <span className="vc-item__name">{m.vc_name}</span>
                <span className="vc-item__score">매칭 {m.match_score}점</span>
              </div>
              <ul className="vc-item__reasons">
                {m.reasons.map((r) => (
                  <li key={r}>{r}</li>
                ))}
              </ul>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
