import { AnimatePresence } from "framer-motion";
import { useCallback, useEffect, useState } from "react";
import { api, Card } from "../api";
import { IconCheck, IconChevron, IconUndo, IconX } from "../icons";
import JobCard, { Dir } from "./JobCard";
import JobDetails from "./JobDetails";

type Props = { toast: (m: string) => void; onApplied: () => void; onQueue?: (cards: Card[], remaining: number) => void; onDone?: () => void };

/** The swipe deck: used on the page (desktop and real phones) and inside the phone frame. */
export default function Deck({ toast, onApplied, onQueue, onDone }: Props) {
  const [cards, setCards] = useState<Card[] | null>(null);
  const [open, setOpen] = useState<Card | null>(null);
  const [lastDir, setLastDir] = useState<Dir>("RIGHT");

  const load = useCallback(async () => {
    const f = await api.feed();
    setCards(f.cards);
    onQueue?.(f.cards, f.remaining);
  }, [onQueue]);
  useEffect(() => { load().catch(() => setCards([])); }, [load]);

  const swipe = useCallback(async (dir: Dir) => {
    if (!cards?.length) return;
    const [top, ...rest] = cards;
    setLastDir(dir);
    setCards(rest);
    onQueue?.(rest, rest.length);
    setOpen(null);
    try {
      await api.swipe(top.id, dir);
      if (dir === "RIGHT") { toast(`Writing your CV for ${top.company}`); onApplied(); }
    } catch (e) { toast(e instanceof Error ? e.message : "Something went wrong"); }
  }, [cards, onApplied, onQueue, toast]);

  const undo = async () => {
    try { await api.undo(); await load(); onApplied(); } catch { toast("Nothing to undo"); }
  };

  useEffect(() => {
    const key = (e: KeyboardEvent) => {
      if ((e.target as HTMLElement)?.tagName === "INPUT") return;
      if (open) { if (e.key === "Escape" || e.key === "ArrowDown") setOpen(null); return; }
      if (e.key === "ArrowRight") swipe("RIGHT");
      if (e.key === "ArrowLeft") swipe("LEFT");
      if (e.key === "ArrowUp" && cards?.[0]) setOpen(cards[0]);
    };
    window.addEventListener("keydown", key);
    return () => window.removeEventListener("keydown", key);
  }, [swipe, open, cards]);

  return (
    <div className="deck-area">
      <div className="deck">
        {cards === null ? <div className="jc skeleton" /> : cards.length === 0 ? (
          <div className="jc done">
            <div className="done-art"><IconCheck className="icon" /></div>
            <h2>You're all caught up</h2>
            <p>New verified matches arrive as sponsors post them. Your tailored CVs are ready in Applications.</p>
            {onDone && <button className="btn primary" onClick={onDone}>See your CVs</button>}
          </div>
        ) : (
          <AnimatePresence custom={lastDir}>
            {cards.slice(0, 3).map((c, i) => <JobCard key={c.id} card={c} depth={i} onSwipe={swipe} onOpen={() => setOpen(c)} />).reverse()}
          </AnimatePresence>
        )}
      </div>
      {!!cards?.length && (
        <div className="deck-actions">
          <button className="act skip" onClick={() => swipe("LEFT")} aria-label="Skip"><IconX /></button>
          <button className="act mini" onClick={undo} aria-label="Undo"><IconUndo /></button>
          <button className="act mini up" onClick={() => setOpen(cards[0])} aria-label="Details"><IconChevron /></button>
          <button className="act apply" onClick={() => swipe("RIGHT")} aria-label="Apply"><IconCheck /></button>
        </div>
      )}
      <AnimatePresence>{open && <JobDetails card={open} onClose={() => setOpen(null)} onSwipe={swipe} />}</AnimatePresence>
    </div>
  );
}
