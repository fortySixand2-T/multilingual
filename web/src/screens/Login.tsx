import { useState } from "react";
import { useAuth } from "../auth";

// A ?invite=<token> link (e.g. /signup?invite=abc123) prefills the code and opens
// signup, so a shared invite link is one click to the right form.
const inviteFromUrl = new URLSearchParams(window.location.search).get("invite") ?? "";

export default function Login() {
  const { login, signup } = useAuth();
  const [mode, setMode] = useState<"login" | "signup">(inviteFromUrl ? "signup" : "login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [inviteCode, setInviteCode] = useState(inviteFromUrl);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setBusy(true);
    try {
      if (mode === "login") await login(email, password);
      else await signup({ email, password, display_name: displayName, invite_code: inviteCode });
    } catch (err: any) {
      setError(err.message ?? "Something went wrong");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="auth-wrap">
      <form className="card auth-card" onSubmit={submit}>
        <h1>🍁 TEF Prep</h1>
        <p className="muted center" style={{ marginTop: -8 }}>
          {mode === "login" ? "Welcome back." : "Join your study group."}
        </p>

        {mode === "signup" && (
          <div className="field">
            <label>Display name</label>
            <input className="text-input" value={displayName} onChange={(e) => setDisplayName(e.target.value)} required maxLength={80} />
          </div>
        )}
        <div className="field">
          <label>Email</label>
          <input className="text-input" type="email" value={email} onChange={(e) => setEmail(e.target.value)} required />
        </div>
        <div className="field">
          <label>Password</label>
          <input className="text-input" type="password" value={password} onChange={(e) => setPassword(e.target.value)} required minLength={mode === "signup" ? 8 : undefined} />
        </div>
        {mode === "signup" && (
          <div className="field">
            <label>Invite code</label>
            <input className="text-input" value={inviteCode} onChange={(e) => setInviteCode(e.target.value)} required />
          </div>
        )}

        {error && <div className="error">{error}</div>}
        <button className="btn wide" disabled={busy}>
          {busy ? "…" : mode === "login" ? "Log in" : "Create account"}
        </button>

        <div className="switch">
          {mode === "login" ? "New here? " : "Already have an account? "}
          <button type="button" onClick={() => { setMode(mode === "login" ? "signup" : "login"); setError(""); }}>
            {mode === "login" ? "Sign up" : "Log in"}
          </button>
        </div>
      </form>
    </div>
  );
}
