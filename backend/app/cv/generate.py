"""Tailored CV on a right swipe: Claude Sonnet on Bedrock writes it from VERIFIED facts only; code checks it.

Every line cites fact ids; a line citing no real fact, or stating a number its facts do not contain,
is removed (reported in notes). Employer, title and dates always come from the verified roles.
"""
from __future__ import annotations

import json
import re

from anthropic import AnthropicBedrock

from app.config import get_settings

PRICE_PER_MTOK = (2.0, 10.0)  # Sonnet 5.5 input / output, USD (Anthropic list price; Bedrock is close)
CACHE_WRITE_FACTOR, CACHE_READ_FACTOR = 1.25, 0.05  # 5-minute cache entries; reads on Sonnet 5.5
MAX_BULLETS = 18
_NUM = re.compile(r"\d+(?:[.,]\d+)*")

CV_TOOL = {
    "name": "tailored_cv",
    "description": "The tailored CV, every line citing the verified facts it is based on.",
    "input_schema": {
        "type": "object", "required": ["headline", "summary", "skills", "experience"],
        "properties": {
            "headline": {"type": "string", "description": "One positioning line under the name, true to the roles."},
            "summary": {"type": "array", "items": {"$ref": "#/$defs/line"}, "description": "2 to 3 sentences."},
            "skills": {"type": "array", "items": {"type": "object", "required": ["label", "items"], "properties": {
                "label": {"type": "string"}, "items": {"type": "array", "items": {"type": "string"}}}}},
            "experience": {"type": "array", "items": {"type": "object", "required": ["role_id", "bullets"], "properties": {
                "role_id": {"type": "integer"}, "bullets": {"type": "array", "items": {"$ref": "#/$defs/line"}}}}},
        },
        "$defs": {"line": {"type": "object", "required": ["text", "fact_ids"], "properties": {
            "text": {"type": "string"}, "fact_ids": {"type": "array", "items": {"type": "integer"}}}}},
    },
}

SYSTEM = """You write a tailored, ATS-friendly CV for ONE job, using ONLY the candidate's verified facts.
Rules:
- Every summary sentence and bullet cites the fact ids it is based on (fact_ids). Never state anything,
  including numbers, technologies, employers, titles or outcomes, that its cited facts do not support.
- Lead with what this job needs most. Order bullets by relevance; every role gets at least one bullet,
  older or less relevant roles exactly one. At most 18 bullets in total.
- Rephrase for the employer's problem, not just its keywords. Plain, confident, specific; no buzzwords,
  no em dashes, no first person.
- Skills: only skills named in the facts, grouped for this job (3 to 5 groups).
- Include every role (role_id from the list), most recent first.
Call the tailored_cv tool with the result."""


def _facts_block(profile: dict) -> str:
    roles = {r["id"]: r for r in profile["roles"]}
    lines = ["ROLES:"] + [f"- role_id {r['id']}: {r['title']}, {r['employer']} ({r.get('start') or '?'} to {r.get('end') or 'present'})"
                          for r in profile["roles"]]
    lines.append("\nFACTS:")
    for f in profile["facts"]:
        if f["category"] in ("EDUCATION", "EDUCATION_OPTIONAL", "CERTIFICATION", "LANGUAGE", "MOTIVATION"):
            continue
        where = f"role {f['role_id']}" if f.get("role_id") in roles else "general"
        lines.append(f"[{f['id']}] ({where}, {f['category'].lower()}) {f['text']}")
    return "\n".join(lines)


def _job_block(job) -> str:
    return (f"JOB: {job.title} at {job.company} ({job.location or job.country})\n\n"
            f"POSTING:\n{(job.description or '')[:14000]}")


