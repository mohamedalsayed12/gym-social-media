import { useEffect, useRef, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { api, localInputValue, toIso, uploadWorkoutPhoto } from "../api.js";
import { formatClock, formatKg } from "../format.js";

const MUSCLE_GROUPS = ["chest", "back", "shoulders", "arms", "legs", "core", "full_body"];

function emptySet() {
  return { reps: "", weight: "", done: false };
}

function emptyExercise() {
  return { name: "", muscle_group: "", sets: [emptySet()] };
}

function bestLine(exercise) {
  const sets = exercise.sets
    .map((set) => ({ weight: Number(set.weight), reps: Number(set.reps) }))
    .filter((set) => Number.isFinite(set.weight) && set.weight >= 0 && Number.isInteger(set.reps) && set.reps > 0);
  if (sets.length === 0) return "No sets logged yet";
  const best = sets.reduce((top, set) => (set.weight > top.weight ? set : top));
  return `Best: ${formatKg(best.weight)} kg × ${best.reps}`;
}

export default function WorkoutForm() {
  const { id } = useParams();
  const navigate = useNavigate();
  const editing = Boolean(id);
  const [name, setName] = useState("");
  const [visibility, setVisibility] = useState("public");
  const [performedAt, setPerformedAt] = useState(localInputValue());
  const [exercises, setExercises] = useState([emptyExercise()]);
  const [error, setError] = useState("");
  const [pending, setPending] = useState(false);
  const [elapsed, setElapsed] = useState(0);
  const [photo, setPhoto] = useState(null);
  const [photoUrl, setPhotoUrl] = useState("");
  const cameraRef = useRef(null);

  useEffect(() => {
    const started = Date.now();
    const timer = setInterval(() => setElapsed(Math.floor((Date.now() - started) / 1000)), 1000);
    return () => clearInterval(timer);
  }, []);

  useEffect(() => {
    if (!id) return;
    let active = true;
    api(`/workouts/${id}`).then((workout) => {
      if (!active) return;
      setName(workout.notes || "");
      setVisibility(workout.visibility);
      setPerformedAt(localInputValue(new Date(workout.performed_at)));
      setExercises(
        workout.exercises.map((exercise) => ({
          name: exercise.name,
          muscle_group: exercise.muscle_group,
          sets: exercise.sets.map((set) => ({
            reps: String(set.reps),
            weight: String(set.weight),
            done: true,
          })),
        })),
      );
    });
    return () => {
      active = false;
    };
  }, [id]);

  function updateExercise(index, patch) {
    setExercises((current) => current.map((exercise, exerciseIndex) => (exerciseIndex === index ? { ...exercise, ...patch } : exercise)));
  }

  function updateSet(exerciseIndex, setIndex, patch) {
    setExercises((current) =>
      current.map((exercise, index) => {
        if (index !== exerciseIndex) return exercise;
        return {
          ...exercise,
          sets: exercise.sets.map((set, currentIndex) => (currentIndex === setIndex ? { ...set, ...patch } : set)),
        };
      }),
    );
  }

  async function finish() {
    const cleaned = exercises
      .map((exercise) => ({
        name: exercise.name.trim(),
        muscle_group: exercise.muscle_group || "full_body",
        sets: exercise.sets
          .filter((set) => set.reps !== "" && set.weight !== "")
          .map((set) => ({ reps: Number(set.reps), weight: Number(set.weight) })),
      }))
      .filter((exercise) => exercise.name && exercise.sets.length > 0);

    if (!name.trim()) {
      setError("Name the session.");
      return;
    }
    if (cleaned.length === 0) {
      setError("Log at least one set with reps and weight.");
      return;
    }
    const invalid = cleaned.some((exercise) =>
      exercise.sets.some((set) => !Number.isInteger(set.reps) || set.reps < 1 || set.reps > 100 || Number.isNaN(set.weight) || set.weight < 0),
    );
    if (invalid) {
      setError("Reps are 1–100. Weight is 0 kg or more.");
      return;
    }

    setPending(true);
    setError("");
    const body = {
      notes: name.trim(),
      performed_at: toIso(performedAt),
      visibility,
      exercises: cleaned,
    };
    try {
      const saved = editing
        ? await api(`/workouts/${id}`, { method: "PATCH", json: body })
        : await api("/workouts/", { method: "POST", json: body });
      if (photo) await uploadWorkoutPhoto(saved.id, photo);
      navigate(`/workouts/${saved.id}`);
    } catch (err) {
      setError(err.message);
    } finally {
      setPending(false);
    }
  }

  return (
    <main>
      <div className="logger-top">
        <button type="button" className="icon-btn" onClick={() => navigate("/")} aria-label="Close">
          ×
        </button>
        <div className="elapsed">
          <span>Elapsed</span>
          <strong>{formatClock(elapsed)}</strong>
        </div>
        <button type="button" className="finish" onClick={finish} disabled={pending}>
          {pending ? "…" : "Finish"}
        </button>
      </div>
      <label>
        Workout name
        <input className="name-input" value={name} placeholder="Push Day" onChange={(event) => setName(event.target.value)} />
      </label>
      <label>
        Who can see it
        <select value={visibility} onChange={(event) => setVisibility(event.target.value)}>
          <option value="public">Public</option>
          <option value="followers">Followers</option>
          <option value="private">Private</option>
        </select>
      </label>
      {exercises.map((exercise, exerciseIndex) => (
        <section className="card" key={exerciseIndex}>
          <div className="exercise-head">
            <input
              className="name-input"
              style={{ fontSize: "1.15rem" }}
              value={exercise.name}
              placeholder="Bench press"
              onChange={(event) => updateExercise(exerciseIndex, { name: event.target.value })}
            />
          </div>
          <select
            value={exercise.muscle_group}
            onChange={(event) => updateExercise(exerciseIndex, { muscle_group: event.target.value })}
          >
            <option value="">Muscle group</option>
            {MUSCLE_GROUPS.map((group) => (
              <option key={group} value={group}>
                {group.replace("_", " ")}
              </option>
            ))}
          </select>
          <p className="muted">{bestLine(exercise)}</p>
          {exercise.sets.length > 0 ? (
            <table className="set-table">
              <thead>
                <tr>
                  <th>Set</th>
                  <th>kg</th>
                  <th>Reps</th>
                  <th>Done</th>
                </tr>
              </thead>
              <tbody>
                {exercise.sets.map((set, setIndex) => (
                  <tr key={setIndex}>
                    <td>{setIndex + 1}</td>
                    <td>
                      <input
                        inputMode="decimal"
                        value={set.weight}
                        onChange={(event) => updateSet(exerciseIndex, setIndex, { weight: event.target.value })}
                      />
                    </td>
                    <td>
                      <input
                        inputMode="numeric"
                        value={set.reps}
                        onChange={(event) => updateSet(exerciseIndex, setIndex, { reps: event.target.value })}
                      />
                    </td>
                    <td>
                      <input
                        className="check"
                        type="checkbox"
                        checked={set.done}
                        onChange={(event) => updateSet(exerciseIndex, setIndex, { done: event.target.checked })}
                      />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : (
            <p className="empty">No sets logged yet</p>
          )}
          <button
            type="button"
            className="linkish"
            onClick={() => updateExercise(exerciseIndex, { sets: [...exercise.sets, emptySet()] })}
          >
            + Add set
          </button>
        </section>
      ))}
      <button type="button" className="btn" onClick={() => setExercises((current) => [...current, emptyExercise()])}>
        + Add exercise
      </button>
      <input
        ref={cameraRef}
        type="file"
        accept="image/*"
        capture="environment"
        hidden
        onChange={(event) => {
          const file = event.target.files?.[0] || null;
          setPhoto(file);
          setPhotoUrl(file ? URL.createObjectURL(file) : "");
        }}
      />
      <button type="button" className="linkish" onClick={() => cameraRef.current?.click()}>
        + Add photo
      </button>
      {photoUrl ? <img className="post-photo" src={photoUrl} alt="Workout photo" /> : null}
      {error ? <p className="form-error">{error}</p> : null}
    </main>
  );
}
