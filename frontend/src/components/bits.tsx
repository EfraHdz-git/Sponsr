import { CSSProperties } from "react";

/** Employer logo on a white tile; monogram in the brand colour when there is no logo. */
export function CompanyLogo({ name, logo, color, size = 72, radius }: { name: string; logo: string | null; color: string; size?: number; radius?: number }) {
  const style: CSSProperties = { width: size, height: size, borderRadius: radius ?? size * 0.28 };
  return logo ? (
    <div className="logo-tile" style={style}><img src={logo} alt={`${name} logo`} style={{ width: "72%", height: "72%" }} /></div>
  ) : (
    <div className="logo-tile mono" style={{ ...style, background: `linear-gradient(135deg, ${color}, color-mix(in srgb, ${color} 65%, #000))` }}>
      <span style={{ fontSize: size * 0.42 }}>{name.replace(/[^A-Za-z0-9]/g, "").slice(0, 1).toUpperCase()}</span>
    </div>
  );
}

/** Circular score (0-100). */
export function Ring({ value, label = "fit", size = 56, light = false }: { value: number | null; label?: string; size?: number; light?: boolean }) {
  const v = Math.max(0, Math.min(100, value ?? 0));
  const c = 2 * Math.PI * 22;
  return (
    <div className={`ring ${light ? "light" : ""}`} style={{ width: size, height: size }}>
      <svg viewBox="0 0 52 52"><circle cx="26" cy="26" r="22" className="track" />
        <circle cx="26" cy="26" r="22" className="bar" strokeDasharray={`${(v / 100) * c} ${c}`} transform="rotate(-90 26 26)" /></svg>
      <div><b>{value ?? "?"}</b><span>{label}</span></div>
    </div>
  );
}

export const countryShort = (c: string | null) => ({ GB: "UK", NL: "Netherlands" } as Record<string, string>)[c || ""] || c || "";
export const registerName = (c: string | null) => (c === "NL" ? "Dutch IND register" : "UK Home Office register");