def guard(cv: dict, profile: dict) -> tuple[dict, list[str]]:
    facts = {f["id"]: f for f in profile["facts"]}
    role_ids = {r["id"] for r in profile["roles"]}
    known_skills = {s.lower() for f in profile["facts"] for s in f.get("skills") or []}
    notes: list[str] = []

    def keep(line: dict, where: str) -> bool:
        cited = [facts[i] for i in line.get("fact_ids") or [] if i in facts]
        if not cited:
            notes.append(f"removed {where} (cites no verified fact): {line.get('text', '')[:80]}")
            return False
        source_numbers = {n.replace(",", "") for f in cited for n in _NUM.findall(f["text"])}
        if {n.replace(",", "") for n in _NUM.findall(line["text"])} - source_numbers:
            notes.append(f"removed {where} (number not in its facts): {line['text'][:80]}")
            return False
        line["text"] = re.sub(r"\s*—\s*", ", ", line["text"])
        return True

    cv["summary"] = [s for s in cv.get("summary") or [] if keep(s, "summary sentence")]
    blocks = []
    for b in cv.get("experience") or []:
        if b.get("role_id") in role_ids:
            b["bullets"] = [x for x in b.get("bullets") or [] if keep(x, "bullet")]
            blocks.append(b)
    cv["experience"] = blocks
    while sum(len(b["bullets"]) for b in blocks) > MAX_BULLETS:
        widest = max(blocks, key=lambda b: len(b["bullets"]))
        notes.append(f"over {MAX_BULLETS} bullets: dropped '{widest['bullets'].pop()['text'][:60]}'")
    corpus = " ".join([f["text"] for f in facts.values()] + sorted(known_skills)).lower()
    words = set(re.findall(r"[a-z0-9#+.]+", corpus))

    def supported(skill: str) -> bool:  # every word of the skill appears in your facts ("MCP servers" ~ "MCP server")
        toks = [t.strip(".") for t in re.findall(r"[a-z0-9#+.]+", skill.lower()) if len(t.strip(".")) > 1]
        return bool(toks) and all(t in words or t.rstrip("s") in words or f"{t}s" in words for t in toks)
    for g in cv.get("skills") or []:
        dropped = [s for s in g["items"] if not supported(s)]
        g["items"] = [s for s in g["items"] if s not in dropped]
        notes += [f"removed skill not in your facts: {s}" for s in dropped]
    cv["skills"] = [g for g in cv.get("skills") or [] if g["items"]]
    return cv, notes


def usage_report(u) -> dict:
    """Cost of one call, priced with prompt caching (5-minute entries), and what the cache saved."""
    fresh, read = u.input_tokens or 0, getattr(u, "cache_read_input_tokens", 0) or 0
    written, out = getattr(u, "cache_creation_input_tokens", 0) or 0, u.output_tokens or 0
    inp, outp = PRICE_PER_MTOK
    cost = (fresh * inp + read * inp * CACHE_READ_FACTOR + written * inp * CACHE_WRITE_FACTOR + out * outp) / 1e6
    uncached = ((fresh + read + written) * inp + out * outp) / 1e6
    total_in = fresh + read + written
    return {"input_tokens": total_in, "cached_tokens": read, "cache_written_tokens": written, "output_tokens": out,
            "cached_pct": round(100 * read / total_in) if total_in else 0,
            "cost_usd": round(cost, 4), "saved_usd": round(uncached - cost, 4)}


def write_cv(job, profile: dict) -> tuple[dict, list[str], float]:
    """Prompt order is stable first, job last: tools + instructions + the candidate's facts are identical for every
    job, so they are cached (5 minutes) and a burst of CVs (a demo, a chat session) reads them from cache."""
    s = get_settings()
    client = AnthropicBedrock(aws_region=s.aws_region)
    msg = client.messages.create(
        model=s.cv_model, max_tokens=6000, tools=[CV_TOOL], tool_choice={"type": "auto"},
        system=[{"type": "text", "text": SYSTEM},
                {"type": "text", "text": "CANDIDATE (verified, the only source):\n" + _facts_block(profile),
                 "cache_control": {"type": "ephemeral"}}],
        messages=[{"role": "user", "content": _job_block(job)}])
    use = next((b for b in msg.content if b.type == "tool_use"), None)
    if use is None:
        raise RuntimeError("the model did not return a CV")
    usage = usage_report(msg.usage)
    cv, notes = guard(json.loads(json.dumps(use.input)), profile)
    cv["relocating_to"] = {"GB": "the UK", "NL": "the Netherlands"}.get(job.country or "")
    cv["usage"] = usage
    return cv, notes, usage["cost_usd"]


def extras(profile: dict) -> dict[str, list[str]]:
    pick = lambda c: [f["text"] for f in profile["facts"] if f["category"] == c]  # noqa: E731
    return {"education": pick("EDUCATION"), "certifications": pick("CERTIFICATION"), "languages": pick("LANGUAGE")}
