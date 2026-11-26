import { useCallback, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api, Card, Me } from "../api";
import { CompanyLogo, countryShort } from "../components/bits";
import Deck from "../components/Deck";
import PhoneFrame from "../components/PhoneFrame";
import { IconCards, IconShield, IconUndo } from "../icons";
import "./discover.css";

// Mobile view is the default; Desktop only when this browser chose it.
const read = () => { try { return localStorage.getItem("sponsr-view") !== "desk"; } catch { return true; } };

export default function Discover({ me, toast, onApplied }: { me: Me; toast: (m: string) => void; onApplied: () => void }) {
  const [phone, setPhone] = useState(read);
  const [round, setRound] = useState(0);  // bumping it reloads the deck after a reset
  const [queue, setQueue] = useState<Card[]>([]);
  const [left, setLeft] = useState(0);
  const navigate = useNavigate();
  const onQueue = useCallback((cards: Card[], remaining: number) => { setQueue(cards); setLeft(remaining); }, []);
  const resetDemo = async () => {
    try { await api.reset(); setRound((r) => r + 1); onApplied(); toast("Demo reset: every card is back"); }
    catch (e) { toast(e instanceof Error ? e.message : "Reset failed"); }
  };
  const toggle = (v: boolean) => { setPhone(v); try { localStorage.setItem("sponsr-view", v ? "phone" : "desk"); } catch { /* private mode */ } };

  return (
    <div className="discover">
      <div className="disc-head">
        <div><h1>Discover</h1><p className="muted">Engineering roles at verified visa sponsors, matched to your experience.</p></div>
        <div className="head-tools">
        <button className="btn ghost reset" onClick={resetDemo} title="Clear your swipes and demo CVs so every card is back">
          <IconUndo className="icon" />Reset demo</button>
        <div className="seg" role="tablist" aria-label="View">
          <button className={!phone ? "on" : ""} onClick={() => toggle(false)}>Desktop</button>
          <button className={phone ? "on" : ""} onClick={() => toggle(true)}>Mobile view</button>
        </div>
        </div>
      </div>
      {phone ? <PhoneFrame key={round} me={me} toast={toast} onApplied={onApplied} /> : (
        <div className="desk">
          <Deck key={round} toast={toast} onApplied={onApplied} onQueue={onQueue} onDone={() => navigate("/applications")} />
          <aside className="side">
            <div className="side-card stat-hero">
              <IconShield className="icon" />
              <div><b>{left}</b><span>verified {left === 1 ? "match" : "matches"} waiting</span></div>
              <p>Licensed on the official register, and the posting itself says it sponsors visas.</p>
            </div>
            <div className="side-card">
              <div className="side-title">Up next</div>
              {queue.slice(1, 6).map((c) => (
                <div key={c.id} className="next">
                  <CompanyLogo name={c.company} logo={c.logo} color={c.color} size={40} />
                  <div><b>{c.title}</b><span>{c.company} · {countryShort(c.country)}</span></div>
                  <em style={{ color: c.color }}>{c.fit}</em>
                </div>))}
              {queue.length <= 1 && <p className="muted small">That's everything for now.</p>}
            </div>
            <div className="side-card keys">
              <div className="side-title"><IconCards className="icon" />Shortcuts</div>
              <p><kbd>&larr;</kbd> skip <kbd>&rarr;</kbd> apply <kbd>&uarr;</kbd> details</p>
            </div>
          </aside>
        </div>
      )}
    </div>
  );
}
