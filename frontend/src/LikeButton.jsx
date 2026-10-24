import { useState } from "react";
import { api } from "./api.js";

export default function LikeButton({ workoutId, likes, likedByMe, onChange }) {
  const [pending, setPending] = useState(false);

  async function toggle() {
    setPending(true);
    try {
      const updated = likedByMe
        ? await api(`/workouts/${workoutId}/like`, { method: "DELETE" })
        : await api(`/workouts/${workoutId}/like`, { method: "POST" });
      onChange?.(updated);
    } catch {
    } finally {
      setPending(false);
    }
  }

  return (
    <button type="button" className={likedByMe ? "heart liked" : "heart"} onClick={toggle} disabled={pending} aria-pressed={likedByMe}>
      <svg width="16" height="16" viewBox="0 0 24 24" aria-hidden="true">
        <path
          d="M12 20s-7-4.4-7-9a4 4 0 0 1 7-2 4 4 0 0 1 7 2c0 4.6-7 9-7 9z"
          fill={likedByMe ? "currentColor" : "none"}
          stroke="currentColor"
          strokeWidth="2"
        />
      </svg>
      {likes}
    </button>
  );
}
