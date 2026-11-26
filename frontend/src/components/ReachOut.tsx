import { useEffect, useState } from "react";
import { api, Contacts, Outreach } from "../api";
import { IconCheck, IconExternal } from "../icons";

/** Who to contact about a job: LinkedIn searches (open in the user's own, signed-in browser) and an on-demand,
 *  fact-checked outreach draft to copy into LinkedIn. Nothing is sent from Sponsr. */
export default function ReachOut({ jobId }: { jobId: number }) {
  const [c, setC] = useState<Contacts | null>(null);
  const [recipient, setRecipient] = useState<"RECRUITER" | "ENGINEERING_LEADER">("RECRUITER");
  const [name, setName] = useState("");
  const [draft, setDraft] = useState<Outreach | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [copied, setCopied] = useState("");

  useEffect(() => { api.contacts(jobId).then(setC).catch(() => setC(null)); }, [jobId]);
  if (!c) return null;

  const write = async () => {
    setBusy(true); setError("");
    try { setDraft(await api.outreach(jobId, recipient, name.trim() || null)); }
    catch (e) { setError(e instanceof Error ? e.message : "Could not write the draft"); }
    setBusy(false);
  };
  const copy = async (label: string, text: string) => { await navigator.clipboard.writeText(text); setCopied(label); };

  return (
    <section className="reach">
      <h3>Who to contact</h3>
      {c.contacts.map((p) => (
        <div key={p.email} className="reach-person"><b>{p.name || "Recruiting team"}</b>
          <a href={`mailto:${p.email}`}>{p.email}</a><small>"{p.context}"</small></div>
      ))}
      <div className="reach-links">
        {c.linkedin_searches.map((l) => (
          <a key={l.url} className="btn" href={l.url} target="_blank" rel="noopener noreferrer"><IconExternal className="icon" />{l.label}</a>
        ))}
      </div>
      <p className="reach-note">{c.how_it_works}</p>
      <div className="reach-form">
        <select value={recipient} onChange={(e) => setRecipient(e.target.value as typeof recipient)}>
          <option value="RECRUITER">To a recruiter</option><option value="ENGINEERING_LEADER">To an engineering leader</option>
        </select>
        <input value={name} onChange={(e) => setName(e.target.value)} placeholder="Their name (optional)" maxLength={80} />
        <button className="btn primary" onClick={write} disabled={busy}>{busy ? "Writing..." : draft ? "Write again" : "Draft a message"}</button>
      </div>
      {error && <p className="error small">{error}</p>}
      {draft && (
        <div className="reach-drafts">
          {[["InMail", draft.inmail, draft.inmail_chars, 1900], ["Connection note", draft.connection_note, draft.connection_note_chars, 300]].map(
            ([label, text, chars, max]) => (
              <div key={label as string} className="reach-draft">
                <div className="reach-draft-head"><b>{label as string}{label === "InMail" ? `: ${draft.subject}` : ""}</b>
                  <span>{chars as number}/{max as number}</span>
                  <button className="btn" onClick={() => copy(label as string, text as string)}>
                    {copied === label ? <><IconCheck className="icon" />Copied</> : "Copy"}</button></div>
                <p>{text as string}</p>
              </div>))}
          <p className="reach-note">{draft.notes.length ? `Fact check: ${draft.notes.join(" · ")}` : "Fact check passed: every claim traces to your verified facts."}
            {` Cost $${draft.usage.cost_usd.toFixed(3)}${draft.usage.cached_pct ? `, ${draft.usage.cached_pct}% from cache` : ""}.`}</p>
        </div>
      )}
    </section>
  );
}
