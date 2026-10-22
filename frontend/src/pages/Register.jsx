import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { api } from "../api.js";

export default function Register() {
  const navigate = useNavigate();
  const [error, setError] = useState("");
  const [pending, setPending] = useState(false);

  async function onSubmit(event) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    setError("");
    setPending(true);
    try {
      await api("/users/", {
        method: "POST",
        auth: false,
        json: {
          email: String(form.get("email") || ""),
          username: String(form.get("username") || ""),
          password: String(form.get("password") || ""),
          bodyweight_kg: Number(form.get("bodyweight")),
          height_cm: Number(form.get("height")),
        },
      });
      navigate("/login");
    } catch (err) {
      setError(err.message);
    } finally {
      setPending(false);
    }
  }

  return (
    <div className="stage">
      <main className="phone">
        <div className="screen auth">
          <h1 className="wordmark lime">LIFTLOG</h1>
          <p className="lede">Create an account, then log the sets you want people to see.</p>
          <form onSubmit={onSubmit}>
            <label>
              Email
              <input name="email" type="email" autoComplete="email" required />
            </label>
            <label>
              Username
              <input name="username" autoComplete="username" required minLength={3} maxLength={32} />
            </label>
            <label>
              Password
              <input name="password" type="password" autoComplete="new-password" required minLength={8} />
            </label>
            <div className="split">
              <label>
                Weight (kg)
                <input name="bodyweight" type="number" inputMode="decimal" min="20" max="400" step="0.1" required />
              </label>
              <label>
                Height (cm)
                <input name="height" type="number" inputMode="decimal" min="50" max="250" step="0.1" required />
              </label>
            </div>
            {error ? <p className="form-error">{error}</p> : null}
            <button className="btn" type="submit" disabled={pending}>
              {pending ? "Creating…" : "Create account"}
            </button>
          </form>
          <p className="center muted">
            Already training? <Link to="/login">Log in</Link>
          </p>
        </div>
      </main>
    </div>
  );
}
