import { useEffect, useState } from "react";
import { Link, Navigate, Outlet, Route, Routes, useLocation } from "react-router-dom";
import { api, getToken } from "./api.js";
import Communities from "./pages/Communities.jsx";
import Feed from "./pages/Feed.jsx";
import Login from "./pages/Login.jsx";
import Profile from "./pages/Profile.jsx";
import Register from "./pages/Register.jsx";
import WorkoutDetail from "./pages/WorkoutDetail.jsx";
import WorkoutForm from "./pages/WorkoutForm.jsx";

function RequireAuth() {
  if (!getToken()) return <Navigate to="/login" replace />;
  return <Outlet />;
}

function Shell() {
  const { pathname } = useLocation();
  const [user, setUser] = useState(null);
  const logging = pathname === "/workouts/new" || pathname.endsWith("/edit");

  useEffect(() => {
    let active = true;
    api("/users/me")
      .then((me) => {
        if (active) setUser(me);
      })
      .catch(() => {});
    return () => {
      active = false;
    };
  }, []);

  return (
    <div className="stage">
      <div className="phone">
        {logging ? null : (
          <header className="appbar">
            <Link className="wordmark" to="/">
              Gym Social
            </Link>
          </header>
        )}
        <div className="screen">
          <Outlet context={{ user }} />
        </div>
        {logging ? null : (
          <nav className="tabbar" aria-label="Primary">
            <Link to="/" className={pathname === "/" ? "active" : ""}>
              Home
            </Link>
            <Link to="/workouts/new" className="fab" aria-label="Log workout">
              +
            </Link>
            <Link to="/profile" className={pathname === "/profile" ? "active" : ""}>
              Profile
            </Link>
          </nav>
        )}
      </div>
    </div>
  );
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route path="/register" element={<Register />} />
      <Route element={<RequireAuth />}>
        <Route element={<Shell />}>
          <Route path="/" element={<Feed />} />
          <Route path="/profile" element={<Profile />} />
          <Route path="/communities" element={<Communities />} />
          <Route path="/workouts/new" element={<WorkoutForm />} />
          <Route path="/workouts/:id" element={<WorkoutDetail />} />
          <Route path="/workouts/:id/edit" element={<WorkoutForm />} />
        </Route>
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
