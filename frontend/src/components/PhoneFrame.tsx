import { useState } from "react";
import { Me } from "../api";
import { Logo } from "../brand";
import { IconCards, IconCheck, IconChevron, IconDoc, IconShield, IconUser } from "../icons";
import Applications from "../pages/Applications";
import Profile from "../pages/Profile";
import Deck from "./Deck";

type Tab = "discover" | "applications" | "profile";

/** The mobile app inside a phone, for showing the product on a laptop or projector. */
export default function PhoneFrame({ me, toast, onApplied }: { me: Me; toast: (m: string) => void; onApplied: () => void }) {
  const [tab, setTab] = useState<Tab>("discover");
  const initials = me.name.split(" ").map((w) => w[0]).slice(0, 2).join("");
  const time = new Date().toLocaleTimeString([], { hour: "numeric", minute: "2-digit" }).replace(/\s?[AP]M/i, "");
  return (
    <div className="stage">
      <ul className="callouts left">
        <li><span className="co-ic swipe-r"><IconCheck className="icon" /></span><div><b>Swipe right</b><p>A CV tailored to the role, written from your verified experience in about 20 seconds.</p></div></li>
        <li><span className="co-ic swipe-l"><IconChevron className="icon flip" /></span><div><b>Swipe left</b><p>Skip it. Nothing is sent, and you can undo.</p></div></li>
      </ul>
      <div className="phone">
        <div className="phone-screen appview">
          <div className="island" />
          <div className="statusbar"><b>{time}</b><span className="sb-icons">
            <svg viewBox="0 0 18 12"><rect x="0" y="8" width="3" height="4" rx="1" /><rect x="5" y="5.5" width="3" height="6.5" rx="1" /><rect x="10" y="3" width="3" height="9" rx="1" /><rect x="15" y="0" width="3" height="12" rx="1" /></svg>
            <svg viewBox="0 0 16 12"><path d="M8 11.5 5.6 9a3.4 3.4 0 0 1 4.8 0L8 11.5Zm-4.2-4.3L2.4 5.8a8 8 0 0 1 11.2 0l-1.4 1.4a6 6 0 0 0-8.4 0ZM.9 4.3-.5 2.9a12 12 0 0 1 17 0L15.1 4.3a10 10 0 0 0-14.2 0Z" /></svg>
            <svg viewBox="0 0 27 12"><rect x=".5" y=".5" width="22" height="11" rx="3.5" fill="none" stroke="currentColor" opacity=".4" /><rect x="2" y="2" width="17" height="8" rx="2" /><rect x="24" y="4" width="2" height="4" rx="1" opacity=".4" /></svg>
          </span></div>
          <header className="m-head"><Logo size={28} /><b>{tab === "discover" ? "Discover" : tab === "applications" ? "Applications" : "Profile"}</b><span className="avatar sm">{initials}</span></header>
          <div className="m-content">
            {tab === "discover" && <Deck toast={toast} onApplied={onApplied} onDone={() => setTab("applications")} />}
            {tab === "applications" && <div className="m-scroll"><Applications toast={toast} onChange={onApplied} /></div>}
            {tab === "profile" && <div className="m-scroll"><Profile /></div>}
          </div>
          <nav className="m-tabs">
            {([["discover", "Discover", <IconCards className="icon" key="d" />], ["applications", "Applications", <IconDoc className="icon" key="a" />],
              ["profile", "Profile", <IconUser className="icon" key="p" />]] as [Tab, string, JSX.Element][]).map(([t, l, ic]) => (
              <button key={t} className={tab === t ? "on" : ""} onClick={() => setTab(t)}>{ic}{l}</button>))}
          </nav>
          <span className="home-bar" />
        </div>
      </div>
      <ul className="callouts right">
        <li><span className="co-ic swipe-u"><IconChevron className="icon rot" /></span><div><b>Swipe up</b><p>The full picture: fit scores, the employer's own words on sponsorship, gaps to prepare for.</p></div></li>
        <li><span className="co-ic shield"><IconShield className="icon" /></span><div><b>Verified, twice</b><p>Every employer is on the official sponsor register, and every posting says it sponsors visas.</p></div></li>
      </ul>
    </div>
  );
}
