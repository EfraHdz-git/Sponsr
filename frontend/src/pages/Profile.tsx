import { AnimatePresence, motion } from "framer-motion";
import { ChangeEvent, useEffect, useRef, useState } from "react";
import { api, Fact, Profile as P, Role } from "../api";
import { CompanyLogo } from "../components/bits";
import { IconCards, IconDoc, IconPin, IconShield, IconSpark, IconUser, IconX } from "../icons";
import "./profile.css";

const label = (u: string) => u.split("://").pop()!.replace(/^www\./, "").replace(/\/$/, "");
const years = (r: Role) => `${(r.start || "").slice(0, 4)} to ${r.end ? r.end.slice(0, 4) : "now"}`;
const short = (e: string) => e.replace(/\s*\(.*\)/, "").replace(/ Automotive| Ltd| Inc/g, "");
type Tab = "grid" | "skills" | "career";

export default function Profile() {
  const [p, setP] = useState<P | null>(null);
  const [role, setRole] = useState<number | null>(null);
  const [tab, setTab] = useState<Tab>("grid");
  const [fact, setFact] = useState<{ f: Fact; r: Role } | null>(null);
  const [busy, setBusy] = useState(false);
  const file = useRef<HTMLInputElement>(null);
  useEffect(() => { api.profile().then(setP).catch(() => undefined); }, []);
  if (!p) return <div className="ig"><div className="skeleton-block" style={{ height: 260 }} /></div>;

  const h = p.header;
  const initials = (h.full_name || "?").split(" ").map((w) => w[0]).slice(0, 2).join("");
  const tiles = p.roles.filter((r) => role === null || r.id === role)
    .flatMap((r) => r.facts.filter((f) => ["ACHIEVEMENT", "PROJECT"].includes(f.category)).map((f) => ({ f, r })));

  async function pick(e: ChangeEvent<HTMLInputElement>) {
    const f = e.target.files?.[0];
    if (!f) return;
    setBusy(true);
    const data = await new Promise<string>((res) => { const rd = new FileReader(); rd.onload = () => res(String(rd.result)); rd.readAsDataURL(f); });
    try { const r = await api.uploadPhoto(data); setP({ ...p!, header: { ...p!.header, photo: r.photo } }); }
    catch (err) { alert(err instanceof Error ? err.message : "Upload failed"); }
    finally { setBusy(false); e.target.value = ""; }
  }

  return (
    <div className="ig">
      <section className="ig-head">
        <button className="ig-avatar" onClick={() => file.current?.click()} title="Change photo">
          <span className="ring-grad">{h.photo ? <img src={h.photo} alt={h.full_name} /> : <span className="ig-initials">{initials}</span>}</span>
          <span className="ig-cam">{busy ? <span className="spinner" /> : "+"}</span>
        </button>
        <input ref={file} type="file" accept="image/png,image/jpeg,image/webp" hidden onChange={pick} />
        <div className="ig-meta">
          <div className="ig-name"><h1>{h.full_name}</h1><span className="verified" title="Every fact verified"><IconShield className="icon" /></span></div>
          <div className="ig-stats">
            <div><b>{p.cvs}</b><span>CVs</span></div><div><b>{p.facts}</b><span>facts</span></div>
            <div><b>{p.roles.length}</b><span>roles</span></div><div><b>{p.skills.length}</b><span>skills</span></div>
          </div>
          <p className="ig-bio"><b>{(h.headline || "").split(/[,|]/)[0]}</b><br />{(h.headline || "").split(/[,|]/).slice(1).join(", ").trim()}</p>
          <div className="ig-links">
            {h.location && <span><IconPin className="icon" />{h.location}</span>}
            {(h.links || []).map((u) => <a key={u} href={u} target="_blank" rel="noopener noreferrer">{label(u)}</a>)}
          </div>
        </div>
      </section>
      <div className="ig-actions">
        <button className="btn" onClick={() => file.current?.click()}><IconUser className="icon" />{h.photo ? "Change photo" : "Add a photo"}</button>
        <span className="ig-trust"><IconShield className="icon" />Your CVs only use what is on this page</span>
      </div>

      <div className="ig-highlights">
        <button className={`hl ${role === null ? "on" : ""}`} onClick={() => setRole(null)}>
          <span className="hl-ring" style={{ "--c": "#2f5bd3" } as never}><span className="hl-all"><IconSpark className="icon" /></span></span><span>All</span></button>
        {p.roles.map((r) => (
          <button key={r.id} className={`hl ${role === r.id ? "on" : ""}`} onClick={() => setRole(role === r.id ? null : r.id)}>
            <span className="hl-ring" style={{ "--c": r.color } as never}><CompanyLogo name={r.employer} logo={r.logo} color={r.color} size={56} radius={28} /></span>
            <span>{short(r.employer)}</span></button>))}
      </div>

      <nav className="ig-tabs">
        {([["grid", "Highlights", <IconCards className="icon" key="g" />], ["skills", "Skills", <IconSpark className="icon" key="s" />],
          ["career", "Career", <IconDoc className="icon" key="c" />]] as [Tab, string, JSX.Element][]).map(([t, l, ic]) => (
          <button key={t} className={tab === t ? "on" : ""} onClick={() => setTab(t)}>{ic}<span>{l}</span></button>))}
      </nav>

      {tab === "grid" && (
        <div className="ig-grid">{tiles.map(({ f, r }, i) => (
          <motion.button key={f.id} className="tile" onClick={() => setFact({ f, r })} whileHover={{ scale: 1.02 }}
            style={{ "--c": r.color, "--i": i % 5 } as never}>
            <span className="tile-text">{f.text}</span><span className="tile-tag">{short(r.employer)}</span>
          </motion.button>))}</div>
      )}
      {tab === "skills" && <div className="ig-skills">{p.skills.map((s) => <span key={s}>{s}</span>)}</div>}
      {tab === "career" && (
        <div className="ig-career">{p.roles.map((r) => (
          <div key={r.id} className="car-row" style={{ "--c": r.color } as never}>
            <CompanyLogo name={r.employer} logo={r.logo} color={r.color} size={48} />
            <div><b>{r.title}</b><span>{r.employer} · {years(r)}</span></div><em>{r.facts.length} facts</em>
          </div>))}</div>
      )}

      <AnimatePresence>{fact && (
        <motion.div className="ov ov-sheet" onClick={() => setFact(null)} initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
          <motion.div className="fact-card" onClick={(e) => e.stopPropagation()} style={{ "--c": fact.r.color } as never}
            initial={{ scale: .94, y: 20 }} animate={{ scale: 1, y: 0 }} exit={{ scale: .94, opacity: 0 }}>
            <button className="jd-close" onClick={() => setFact(null)} aria-label="Close"><IconX className="icon" /></button>
            <div className="fc-head"><CompanyLogo name={fact.r.employer} logo={fact.r.logo} color={fact.r.color} size={44} />
              <div><b>{fact.r.title}</b><span>{fact.r.employer} · {years(fact.r)}</span></div></div>
            <p>{fact.f.text}</p>
            {fact.f.skills.length > 0 && <div className="fc-skills">{fact.f.skills.map((s) => <span key={s}>{s}</span>)}</div>}
            <div className="fc-foot"><IconShield className="icon" />Verified against your own CV, word for word</div>
          </motion.div>
        </motion.div>)}</AnimatePresence>
    </div>
  );
}
