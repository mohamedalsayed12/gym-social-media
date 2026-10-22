import { useState } from "react";
import { Link, Navigate, useNavigate } from "react-router-dom";
import { api, getToken, setSession } from "../api.js";

export default function Login() {
  const navigate = useNavigate();
  const [error, setError] = useState("");
  const [pending, setPending] = useState(false);
  const [resetNote, setResetNote] = useState(false);

  if (getToken()) return <Navigate to="/" replace />;

  async function onSubmit(event) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    setError("");
    setPending(true);
    try {
      const token = await api("/login", {
        method: "POST",
        auth: false,
        form: {
          username: String(form.get("username") || ""),
          password: String(form.get("password") || ""),
        },
      });
      setSession(token);
      navigate("/");
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
          <p className="lede">Log every set. Share every PR. Train with your people.</p>
          <form onSubmit={onSubmit}>
            <label>
              Email
              <input name="username" placeholder="you@example.com" autoComplete="username" required />
            </label>
            <label>
              Password
              <input name="password" type="password" placeholder="Password" autoComplete="current-password" required />
            </label>
            {error ? <p className="form-error">{error}</p> : null}
            <button className="btn" type="submit" disabled={pending}>
              {pending ? "Logging in…" : "Log in"}
            </button>
          </form>
          <p className="center">
            <button type="button" className="linkish" onClick={() => setResetNote(true)}>
              Forgot password?
            </button>
          </p>
          {resetNote ? <p className="muted center">Password reset isn’t set up. Use the password from signup.</p> : null}
          <p className="center muted">
            New here? <Link to="/register">Create an account</Link>
          </p>
        </div>
      </main>
    </div>
  );
}
