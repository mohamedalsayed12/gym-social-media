import { useEffect, useState } from "react";
import { api } from "../api.js";

function ordinal(value) {
  const mod100 = value % 100;
  if (mod100 >= 11 && mod100 <= 13) return `${value}th`;
  const last = value % 10;
  if (last === 1) return `${value}st`;
  if (last === 2) return `${value}nd`;
  if (last === 3) return `${value}rd`;
  return `${value}th`;
}

export default function Communities() {
  const [rows, setRows] = useState([]);
  const [error, setError] = useState("");
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [pending, setPending] = useState(false);

  function load() {
    return api("/communities/")
      .then(setRows)
      .catch((err) => setError(err.message));
  }

  useEffect(() => {
    let active = true;
    api("/communities/")
      .then((body) => {
        if (active) setRows(body);
      })
      .catch((err) => {
        if (active) setError(err.message);
      });
    return () => {
      active = false;
    };
  }, []);

  async function createCommunity(event) {
    event.preventDefault();
    setPending(true);
    setError("");
    try {
      await api("/communities/", { method: "POST", json: { name, description } });
      setName("");
      setDescription("");
      await load();
    } catch (err) {
      setError(err.message);
    } finally {
      setPending(false);
    }
  }

  async function toggle(community) {
    setError("");
    try {
      if (community.joined) {
        await api(`/communities/${community.slug}/join`, { method: "DELETE" });
      } else {
        await api(`/communities/${community.slug}/join`, { method: "POST" });
      }
      await load();
    } catch (err) {
      setError(err.message);
    }
  }

  return (
    <main>
      <h1 className="section-label">Communities</h1>
      <p className="muted">Join a group. Your rank there is only against its members.</p>
      <form onSubmit={createCommunity} className="card">
        <label>
          New community
          <input value={name} onChange={(event) => setName(event.target.value)} placeholder="Hyrox" required minLength={2} maxLength={40} />
        </label>
        <label>
          Description
          <input value={description} onChange={(event) => setDescription(event.target.value)} placeholder="What you train" maxLength={200} />
        </label>
        <button className="btn" type="submit" disabled={pending}>
          {pending ? "Creating…" : "Create community"}
        </button>
      </form>
      {error ? <p className="form-error">{error}</p> : null}
      {rows.map((community) => (
        <article className="card community" key={community.slug}>
          <strong>{community.name}</strong>
          <p className="muted">{community.description}</p>
          <p className="muted">{community.members} members</p>
          {community.joined && community.percentile != null ? (
            <p className="community-rank">
              {ordinal(community.percentile)} percentile · #{community.rank} of {community.ranked_lifters}
            </p>
          ) : null}
          <button type="button" className="btn slim" onClick={() => toggle(community)}>
            {community.joined ? "Leave" : "Join"}
          </button>
        </article>
      ))}
    </main>
  );
}
