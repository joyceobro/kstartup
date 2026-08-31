import { useState } from "react";

// 반증 플래그에서 자동 생성된 "심층심사 질의서 시드".
// 심사역이 질의서·심사의견서에 그대로 옮겨 붙일 수 있도록 전체 복사 버튼을 제공한다.
export default function InterviewQuestionList({ questions, companyName }) {
  const [copied, setCopied] = useState(false);

  if (!questions || questions.length === 0) return null;

  const plainText = [
    `[${companyName}] 심층심사 질의서 (자동 생성 초안)`,
    "",
    ...questions.map((q, i) => `${i + 1}. (${q.title}) ${q.question}`),
  ].join("\n");

  async function handleCopy() {
    try {
      await navigator.clipboard.writeText(plainText);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      setCopied(false);
    }
  }

  return (
    <section className="iq-section">
      <div className="iq-section__head">
        <h3>심층심사 질의서 시드 (자동 생성)</h3>
        <button type="button" className="iq-section__copy" onClick={handleCopy}>
          {copied ? "복사됨" : "전체 복사"}
        </button>
      </div>
      <p className="iq-section__note">
        위 확인 필요 플래그를 심층심사에서 물어볼 질문 문항으로 변환한 것입니다. 심사의견서·질의서 초안으로 사용하세요.
        <span className="iq-section__legend"> ✎ 표시는 AI가 기업 맥락을 반영해 다듬은 문항입니다.</span>
      </p>
      <ol className="iq-list">
        {questions.map((q) => (
          <li key={q.rule} className="iq-item">
            <span className="iq-item__title">
              {q.title}
              {q.ai_refined && <span className="iq-item__refined" title="AI가 다듬은 문항"> ✎</span>}
            </span>
            <p className="iq-item__question">{q.question}</p>
          </li>
        ))}
      </ol>
    </section>
  );
}
