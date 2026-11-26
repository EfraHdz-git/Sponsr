import { AnimatePresence, motion } from "framer-motion";
import { CSSProperties, useCallback, useEffect, useState } from "react";
import { api, AppItem } from "../api";
import { CompanyLogo, countryShort } from "../components/bits";
import { IconCheck, IconDoc, IconDownload, IconExternal, IconRefresh, IconShield, IconX } from "../icons";
import PdfPages from "../components/PdfPages";
import "./pages.css";

const STATUS: Record<AppItem["status"], { label: string; cls: string }> = {
  WRITING: { label: "Writing your CV", cls: "b-brand" }, READY: { label: "CV ready", cls: "b-ok" },
  FAILED: { label: "Needs a retry", cls: "b-bad" }, APPLIED: { label: "Applied", cls: "b-neutral" },
};

export default function Applications({ toast, onChange }: { toast: (m: string) => void; onChange: () => void }) {
  const [items, setItems] = useState<AppItem[] | null>(null);
  const [viewing, setViewing] = useState<AppItem | null>(null);
  const load = useCallback(() => api.applications().then(setItems).catch(() => setItems([])), []);
  useEffect(() => { load(); }, [load]);
  useEffect(() => {  // live while any CV is being written
    if (!items?.some((i) => i.status === "WRITING")) return;
    const t = setTimeout(load, 3000);
    return () => clearTimeout(t);
  }, [items, load]);

  const act = async (fn: () => Promise<unknown>, msg: string) => {
    try { await fn(); toast(msg); load(); onChange(); } catch (e) { toast(e instanceof Error ? e.message : "Failed"); }
  };

  if (items === null) return <div className="list-wrap"><div className="app-card skeleton-block" /></div>;
  return (
    <div className="list-wrap">
      <div className="page-head"><h1>Applications</h1>
        <p className="muted">Every right swipe gets a CV tailored to the role, written only from your verified experience.</p></div>
      {items.length === 0 && (
        <div className="empty panel"><div className="empty-art"><IconDoc className="icon" /></div><h2>No CVs yet</h2>
          <p className="muted">Swipe right on a role you like and your tailored CV appears here in about 20 seconds.</p></div>
      )}
      {items.map((a) => (
        <article key={a.id} className="app-card" style={{ "--c": a.job.color } as unknown as CSSProperties}>
          <header className="app-head">
            <CompanyLogo name={a.job.company} logo={a.job.logo} color={a.job.color} size={52} />
            <div className="app-who"><b>{a.job.title}</b><span>{a.job.company} · {a.job.location?.split(/[,;(]/)[0] || countryShort(a.job.country)}</span></div>
            <span className={`badge ${STATUS[a.status].cls}`}>
              {a.status === "WRITING" ? <span className="spinner" /> : a.status !== "FAILED" ? <IconCheck className="icon" /> : null}
              {STATUS[a.status].label}</span>
          </header>
          {a.status === "WRITING" && <div className="writing"><span className="pulse-bar" /><p>Matching your verified facts to what {a.job.company} is looking for.</p></div>}
          {a.status === "FAILED" && <p className="error small">{a.error}</p>}
          {(a.status === "READY" || a.status === "APPLIED") && (
            <button className="cv-preview" onClick={() => setViewing(a)}>
              <div className="cv-thumb"><i /><i /><i /><i /><i /></div>
              <div className="cv-text"><b>{a.headline}</b><p className="clamp">{a.summary}</p>
                <span className="checks"><IconShield className="icon" />{a.bullets} points, each traced to your facts</span></div>
            </button>
          )}
          <footer className="row-actions">
            {(a.status === "READY" || a.status === "APPLIED") && <button className="btn" onClick={() => setViewing(a)}><IconDoc className="icon" />Preview</button>}
            {a.status === "FAILED" && <button className="btn" onClick={() => act(() => api.retry(a.id), "Writing it again")}><IconRefresh className="icon" />Retry</button>}
            <a className="btn ghost" href={a.job.url} target="_blank" rel="noopener noreferrer"><IconExternal className="icon" />Job</a>
            <span className="grow-space" />
            {a.status === "READY" && <button className="btn primary" onClick={() => act(() => api.applied(a.id), "Marked as applied")}><IconCheck className="icon" />I applied</button>}
          </footer>
        </article>
      ))}
      <AnimatePresence>{viewing && <PdfViewer item={viewing} onClose={() => setViewing(null)} />}</AnimatePresence>
    </div>
  );
}

function PdfViewer({ item, onClose }: { item: AppItem; onClose: () => void }) {
  const src = `/api/applications/${item.id}/cv.pdf`;
  useEffect(() => {
    const key = (e: KeyboardEvent) => { if (e.key === "Escape") onClose(); };
    window.addEventListener("keydown", key);
    return () => window.removeEventListener("keydown", key);
  }, [onClose]);
  return (
    <motion.div className="ov ov-pdf" onClick={onClose} initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
      <motion.div className="pdf-box" onClick={(e) => e.stopPropagation()} initial={{ y: 30, scale: .98 }} animate={{ y: 0, scale: 1 }} exit={{ y: 30, opacity: 0 }}>
        <header className="pdf-bar">
          <CompanyLogo name={item.job.company} logo={item.job.logo} color={item.job.color} size={34} />
          <div className="pdf-who"><b>Your CV for {item.job.company}</b><span>{item.job.title}</span></div>
          <a className="btn" href={`${src}?download=true`}><IconDownload className="icon" /><span className="hide-sm">Download</span></a>
          <button className="btn ghost" onClick={onClose} aria-label="Close"><IconX className="icon" /></button>
        </header>
        <PdfPages src={src} />
      </motion.div>
    </motion.div>
  );
}
