export type Licence = { status?: string; register?: string; entry?: string; source_url?: string };
export type Sponsorship = { status?: string; quote?: string | null };
export type Card = {
  id: number; company: string; title: string; location: string | null; country: string | null; url: string;
  logo: string | null; color: string; work: string | null;
  salary: string | null; posted_at: string | null; summary: string | null; strengths: string[]; gaps: string[];
  fit: number | null; scores: { strategy: number | null; skills: number | null; interview: number | null };
  licence: Licence; sponsorship: Sponsorship; description: string | null;
};
export type Me = { username: string; name: string; headline: string | null; location: string | null; facts: number; roles: number };
export type AppItem = {
  id: number; status: "WRITING" | "READY" | "FAILED" | "APPLIED"; job: Card; created_at: string; ready_at: string | null;
  error: string | null; notes: string[]; headline: string | null; summary: string; bullets: number;
};
export type Fact = { id: number; role_id: number | null; category: string; text: string; skills: string[]; skill_level: string | null };
export type Role = { id: number; employer: string; title: string; start: string | null; end: string | null; location: string | null;
  facts: Fact[]; logo: string | null; color: string };
export type Profile = { header: { full_name?: string; headline?: string; email?: string; location?: string; links?: string[]; photo?: string | null };
  roles: Role[]; other: Fact[]; skills: string[]; facts: number; cvs: number };

export class ApiError extends Error { constructor(public status: number, message: string) { super(message); } }

async function call<T>(path: string, init: RequestInit = {}): Promise<T> {
  const res = await fetch(`/api${path}`, { credentials: "include", headers: { "Content-Type": "application/json" }, ...init });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new ApiError(res.status, typeof body.detail === "string" ? body.detail : `Request failed (${res.status})`);
  }
  return res.json() as Promise<T>;
}

export const api = {
  me: () => call<Me>("/me"),
  login: (username: string, password: string) => call<Me>("/login", { method: "POST", body: JSON.stringify({ username, password }) }),
  logout: () => call("/logout", { method: "POST" }),
  feed: () => call<{ cards: Card[]; remaining: number }>("/feed"),
  swipe: (job_id: number, direction: "LEFT" | "RIGHT") =>
    call<{ application_id: number | null }>("/swipe", { method: "POST", body: JSON.stringify({ job_id, direction }) }),
  undo: () => call<{ job_id: number }>("/undo", { method: "POST" }),
  applications: () => call<AppItem[]>("/applications"),
  retry: (id: number) => call(`/applications/${id}/retry`, { method: "POST" }),
  applied: (id: number) => call(`/applications/${id}/applied`, { method: "POST" }),
  profile: () => call<Profile>("/profile"),
  reset: () => call<{ swipes: number; applications: number }>("/reset", { method: "POST" }),
  uploadPhoto: (data_url: string) => call<{ photo: string }>("/profile/photo", { method: "POST", body: JSON.stringify({ data_url }) }),
};

export const countryName = (c: string | null) => ({ GB: "United Kingdom", NL: "Netherlands" } as Record<string, string>)[c || ""] || c || "";
