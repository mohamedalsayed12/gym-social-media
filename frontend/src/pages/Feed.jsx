import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import LikeButton from "../LikeButton.jsx";
import { api, mediaUrl } from "../api.js";
import { formatKg, initials, previewSets, relativeTime, volumeKg, workoutTitle } from "../format.js";

const TABS = [
  { id: "following", label: "Following" },
  { id: "discover", label: "Discover" },
  { id: "prs", label: "PRs only" },
];

export default function Feed() {
  const [tab, setTab] = useState("discover");
  const [workouts, setWorkouts] = useState([]);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let active = true;
    setLoading(true);
    const scope = tab === "following" ? "following" : "discover";
    api(`/feed/?scope=${scope}&limit=50`)
      .then((rows) => {
        if (!active) return;
        const next = tab === "prs" ? rows.filter((workout) => workout.exercises.some((exercise) => exercise.sets.some((set) => set.is_pr))) : rows;
        setWorkouts(next);
      })
      .catch((err) => {
        if (active) setError(err.message);
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [tab]);

  function replaceWorkout(updated) {
    setWorkouts((current) => current.map((item) => (item.id === updated.id ? updated : item)));
  }

  return (
    <main>
      <div className="tabs" role="tablist">
        {TABS.map((item) => (
          <button key={item.id} type="button" className={tab === item.id ? "active" : ""} onClick={() => setTab(item.id)}>
            {item.label}
          </button>
        ))}
      </div>
      {error ? <p className="form-error">{error}</p> : null}
      {workouts.map((workout) => (
        <article className="card" key={workout.id}>
          <Link className="person" to={`/workouts/${workout.id}`}>
            <span className="avatar">{initials(workout.owner.username)}</span>
            <span>
              <strong>{workout.owner.username}</strong>
              <span className="muted"> · {relativeTime(workout.performed_at)}</span>
            </span>
          </Link>
          <h2 className="session-title">{workoutTitle(workout)}</h2>
          {workout.photo_url ? <img className="post-photo" src={mediaUrl(workout.photo_url)} alt="" /> : null}
          <div className="stats-row">
            <span>{formatKg(volumeKg(workout))} kg</span>
            <span>{workout.exercises.length} exercises</span>
          </div>
          {previewSets(workout).map((set) => (
            <p className="set-line" key={set.key}>
              <span>{set.label}</span>
              <span>{set.detail}</span>
            </p>
          ))}
          <LikeButton workoutId={workout.id} likes={workout.likes} likedByMe={workout.liked_by_me} onChange={replaceWorkout} />
        </article>
      ))}
      {!loading && workouts.length === 0 ? <p className="empty">No sessions on this tab yet.</p> : null}
    </main>
  );
}
