import { useEffect, useState } from "react";
import { useNavigate, useOutletContext } from "react-router-dom";
import BodyMap from "../BodyMap.jsx";
import { api, logout as endSession } from "../api.js";
import { formatKg, initials } from "../format.js";

export default function Profile() {
  const navigate = useNavigate();
  const { user } = useOutletContext();
  const [profile, setProfile] = useState(null);
  const [error, setError] = useState("");
  const [showAccount, setShowAccount] = useState(false);

  useEffect(() => {
    let active = true;
    const zone = Intl.DateTimeFormat().resolvedOptions().timeZone || "UTC";
    api(`/users/me/profile?tz=${encodeURIComponent(zone)}`)
      .then((body) => {
        if (active) setProfile(body);
      })
      .catch((err) => {
        if (active) setError(err.message);
      });
    return () => {
      active = false;
    };
  }, []);

  async function logout() {
    await endSession();
    navigate("/login");
  }

  const maxVolume = Math.max(1, ...(profile?.week.map((item) => item.volume) || [1]));

  function ordinal(value) {
    const mod100 = value % 100;
    if (mod100 >= 11 && mod100 <= 13) return `${value}th`;
    const last = value % 10;
    if (last === 1) return `${value}st`;
    if (last === 2) return `${value}nd`;
    if (last === 3) return `${value}rd`;
    return `${value}th`;
  }

  return (
    <main className="center">
      <div className="avatar lg">{initials(user?.username || profile?.username)}</div>
      <h1 className="profile-name">{user?.username || "Lifter"}</h1>
      <p className="handle">@{user?.username || "you"}</p>
      {profile?.bodyweight_kg != null && profile?.height_cm != null ? (
        <p className="muted">
          {profile.bodyweight_kg} kg · {profile.height_cm} cm
        </p>
      ) : null}
      {error ? <p className="form-error">{error}</p> : null}
      <div className="stat-grid">
        <div>
          <strong>{profile?.workouts ?? 0}</strong>
          <span>Workouts</span>
        </div>
        <div>
          <strong>{profile?.prs_this_month ?? 0}</strong>
          <span>PRs this month</span>
        </div>
        <div>
          <strong>{profile?.following ?? 0}</strong>
          <span>Following</span>
        </div>
      </div>
      {profile?.percentile != null ? (
        <div className="rank-card">
          <strong>{ordinal(profile.percentile)} percentile</strong>
          <span>
            #{profile.rank} of {profile.ranked_lifters} lifters
          </span>
          <span>Strength per kg, adjusted for height</span>
        </div>
      ) : null}
      <button type="button" className="btn slim" onClick={() => navigate("/communities")}>
        Communities
      </button>
      <button type="button" className="btn slim" onClick={() => setShowAccount((open) => !open)}>
        Edit profile
      </button>
      {showAccount ? (
        <div className="card" style={{ textAlign: "left", marginTop: 16 }}>
          <p className="muted">{profile?.email}</p>
          <button type="button" className="btn" onClick={logout}>
            Log out
          </button>
        </div>
      ) : null}
      <section style={{ textAlign: "left", marginTop: 22 }}>
        <div className="section-head">
          <h2 className="section-label">This week</h2>
          <span className="muted">Share of hits</span>
        </div>
        <BodyMap hits={profile?.hits || []} />
        {(profile?.hits || []).length === 0 ? <p className="empty">Log a workout to light up the body.</p> : null}
      </section>
      <section style={{ textAlign: "left", marginTop: 8 }}>
        <div className="section-head">
          <h2 className="section-label">Volume</h2>
          <span className="muted">By muscle</span>
        </div>
        {(profile?.week || []).map((item) => (
          <div className="bar-row" key={item.muscle_group}>
            <span>{item.muscle_group}</span>
            <div className="bar">
              <span style={{ width: `${Math.max(8, (item.volume / maxVolume) * 100)}%` }} />
            </div>
            <span>{(item.volume / 1000).toFixed(1)}t</span>
          </div>
        ))}
        {profile && profile.week.length === 0 ? <p className="empty">No sets logged this week.</p> : null}
      </section>
      <section style={{ textAlign: "left", marginTop: 18 }}>
        <div className="section-head">
          <h2 className="section-label">Personal records</h2>
          <span className="muted">Lift ÷ bodyweight × height</span>
        </div>
        {(profile?.records || []).map((record) => (
          <div className="record" key={record.name}>
            <div className="record-main">
              <span>{record.name}</span>
              <strong>
                {formatKg(record.weight)} × {record.reps}
              </strong>
            </div>
            <small>
              #{record.rank} of {record.lifters} · {ordinal(record.percentile)} percentile
            </small>
          </div>
        ))}
        {profile && profile.records.length === 0 ? <p className="empty">Records show up after your first set.</p> : null}
      </section>
    </main>
  );
}
