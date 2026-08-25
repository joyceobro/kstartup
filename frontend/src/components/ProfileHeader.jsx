import Badge from "./Badge";
import { DART_HOME, MATCH_CONFIDENCE_LABELS } from "../constants";

export default function ProfileHeader({ profile }) {
  const confidence = MATCH_CONFIDENCE_LABELS[profile.match_confidence] || MATCH_CONFIDENCE_LABELS.unmatched;

  return (
    <header className="profile-header">
      <div className="profile-header__title">
        <h2>{profile.input_name}</h2>
        <Badge tone={confidence.tone}>{confidence.label}</Badge>
      </div>
      <p className="profile-header__desc">{confidence.desc}</p>
      <ul className="profile-header__sources">
        <li>벤처확인: {profile.venture ? "매칭됨" : "매칭 없음"}</li>
        <li>
          DART:{" "}
          {profile.dart ? (
            <a href={DART_HOME} target="_blank" rel="noreferrer">
              매칭됨 (corp_code {profile.dart.corp_code})
            </a>
          ) : (
            "매칭 없음"
          )}
        </li>
        {profile.identifiers && (
          <li>
            사업자번호 {profile.identifiers.bizr_no || "-"} / 법인번호 {profile.identifiers.jurir_no || "-"}
          </li>
        )}
      </ul>
    </header>
  );
}
