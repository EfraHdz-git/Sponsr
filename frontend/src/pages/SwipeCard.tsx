import { motion, PanInfo, useMotionValue, useTransform } from "framer-motion";
import { Card, countryName } from "../api";
import { IconAlert, IconCash, IconCheck, IconPin, IconShield, IconSpark } from "../icons";

const HUES = [222, 248, 160, 12, 280, 196, 330, 32];
export const companyHue = (name: string) => HUES[[...name].reduce((a, c) => a + c.charCodeAt(0), 0) % HUES.length];

export function Monogram({ name, size = 52 }: { name: string; size?: number }) {
  const h = companyHue(name);
  return (
    <div className="mono" style={{ width: size, height: size, background: `linear-gradient(135deg, hsl(${h} 75% 55%), hsl(${(h + 30) % 360} 70% 45%))` }}>
      {name.replace(/[^A-Za-z0-9]/g, "").slice(0, 1).toUpperCase()}
    </div>
  );
}

export function FitRing({ value }: { value: number | null }) {
  const v = Math.max(0, Math.min(100, value ?? 0));
  const c = 2 * Math.PI * 22;
  return (
    <div className="fit" title="How well this role fits your verified experience and goals">
      <svg viewBox="0 0 52 52"><circle cx="26" cy="26" r="22" className="track" />
        <circle cx="26" cy="26" r="22" className="bar" strokeDasharray={`${(v / 100) * c} ${c}`} transform="rotate(-90 26 26)" /></svg>
      <div><b>{value ?? "?"}</b><span>fit</span></div>
    </div>
  );
}

export function SponsorBadges({ card }: { card: Card }) {
  const sp = card.sponsorship.status;
  const spLabel = sp === "CONFIRMED" ? "Sponsorship confirmed" : sp === "POSSIBLE" ? "Sponsorship likely" : "Sponsorship: ask the recruiter";
  return (
    <div className="badges">
      <span className="badge b-ok" title={card.licence.entry || ""}><IconShield className="icon" />Licensed sponsor</span>
      <span className={`badge ${sp === "CONFIRMED" ? "b-ok" : sp === "POSSIBLE" ? "b-brand" : "b-neutral"}`}
        title={card.sponsorship.quote || "The posting does not mention sponsorship; the employer is on the official register"}>
        {sp === "CONFIRMED" ? <IconCheck className="icon" /> : <IconSpark className="icon" />}{spLabel}
      </span>
    </div>
  );
}

type Props = { card: Card; onSwipe: (dir: "LEFT" | "RIGHT") => void; onOpen: () => void; top: boolean; depth: number };

export default function SwipeCard({ card, onSwipe, onOpen, top, depth }: Props) {
  const x = useMotionValue(0);
  const rotate = useTransform(x, [-300, 300], [-14, 14]);
  const apply = useTransform(x, [30, 140], [0, 1]);
  const skip = useTransform(x, [-140, -30], [1, 0]);

  function end(_: unknown, info: PanInfo) {
    if (info.offset.x > 120 || info.velocity.x > 700) onSwipe("RIGHT");
    else if (info.offset.x < -120 || info.velocity.x < -700) onSwipe("LEFT");
  }

  return (
    <motion.article
      className="swipe-card panel"
      style={{ x, rotate, zIndex: 10 - depth, pointerEvents: top ? "auto" : "none" }}
      drag={top ? "x" : false}
      dragSnapToOrigin
      onDragEnd={end}
      initial={{ scale: 1 - depth * 0.04, y: depth * 14, opacity: depth > 2 ? 0 : 1 }}
      animate={{ scale: 1 - depth * 0.04, y: depth * 14, opacity: depth > 2 ? 0 : 1 }}
      exit={{ x: x.get() >= 0 ? 600 : -600, opacity: 0, rotate: x.get() >= 0 ? 18 : -18, transition: { duration: 0.32 } }}
      transition={{ type: "spring", stiffness: 300, damping: 28 }}
    >
      <motion.div className="stamp apply" style={{ opacity: apply }}>APPLY</motion.div>
      <motion.div className="stamp skip" style={{ opacity: skip }}>SKIP</motion.div>
      <header className="card-head">
        <Monogram name={card.company} />
        <div className="who-co"><b>{card.company}</b><span><IconPin className="icon" />{card.location || countryName(card.country)}</span></div>
        <FitRing value={card.fit} />
      </header>
      <h2 className="card-title">{card.title}</h2>
      <div className="meta">
        <span className="badge b-neutral">{countryName(card.country)}</span>
        {card.salary ? <span className="badge b-neutral"><IconCash className="icon" />{card.salary}</span> : <span className="badge b-neutral"><IconCash className="icon" />Salary not published</span>}
      </div>
      <SponsorBadges card={card} />
      <div className="why">
        <div className="section-title">Why you fit</div>
        <ul>{card.strengths.slice(0, 3).map((s) => <li key={s}><IconCheck className="icon ok" />{s}</li>)}</ul>
        {card.gaps[0] && <div className="watch"><IconAlert className="icon" /><span><b>Watch out:</b> {card.gaps[0]}</span></div>}
      </div>
      <button className="link-more" onClick={onOpen}>See full details</button>
    </motion.article>
  );
}
