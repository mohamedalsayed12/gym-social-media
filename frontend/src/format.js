export function initials(username) {
  const cleaned = (username || "?").replace(/[^A-Za-z0-9]/g, "");
  return (cleaned.slice(0, 2) || "?").toUpperCase();
}

export function workoutTitle(workout) {
  const named = workout.notes?.trim();
  if (named) return named;
  const group = workout.exercises[0]?.muscle_group || "workout";
  return `${group} day`;
}

export function volumeKg(workout) {
  return workout.exercises.reduce(
    (sum, exercise) => sum + exercise.sets.reduce((inner, set) => inner + set.reps * Number(set.weight), 0),
    0,
  );
}

export function formatKg(value) {
  const number = Number(value);
  if (!Number.isFinite(number)) return "0";
  return Math.round(number).toLocaleString("en-GB");
}

export function relativeTime(iso) {
  const minutes = Math.max(0, Math.round((Date.now() - new Date(iso).getTime()) / 60000));
  if (minutes < 60) return `${minutes} min`;
  const hours = Math.round(minutes / 60);
  if (hours < 48) return `${hours}h`;
  return `${Math.round(hours / 24)}d`;
}

export function previewSets(workout) {
  return workout.exercises
    .flatMap((exercise) =>
      exercise.sets.map((set) => ({
        key: set.id,
        label: exercise.name,
        detail: `${set.reps} × ${formatKg(set.weight)}`,
      })),
    )
    .slice(0, 3);
}

export function formatClock(totalSeconds) {
  const seconds = Math.max(0, totalSeconds);
  const hours = String(Math.floor(seconds / 3600)).padStart(2, "0");
  const minutes = String(Math.floor((seconds % 3600) / 60)).padStart(2, "0");
  const remain = String(seconds % 60).padStart(2, "0");
  return `${hours}:${minutes}:${remain}`;
}
