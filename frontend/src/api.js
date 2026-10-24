export const TOKEN_KEY = "gym-social-token";
export const REFRESH_KEY = "gym-social-refresh";

export const API_ORIGIN = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";
export const API_URL = `${API_ORIGIN}/api/v1`;

export function getToken() {
  return localStorage.getItem(TOKEN_KEY);
}

export function userIdFromToken(token = getToken()) {
  if (!token) return null;
  try {
    const segment = token.split(".")[1];
    const json = atob(segment.replace(/-/g, "+").replace(/_/g, "/"));
    const payload = JSON.parse(json);
    const id = Number(payload.sub ?? payload.user_id);
    return Number.isFinite(id) ? id : null;
  } catch {
    return null;
  }
}

export function saveSession(token) {
  localStorage.setItem(TOKEN_KEY, token.access_token);
  if (token.refresh_token) localStorage.setItem(REFRESH_KEY, token.refresh_token);
}

export function setSession(token) {
  saveSession(token);
}

export async function logout() {
  const refreshToken = localStorage.getItem(REFRESH_KEY);
  clearSession();
  if (!refreshToken) return;
  await fetch(`${API_URL}/logout`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ refresh_token: refreshToken }),
    credentials: "omit",
  }).catch(() => {});
}

export function clearSession() {
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(REFRESH_KEY);
}

function errorMessage(body) {
  if (!body) return "Something went wrong";
  if (typeof body.detail === "string") return body.detail;
  if (Array.isArray(body.detail)) {
    return body.detail.map((item) => item.msg || "Invalid value").join(" ");
  }
  return "Something went wrong";
}

async function refreshSession() {
  const refreshToken = localStorage.getItem(REFRESH_KEY);
  if (!refreshToken) return false;
  const response = await fetch(`${API_URL}/refresh`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ refresh_token: refreshToken }),
    credentials: "omit",
  });
  if (!response.ok) return false;
  const token = await response.json();
  saveSession(token);
  return true;
}

function redirectToLogin() {
  clearSession();
  if (!window.location.pathname.startsWith("/login")) {
    window.location.assign("/login");
  }
}

export async function api(path, options = {}) {
  const { method = "GET", json, form, auth = true, retried = false } = options;
  const headers = {};
  let body;
  if (json !== undefined) {
    headers["Content-Type"] = "application/json";
    body = JSON.stringify(json);
  }
  if (form) {
    headers["Content-Type"] = "application/x-www-form-urlencoded";
    body = new URLSearchParams(form);
  }
  if (auth) {
    const token = getToken();
    if (token) headers.Authorization = `Bearer ${token}`;
  }

  const response = await fetch(`${API_URL}${path}`, {
    method,
    headers,
    body,
    credentials: "omit",
  });

  if (response.status === 401 && auth) {
    if (!retried && (await refreshSession())) {
      return api(path, { ...options, retried: true });
    }
    redirectToLogin();
    const error = new Error("Please log in again");
    error.status = 401;
    throw error;
  }

  if (response.status === 204) return null;

  const text = await response.text();
  const payload = text ? JSON.parse(text) : null;
  if (!response.ok) {
    const error = new Error(errorMessage(payload));
    error.status = response.status;
    throw error;
  }
  return payload;
}

export function formatWeight(weight) {
  const value = Number(weight);
  if (!Number.isFinite(value)) return "0";
  return Number.isInteger(value) ? String(value) : String(value);
}

export function workoutTitle(workout) {
  const names = (workout.exercises || []).map((exercise) => exercise.name).filter(Boolean);
  if (names.length === 0) return "Workout";
  if (names.length === 1) return names[0];
  return `${names[0]} + ${names.length - 1} more`;
}

export function mediaUrl(path) {
  if (!path) return "";
  if (path.startsWith("http")) return path;
  return `${API_ORIGIN}${path}`;
}

export async function uploadWorkoutPhoto(workoutId, file) {
  const headers = {};
  const token = getToken();
  if (token) headers.Authorization = `Bearer ${token}`;
  const body = new FormData();
  body.append("file", file);
  const response = await fetch(`${API_URL}/workouts/${workoutId}/photo`, {
    method: "POST",
    headers,
    body,
    credentials: "omit",
  });
  const text = await response.text();
  const payload = text ? JSON.parse(text) : null;
  if (!response.ok) {
    const error = new Error(errorMessage(payload));
    error.status = response.status;
    throw error;
  }
  return payload;
}

export function localInputValue(value) {
  return toLocalInput(value);
}

export function toIso(value) {
  const date = value ? new Date(value) : new Date();
  return Number.isNaN(date.getTime()) ? new Date().toISOString() : date.toISOString();
}

export function toLocalInput(value) {
  const date = value ? new Date(value) : new Date();
  const pad = (part) => String(part).padStart(2, "0");
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}T${pad(date.getHours())}:${pad(date.getMinutes())}`;
}
