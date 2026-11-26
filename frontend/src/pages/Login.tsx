import { FormEvent, useState } from "react";
import { api, Me } from "../api";
import { HeroArt, Wordmark } from "../brand";
import { IconCheck, IconDoc, IconLock, IconShield } from "../icons";
import LoginPipeline from "./LoginPipeline";
import "./login.css";

const POINTS = [
  { icon: <IconShield className="icon" />, text: "Only employers on the official UK and Dutch sponsor registers" },
  { icon: <IconCheck className="icon" />, text: "Every job checked for sponsorship before you see it" },
  { icon: <IconDoc className="icon" />, text: "Swipe right for a CV tailored to the role, from your verified experience" },
];

export default function Login({ onSignedIn }: { onSignedIn: (me: Me) => void }) {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function submit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError("");
    try { onSignedIn(await api.login(username, password)); }
    catch (err) { setError(err instanceof Error ? err.message : "Could not sign in"); }
    finally { setBusy(false); }
  }

  return (
    <div className="login">
      <section className="login-hero">
        <Wordmark light />
        <div className="hero-copy">
          <h1>Jobs that can<br />sponsor your move.</h1>
          <p>Swipe through engineering roles at verified visa sponsors in the UK and the Netherlands. Swipe right and your tailored CV is ready in seconds.</p>
        </div>
        <HeroArt />
        <ul className="hero-points">{POINTS.map((p) => <li key={p.text}>{p.icon}<span>{p.text}</span></li>)}</ul>
      </section>
      <section className="login-form-wrap">
        <form className="login-form" onSubmit={submit}>
          <div className="mobile-brand"><Wordmark /></div>
          <h2>Welcome back</h2>
          <p className="muted">Sign in to see today's verified matches.</p>
          <label>Username<input autoFocus autoComplete="username" value={username} onChange={(e) => setUsername(e.target.value)} required /></label>
          <label>Password<input type="password" autoComplete="current-password" value={password} onChange={(e) => setPassword(e.target.value)} required /></label>
          {error && <div className="form-error">{error}</div>}
          <button className="btn primary big" disabled={busy}>{busy ? <span className="spinner" /> : <IconLock className="icon" />} Sign in</button>
          <p className="fine">Private beta. Accounts are by invitation.</p>
        </form>
        <LoginPipeline />
      </section>
    </div>
  );
}
