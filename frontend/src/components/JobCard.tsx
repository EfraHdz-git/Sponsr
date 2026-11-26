import { motion, PanInfo, useMotionValue, useTransform } from "framer-motion";
import { Card } from "../api";
import { IconCash, IconCheck, IconPin, IconShield } from "../icons";
import { CompanyLogo, countryShort, registerName, Ring } from "./bits";

export type Dir = "LEFT" | "RIGHT";
type Props = { card: Card; depth: number; onSwipe: (d: Dir) => void; onOpen: () => void };

export const exitVariants = {
  exit: (dir: Dir) => ({ x: dir === "RIGHT" ? 560 : -560, rotate: dir === "RIGHT" ? 16 : -16, opacity: 0, transition: { duration: 0.3 } }),
};

export default function JobCard({ card, depth, onSwipe, onOpen }: Props) {
  const top = depth === 0;
  const x = useMotionValue(0);
  const y = useMotionValue(0);
  const rotate = useTransform(x, [-300, 300], [-12, 12]);
  const apply = useTransform(x, [30, 130], [0, 1]);
  const skip = useTransform(x, [-130, -30], [1, 0]);
  const up = useTransform(y, [-120, -30], [1, 0]);

  function end(_: unknown, info: PanInfo) {
    const { x: dx, y: dy } = info.offset;
    if (dy < -90 && Math.abs(dx) < 90) return onOpen();
    if (dx > 110 || info.velocity.x > 700) onSwipe("RIGHT");
    else if (dx < -110 || info.velocity.x < -700) onSwipe("LEFT");
  }

  return (
    <motion.article
      className="jc" variants={exitVariants} exit="exit"
      style={{ x, y, rotate, zIndex: 10 - depth, pointerEvents: top ? "auto" : "none", "--c": card.color } as never}
      drag={top} dragSnapToOrigin dragElastic={0.6} onDragEnd={end}
      initial={{ scale: 0.92, y: 30, opacity: 0 }}
      animate={{ scale: 1 - depth * 0.045, y: depth * 16, opacity: depth > 2 ? 0 : 1 }}
      transition={{ type: "spring", stiffness: 320, damping: 30 }}
      whileTap={top ? { scale: 0.985 } : undefined}
    >
      <motion.div className="stamp apply" style={{ opacity: apply }}>APPLY</motion.div>
      <motion.div className="stamp skip" style={{ opacity: skip }}>SKIP</motion.div>
      <motion.div className="stamp up" style={{ opacity: up }}>DETAILS</motion.div>
      <div className="jc-hero">
        <div className="jc-hero-top">
          <span className="glass"><IconPin className="icon" />{card.location?.split(/[,;(]/)[0] || countryShort(card.country)} · {countryShort(card.country)}</span>
          <Ring value={card.fit} light />
        </div>
        <div className="jc-company"><b>{card.company}</b></div>
        <div className="jc-logo"><CompanyLogo name={card.company} logo={card.logo} color={card.color} size={84} /></div>
      </div>
      <div className="jc-body">
        <h2 className="jc-title">{card.title}</h2>
        <div className="jc-chips">
          <span className="chip-soft"><IconCash className="icon" />{card.salary || "Salary not published"}</span>
          <span className="chip-soft">Full time · Permanent</span>
        </div>
        <div className="evidence">
          <div className="ev-head"><IconShield className="icon" />Sponsors visas<span className="ev-tag">in the posting</span></div>
          <p>"{(card.sponsorship.quote || "").replace(/^[-•\s]+/, "")}"</p>
          <div className="ev-reg"><IconCheck className="icon" />Licensed on the {registerName(card.country)}</div>
        </div>
        <ul className="jc-why">{card.strengths.slice(0, 2).map((s) => <li key={s}><span className="dot-ok" />{s}</li>)}</ul>
        <button className="jc-handle" onClick={onOpen}><span className="bar" />Swipe up for details</button>
      </div>
    </motion.article>
  );
}
