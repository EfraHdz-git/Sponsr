import { useId } from "react";
// Sponsr logo + the hero illustration (vector, crisp at any size, brand colours exact).

/** The Sponsr mark: a flight path that reads as an S, from origin to the destination dot. */
export function Logo({ size = 34 }: { size?: number }) {
  const id = `sl${useId().replace(/:/g, "")}`;
  return (
    <svg width={size} height={size} viewBox="0 0 64 64" aria-hidden="true">
      <defs><linearGradient id={id} x1="0" y1="1" x2="1" y2="0"><stop offset="0" stopColor="#2F5BD3" /><stop offset="1" stopColor="#7C3AED" /></linearGradient></defs>
      <rect width="64" height="64" rx="18" fill={`url(#${id})`} />
      <path d="M43.5 19.5c-2.2-3.3-6-5.5-11.5-5.5-6.6 0-11 3.6-11 9 0 11.5 22 6.5 22 18 0 5.6-4.6 9-11.5 9-5.4 0-9.6-2.2-12-6"
        fill="none" stroke="#fff" strokeWidth="6.5" strokeLinecap="round" />
      <circle cx="45.5" cy="19.5" r="5" fill="#fff" /><circle cx="45.5" cy="19.5" r="2" fill="#7C3AED" />
    </svg>
  );
}

export function Wordmark({ light = false }: { light?: boolean }) {
  return (
    <span className="brand" style={light ? { color: "#fff" } : undefined}>
      <Logo /> sponsr
    </span>
  );
}

