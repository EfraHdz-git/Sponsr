import { motion, PanInfo } from "framer-motion";
import { useState } from "react";
import { Card, countryName } from "../api";
import { IconAlert, IconCheck, IconExternal, IconShield, IconX } from "../icons";
import { CompanyLogo, registerName, Ring } from "./bits";
import { Dir } from "./JobCard";
import ReachOut from "./ReachOut";

/** Full job details: slides up over the deck (contained inside the phone frame, a centred sheet on desktop). */
export default function JobDetails({ card, onClose, onSwipe }: { card: Card; onClose: () => void; onSwipe: (d: Dir) => void }) {
  const [more, setMore] = useState(false);
  const close = (_: unknown, info: PanInfo) => { if (info.offset.y > 110) onClose(); };
  return (
    <motion.div className="ov ov-sheet" onClick={onClose} initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
      <motion.div className="jd" onClick={(e) => e.stopPropagation()} style={{ "--c": card.color } as never}
        initial={{ y: "100%" }} animate={{ y: 0 }} exit={{ y: "100%" }} transition={{ type: "spring", stiffness: 260, damping: 32 }}
        drag="y" dragConstraints={{ top: 0, bottom: 0 }} dragElastic={{ top: 0, bottom: 0.5 }} onDragEnd={close}>
        <div className="jd-hero">
          <span className="grabber" />
          <button className="jd-close" onClick={onClose} aria-label="Close"><IconX className="icon" /></button>
          <CompanyLogo name={card.company} logo={card.logo} color={card.color} size={76} />
          <div className="jd-head"><span>{card.company} · {card.location || countryName(card.country)}</span><h2>{card.title}</h2></div>
        </div>
        <div className="jd-body">
          <div className="jd-scores">
            <Ring value={card.fit} label="fit" size={70} />
            {card.scores.skills != null && <Ring value={card.scores.skills} label="skills" size={70} />}
            {card.scores.interview != null && <Ring value={card.scores.interview} label="interview" size={70} />}
            {card.scores.strategy != null && <Ring value={card.scores.strategy} label="career" size={70} />}
          </div>
          <section className="evidence big">
            <div className="ev-head"><IconShield className="icon" />Visa sponsorship, verified twice</div>
            <p>"{(card.sponsorship.quote || "").replace(/^[-•\s]+/, "")}"</p>
            <div className="ev-reg"><IconCheck className="icon" />{card.licence.entry || `Licensed on the ${registerName(card.country)}`}</div>
          </section>
          <section><h3>Our read</h3><p>{card.summary}</p></section>
          {card.strengths.length > 0 && <section><h3>Why you fit</h3>
            <ul className="jd-list ok">{card.strengths.map((s) => <li key={s}><IconCheck className="icon" />{s}</li>)}</ul></section>}
          {card.gaps.length > 0 && <section><h3>Worth preparing for</h3>
            <ul className="jd-list warn">{card.gaps.map((s) => <li key={s}><IconAlert className="icon" />{s}</li>)}</ul></section>}
          <ReachOut jobId={card.id} />
          <section><h3>The posting</h3>
            <div className={`jd-posting ${more ? "open" : ""}`}>{card.description}</div>
            <button className="link" onClick={() => setMore(!more)}>{more ? "Show less" : "Read the full posting"}</button></section>
        </div>
        <footer className="jd-actions">
          <a className="btn" href={card.url} target="_blank" rel="noopener noreferrer"><IconExternal className="icon" /></a>
          <button className="btn" onClick={() => onSwipe("LEFT")}><IconX className="icon" />Skip</button>
          <button className="btn primary grow" onClick={() => onSwipe("RIGHT")}><IconCheck className="icon" />Apply with tailored CV</button>
        </footer>
      </motion.div>
    </motion.div>
  );
}
