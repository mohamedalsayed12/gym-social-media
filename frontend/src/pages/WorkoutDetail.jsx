import { useEffect, useState } from "react";
import { Link, useNavigate, useOutletContext, useParams } from "react-router-dom";
import LikeButton from "../LikeButton.jsx";
import { api, mediaUrl } from "../api.js";
import { formatKg, initials, relativeTime, volumeKg, workoutTitle } from "../format.js";

export default function WorkoutDetail() {
  const { id } = useParams();
  const navigate = useNavigate();
  const { user } = useOutletContext();
  const [workout, setWorkout] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    let active = true;
    api(`/workouts/${id}`)
      .then((payload) => {
        if (active) setWorkout(payload);
      })
      .catch((err) => {
        if (active) setError(err.message);
      });
    return () => {
      active = false;
    };
  }, [id]);

  async function remove() {
    if (!window.confirm("Delete this workout?")) return;
    try {
      await api(`/workouts/${id}`, { method: "DELETE" });
      navigate("/");
    } catch (err) {
      setError(err.message);
    }
  }

  if (error && !workout) return <p className="form-error">{error}</p>;
  if (!workout) return <p className="muted">Loading session…</p>;

  const mine = user && workout.owner.id === user.id;

  return (
    <article className="card">
      <div className="person">
        <span className="avatar">{initials(workout.owner.username)}</span>
        <span>
          <strong>{workout.owner.username}</strong>
          <span className="muted"> · {relativeTime(workout.performed_at)}</span>
        </span>
      </div>
      <h1 className="session-title">{workoutTitle(workout)}</h1>
      {workout.photo_url ? <img className="post-photo" src={mediaUrl(workout.photo_url)} alt="" /> : null}
      <p className="muted">{formatKg(volumeKg(workout))} kg · {workout.visibility}</p>
      {workout.exercises.map((exercise) => (
        <section key={exercise.id}>
          <h2>
            {exercise.name} <span className="muted">{exercise.muscle_group}</span>
          </h2>
          {exercise.sets.map((set) => (
            <p className="set-line" key={set.id}>
              <span>
                Set {set.set_number}
                {set.is_pr ? " · PR" : ""}
              </span>
              <span>
                {set.reps} × {formatKg(set.weight)} kg
              </span>
            </p>
          ))}
        </section>
      ))}
      <LikeButton workoutId={workout.id} likes={workout.likes} likedByMe={workout.liked_by_me} onChange={setWorkout} />
      {mine ? (
        <p>
          <Link to={`/workouts/${workout.id}/edit`}>Edit</Link>
          {" · "}
          <button type="button" className="linkish" onClick={remove}>
            Delete
          </button>
        </p>
      ) : null}
      {error ? <p className="form-error">{error}</p> : null}
    </article>
  );
}