/** Globe with a flight path from the Americas to Europe, and verified job cards floating above it. */
export function HeroArt() {
  const meridians = [-60, -30, 0, 30, 60];
  return (
    <svg viewBox="0 0 560 560" className="hero-art" role="img" aria-label="Job cards floating above a globe, with a flight path to Europe">
      <defs>
        <radialGradient id="globe" cx="40%" cy="35%" r="75%"><stop offset="0" stopColor="#ffffff" stopOpacity=".28" /><stop offset="1" stopColor="#ffffff" stopOpacity=".04" /></radialGradient>
        <linearGradient id="arc" x1="0" y1="1" x2="1" y2="0"><stop offset="0" stopColor="#a5b4fc" stopOpacity=".2" /><stop offset="1" stopColor="#ffffff" /></linearGradient>
        <filter id="soft" x="-30%" y="-30%" width="160%" height="160%"><feDropShadow dx="0" dy="18" stdDeviation="18" floodColor="#0b1a4d" floodOpacity=".35" /></filter>
      </defs>
      <g transform="translate(280 300)">
        <clipPath id="globe-clip"><circle r="189" /></clipPath>
        <circle r="190" fill="url(#globe)" stroke="#ffffff" strokeOpacity=".35" />
        {/* Stylised continents, Atlantic view: the Americas on the left (origin: Mexico), Europe and Africa on the right (destination: UK). */}
        <g clipPath="url(#globe-clip)" fill="#fff" fillOpacity=".3" stroke="#fff" strokeOpacity=".45" strokeWidth="1.2" strokeLinejoin="round">
          <path d="M-188-98C-160-140-104-152-66-134c22 10 18 30 2 44-14 12-16 32-30 46-10 10-8 30-18 44-8 12-14 30-6 46l-6 6c-14-4-24-18-30-34-12-28-24-56-38-78-12-18-26-30-30-44z" />
          <path d="M-58-172c18-8 40-4 46 10 4 12-10 22-26 22-16 0-28-8-30-18 0-6 4-10 10-14z" />
          <path d="M-96 94c26-8 52 6 58 28 6 24-14 44-28 62l-10 14c-14-20-24-48-28-70-2-14 0-26 8-34z" />
          <path d="M104-80c3-6 10-8 15-4s4 12-1 16-12 6-15 1c-2-4-1-9 1-13z" />
          <path d="M128-104c20-16 50-18 70-6 6 4 6 12 0 18-10 8-24 10-32 20-8 8-20 12-32 10-12-2-16-12-12-22 2-8 2-14 6-20z" />
          <path d="M96-24c26-8 58-2 76 18 12 22 0 48-14 72-14 26-28 52-42 60-12-20-14-48-20-70-10-18-14-40-8-58 2-10 4-18 8-22z" />
        </g>
        {meridians.map((a) => <ellipse key={a} rx={Math.abs(Math.cos((a * Math.PI) / 180)) * 190} ry="190" fill="none" stroke="#fff" strokeOpacity=".12" />)}
        {[-120, -60, 0, 60, 120].map((y) => <ellipse key={y} cy={y} rx={Math.sqrt(190 * 190 - y * y)} ry={Math.sqrt(190 * 190 - y * y) * .22} fill="none" stroke="#fff" strokeOpacity=".1" />)}
        <path id="flight" d="M -120 70 C -90 -120, 60 -170, 112 -72" fill="none" stroke="url(#arc)" strokeWidth="3" strokeDasharray="6 9" className="flight" />
        <circle cx="-120" cy="70" r="7" fill="#c7d2fe" /><circle cx="-120" cy="70" r="16" fill="#c7d2fe" opacity=".25" />
        <circle cx="112" cy="-72" r="7" fill="#fff" /><circle cx="112" cy="-72" r="18" fill="#fff" opacity=".22" className="pulse" />
        {/* The plane flies the route on a loop (hidden when the viewer prefers reduced motion). */}
        <g className="plane">
          <path d="M12 0 3.4-2 0-11h-3.4l1.4 9.4-7.8.6-2.4-4.2h-2.4l1 5.2-1 5.2h2.4l2.4-4.2 7.8.6-1.4 9.4H0L3.4 2Z" fill="#fff"
            stroke="#c7d2fe" strokeWidth=".8" transform="scale(1.5)" />
          <animateMotion dur="7s" repeatCount="indefinite" rotate="auto" keyPoints="0;1;1" keyTimes="0;.85;1" calcMode="linear">
            <mpath href="#flight" />
          </animateMotion>
        </g>
      </g>
      <g filter="url(#soft)">
        <g className="float-a" transform="translate(4 74) rotate(-8) scale(.8)">
          <rect width="190" height="118" rx="18" fill="#fff" opacity=".9" />
          <rect x="18" y="20" width="34" height="34" rx="10" fill="#e0e7ff" />
          <rect x="62" y="24" width="96" height="10" rx="5" fill="#cbd5e1" /><rect x="62" y="42" width="64" height="8" rx="4" fill="#e2e8f0" />
          <rect x="18" y="74" width="92" height="24" rx="12" fill="#e7f7ec" /><circle cx="34" cy="86" r="6" fill="#15803d" />
          <rect x="46" y="82" width="52" height="8" rx="4" fill="#86c79b" />
        </g>
        <g className="float-b" transform="translate(392 38) rotate(7) scale(.78)">
          <rect width="200" height="128" rx="18" fill="#fff" />
          <rect x="18" y="20" width="36" height="36" rx="10" fill="#2f5bd3" opacity=".9" />
          <rect x="66" y="24" width="104" height="11" rx="5" fill="#94a3b8" /><rect x="66" y="43" width="70" height="8" rx="4" fill="#cbd5e1" />
          <rect x="18" y="80" width="78" height="26" rx="13" fill="#eaf0ff" /><rect x="104" y="80" width="78" height="26" rx="13" fill="#e7f7ec" />
          <path d="M126 93l6 6 12-13" fill="none" stroke="#15803d" strokeWidth="4" strokeLinecap="round" strokeLinejoin="round" />
        </g>
        <g className="float-c" transform="translate(338 452) rotate(-3) scale(.76)">
          <rect width="230" height="132" rx="20" fill="#fff" />
          <circle cx="44" cy="44" r="22" fill="#eef2ff" stroke="#6366f1" strokeWidth="5" strokeDasharray="104 140" transform="rotate(-90 44 44)" />
          <rect x="80" y="30" width="120" height="11" rx="5" fill="#94a3b8" /><rect x="80" y="50" width="84" height="8" rx="4" fill="#cbd5e1" />
          <rect x="22" y="86" width="186" height="9" rx="4.5" fill="#e2e8f0" /><rect x="22" y="104" width="140" height="9" rx="4.5" fill="#e2e8f0" />
        </g>
      </g>
    </svg>
  );
}
