import { useEffect, useState } from "react";
import { api, BoardMember } from "../api";

export default function GroupBoard() {
  const [members, setMembers] = useState<BoardMember[] | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    api.board().then((b) => setMembers(b.members)).catch((e) => setError(e.message));
  }, []);

  if (error) return <div className="card center">Couldn't load the board: {error}</div>;
  if (!members) return <div className="muted">Loading…</div>;

  return (
    <div>
      <h1>Group board</h1>
      <p className="muted" style={{ marginTop: -10 }}>Everyone pulling toward CLB 7 together.</p>
      <div className="card" style={{ padding: 0, overflow: "hidden" }}>
        {members.length === 0 && <div className="row muted">No one's earned XP yet — be first!</div>}
        {members.map((m, i) => (
          <div className="row" key={m.user_id}>
            <div className="rank">{i + 1}</div>
            <div className="avatar">{(m.display_name || "?").slice(0, 1).toUpperCase()}</div>
            <div className="grow">
              <div style={{ fontWeight: 700 }}>{m.display_name}</div>
              <div className="muted" style={{ fontSize: 13 }}>{m.level.toUpperCase()}</div>
            </div>
            <div className="stat center">🔥 {m.streak}<br /><small>streak</small></div>
            <div className="stat center" style={{ marginLeft: 18 }}>⭐ {m.xp}<br /><small>XP</small></div>
          </div>
        ))}
      </div>
    </div>
  );
}
