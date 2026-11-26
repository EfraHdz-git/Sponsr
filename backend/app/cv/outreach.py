"""On-demand LinkedIn outreach draft (InMail + connection note) to a recruiter or engineering leader about one job.

Same pattern as the CV: Claude Sonnet on Bedrock, the candidate's verified facts cached ahead of the job, and a
code check afterwards: a sentence about the candidate must cite facts, and no sentence may state a number that
neither its cited facts nor the posting contain. Nothing is ever sent; the user copies it into LinkedIn.
"""
from __future__ import annotations

from anthropic import AnthropicBedrock

from app.config import get_settings
from app.cv.generate import _NUM, _facts_block, usage_report

TOOL = {
    "name": "outreach",
    "description": "The outreach draft.",
    "input_schema": {
        "type": "object", "required": ["subject", "inmail", "connection_note"],
        "properties": {
            "subject": {"type": "string", "description": "InMail subject, under 60 characters."},
            "inmail": {"type": "array", "description": "One sentence per item.", "items": {
                "type": "object", "required": ["text", "fact_ids"], "properties": {
                    "text": {"type": "string"}, "fact_ids": {"type": "array", "items": {"type": "integer"}}}}},
            "connection_note": {"type": "string", "description": "Under 280 characters."},
        },
    },
}

SYSTEM = """You write a short LinkedIn message from the candidate to one person at the employer about one job.
- Use ONLY the verified facts for anything about the candidate. Every sentence that describes the candidate's
  experience cites its fact ids; sentences with no claim (context, the ask) have empty fact_ids and state no
  numbers, technologies or achievements.
Voice: follow the candidate's own way of writing to a recruiter. Below is an example in the candidate's own style (names here are placeholders; in production it is the candidate's real message). Keep
its structure, politeness and plain words; fill in the details for this person and job and fix grammar, but do
not make it more polished, salesy or clever:
"Hi Alex, I'm Sam, a software engineer and principal architect. I was looking at the Platform Engineer
role and found it very interesting, so I was wondering if you have any extra information about it. I'm
not based in the UK, so I was curious whether Contoso is currently supporting visa sponsorship for that role,
or if you know of any other role that fits my skills and offers sponsorship. I appreciate any help you can give,
and thank you for taking the time to read my message; I apologise for contacting you without notice. Have a
great day, Sam"
- Introduce the candidate by first name and a short, natural version of their current title (from CANDIDATE).
- Use this job's title, company and country ("the UK", "the Netherlands"). Keep the sponsorship question even if
  the posting mentions sponsorship (ask whether it is currently supported for this role).
- If CANDIDATE HAS APPLIED is yes, add "I've already applied" naturally; otherwise never mention applying.
- Do not describe experience, projects or achievements beyond the short title. No em dashes, no emojis.
- If no name is given, open with "Hi,".
- InMail: that message, one sentence per item. Connection note: under 280 characters, a condensed version
  (name and title, the role, the sponsorship question, thanks, first name).
Call the outreach tool with the result."""


def _numbers(s: str) -> set[str]:
    return {n.replace(",", "") for n in _NUM.findall(s or "")}


def draft_outreach(job, profile: dict, recipient: str = "RECRUITER", name: str | None = None) -> dict:
    s = get_settings()
    d = job.data or {}
    who = "a recruiter / talent acquisition partner" if recipient == "RECRUITER" else "an engineering leader"
    h = profile.get("header") or {}
    candidate = (f"{h.get('full_name') or ''}; current titles: "
                 + "; ".join(f"{r['title']} at {r['employer']}" for r in profile.get("roles") or [] if not r.get("end")))
    message = "\n".join([
        f"CANDIDATE: {candidate}",
        f"RECIPIENT: {who}" + (f", first name {name.split()[0]}" if name else " (name not given)"),
        f"JOB: {job.title} at {job.company} ({job.location or job.country or ''})",
        f"POSTING SAYS IT SPONSORS VISAS: {'yes' if (d.get('sponsorship') or {}).get('quote') else 'unknown'}",
        "WHY THE CANDIDATE FITS: " + "; ".join(d.get("strengths") or []),
        "", "POSTING:", (job.description or "")[:8000]])
    msg = AnthropicBedrock(aws_region=s.aws_region).messages.create(
        model=s.cv_model, max_tokens=2000, tools=[TOOL], tool_choice={"type": "auto"},  # forced choice: 400 on Sonnet 5.5
        system=[{"type": "text", "text": SYSTEM},
                {"type": "text", "text": "CANDIDATE (verified, the only source):\n" + _facts_block(profile),
                 "cache_control": {"type": "ephemeral"}}],
        messages=[{"role": "user", "content": message}])
    use = next((b for b in msg.content if b.type == "tool_use"), None)
    if use is None:
        raise RuntimeError("the model did not return a draft; try again")
    out = use.input
    facts = {f["id"]: f["text"] for f in profile["facts"]}
    posting, kept, notes = job.description or "", [], []
    for line in out.get("inmail") or []:
        text = line["text"].replace(" — ", ", ").replace("—", ", ").strip()
        cited = " ".join(facts.get(i, "") for i in line.get("fact_ids") or [])
        if extra := _numbers(text) - _numbers(cited) - _numbers(posting):
            notes.append(f"removed (number not in your facts: {sorted(extra)}): {text[:80]}")
            continue
        kept.append(text)
    note = out.get("connection_note", "").replace(" — ", ", ").replace("—", ", ").strip()[:300]
    if extra := _numbers(note) - _numbers(" ".join(facts.values())) - _numbers(posting):
        notes.append(f"connection note mentions numbers not in your facts {sorted(extra)}: edit before sending")
    inmail = " ".join(kept)
    return {"subject": (out.get("subject") or job.title)[:60], "inmail": inmail, "inmail_chars": len(inmail),
            "connection_note": note, "connection_note_chars": len(note), "notes": notes,
            "usage": usage_report(msg.usage)}
