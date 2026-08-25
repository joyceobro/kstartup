function formatDate(yyyymmdd) {
  if (!yyyymmdd || yyyymmdd.length !== 8) return yyyymmdd || "-";
  return `${yyyymmdd.slice(0, 4)}-${yyyymmdd.slice(4, 6)}-${yyyymmdd.slice(6, 8)}`;
}

export default function PatentList({ patent }) {
  const items = patent?.items || [];
  if (!items.length) return null;

  return (
    <details className="patent-list">
      <summary>특허·실용신안 목록 ({items.length}건)</summary>
      <table>
        <thead>
          <tr>
            <th>출원일</th>
            <th>명칭</th>
            <th>출원인</th>
            <th>상태</th>
          </tr>
        </thead>
        <tbody>
          {items.map((it) => (
            <tr key={it.applicationNumber}>
              <td>{formatDate(it.applicationDate)}</td>
              <td>{it.inventionTitle}</td>
              <td>{it.applicantName}</td>
              <td>{it.registerStatus}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </details>
  );
}
