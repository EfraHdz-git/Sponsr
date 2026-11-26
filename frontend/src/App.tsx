import { useCallback, useEffect, useState } from "react";
import { NavLink, Route, Routes } from "react-router-dom";
import { api, ApiError, Me } from "./api";
import { Wordmark } from "./brand";
import { IconCards, IconDoc, IconLogout, IconUser } from "./icons";
import Applications from "./pages/Applications";
import Discover from "./pages/Discover";
import Login from "./pages/Login";
import Profile from "./pages/Profile";

export default function App() {
  const [me, setMe] = useState<Me | null | undefined>(undefined);
  const [toastMsg, setToastMsg] = useState("");
  const [count, setCount] = useState(0);

  useEffect(() => { api.me().then(setMe).catch((e) => setMe(e instanceof ApiError && e.status === 401 ? null : null)); }, []);
  const refreshCount = useCallback(() => { api.applications().then((a) => setCount(a.length)).catch(() => undefined); }, []);
  useEffect(() => { if (me) refreshCount(); }, [me, refreshCount]);
  const toast = useCallback((m: string) => {
    setToastMsg(m);
    window.clearTimeout((toast as unknown as { t?: number }).t);
    (toast as unknown as { t?: number }).t = window.setTimeout(() => setToastMsg(""), 2800);
  }, []);

  if (me === undefined) return null;
  if (me === null) return <Login onSignedIn={setMe} />;
  const initials = me.name.split(" ").map((w) => w[0]).slice(0, 2).join("");
  const links = [
    { to: "/", label: "Discover", icon: <IconCards className="icon" /> },
    { to: "/applications", label: "Applications", icon: <IconDoc className="icon" />, count },
    { to: "/profile", label: "Profile", icon: <IconUser className="icon" /> },
  ];
  return (
    <div className="shell">
      <header className="topbar">
        <Wordmark />
        <nav className="nav">{links.map((l) => (
          <NavLink key={l.to} to={l.to} end>{l.icon}{l.label}{l.count ? <span className="count">{l.count}</span> : null}</NavLink>
        ))}</nav>
        <div className="who">
          <span className="name">{me.name}</span><div className="avatar">{initials}</div>
          <button className="btn ghost" title="Sign out" onClick={() => api.logout().then(() => setMe(null))}><IconLogout className="icon" /></button>
        </div>
      </header>
      <main className="page appview">
        <Routes>
          <Route path="/" element={<Discover me={me} toast={toast} onApplied={refreshCount} />} />
          <Route path="/applications" element={<Applications toast={toast} onChange={refreshCount} />} />
          <Route path="/profile" element={<Profile />} />
        </Routes>
      </main>
      <nav className="tabbar">{links.map((l) => <NavLink key={l.to} to={l.to} end>{l.icon}{l.label}</NavLink>)}</nav>
      {toastMsg && <div className="toast">{toastMsg}</div>}
    </div>
  );
}
