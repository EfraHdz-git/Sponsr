"""Sponsr as a remote MCP server (streamable HTTP at <SPONSR_APP_URL>/mcp) for live demos:
"find me sponsored jobs", "why do I fit", "write my CV for it" from Claude.

Sign-in: OAuth with a Sponsr login page (app/oauth.py) for claude.ai custom connectors, or the static bearer
token SPONSR_MCP_TOKEN for Claude Code. Acts as the demo account (SPONSR_IMPORT_USER), so what Claude does shows
up in the app too. Add to Claude Code:
    claude mcp add --transport http sponsr <SPONSR_APP_URL>/mcp --header "Authorization: Bearer <token>"
"""
from __future__ import annotations

import asyncio
from typing import Literal

from mcp.server.auth.settings import AuthSettings, ClientRegistrationOptions, RevocationOptions
from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings
from mcp.types import ToolAnnotations
from sqlalchemy import select

from app.config import get_settings
from app.db import SessionLocal
from app.models import Application, Job, Swipe, User
from app.oauth import SponsrOAuthProvider

APP_URL = get_settings().app_url.rstrip("/")
READ = ToolAnnotations(readOnlyHint=True, openWorldHint=False)

mcp = FastMCP(
    "sponsr", stateless_http=True, json_response=True, streamable_http_path="/mcp",
    auth_server_provider=SponsrOAuthProvider(),
    auth=AuthSettings(issuer_url=APP_URL, resource_server_url=f"{APP_URL}/mcp", validate_token_resource=False,
                      client_registration_options=ClientRegistrationOptions(enabled=True),
                      revocation_options=RevocationOptions(enabled=True)),
    # Every request needs a token, so the localhost-only host check (for unauthenticated local servers) is off:
    # requests arrive through the reverse proxy under the public host name.
    transport_security=TransportSecuritySettings(enable_dns_rebinding_protection=False),
    instructions=("Sponsr finds engineering jobs at employers that can sponsor a work visa in the UK and the Netherlands. "
                  "Every job is verified twice: the employer is on the official sponsor register, and the posting itself "
                  "says it sponsors visas (quote it). It writes CVs tailored to a job using only the candidate's verified "
                  "facts. Always cite the sponsorship quote and register entry when presenting a job."))


def _user(s) -> User:
    return s.scalar(select(User).where(User.username == get_settings().import_user))


def _job_row(j: Job) -> dict:
    d = j.data or {}
    return {"job_id": j.id, "company": j.company, "title": j.title, "location": j.location, "country": j.country,
            "fit": d.get("rank"), "salary": j.salary or "not published",
            "sponsorship_quote": ((d.get("sponsorship") or {}).get("quote") or "").lstrip("-• "),
            "register_entry": (d.get("licence") or {}).get("entry"), "employer_page": j.url}


@mcp.tool(annotations=READ)
def find_sponsored_jobs(country: Literal["ANY", "GB", "NL"] = "ANY", limit: int = 10) -> list[dict]:
    """Verified engineering jobs at licensed visa sponsors, best fit first (the cards in the Sponsr app)."""
    with SessionLocal() as s:
        q = select(Job).where(Job.active.is_(True))
        if country != "ANY":
            q = q.where(Job.country == country)
        jobs = sorted(s.scalars(q).all(), key=lambda j: -((j.data or {}).get("rank") or 0))
        return [_job_row(j) for j in jobs[:max(1, min(limit, 30))]]


@mcp.tool(annotations=READ)
def job_details(job_id: int) -> dict:
    """One job in full: why the candidate fits, gaps to prepare for, scores, sponsorship evidence, posting excerpt."""
    with SessionLocal() as s:
        j = s.get(Job, job_id)
        if j is None:
            raise ValueError("no such job")
        d = j.data or {}
        return _job_row(j) | {"our_read": d.get("summary"), "why_you_fit": d.get("strengths"), "gaps": d.get("gaps"),
                              "scores": {"skills": d.get("technical"), "interview_chance": d.get("interview"),
                                         "career_fit": d.get("strategic")},
                              "posting_excerpt": (j.description or "")[:2500]}


@mcp.tool(annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=False, openWorldHint=False))
async def create_tailored_cv(job_id: int) -> dict:
    """Write a CV tailored to this job from the candidate's verified facts (Claude Sonnet, about 20 seconds, about
    $0.05). Every line is checked against the facts. Same as swiping right in the app."""
    from app.api import _write_in_background
    with SessionLocal() as s:
        user, job = _user(s), s.get(Job, job_id)
        if job is None:
            raise ValueError("no such job")
        if s.scalar(select(Swipe.id).where(Swipe.user_id == user.id, Swipe.job_id == job_id)) is None:
            s.add(Swipe(user_id=user.id, job_id=job_id, direction="RIGHT"))
        app = s.scalar(select(Application).where(Application.user_id == user.id, Application.job_id == job_id))
        if app is None or app.status == "FAILED":
            app = app or Application(user_id=user.id, job_id=job_id)
            app.status, app.error = "WRITING", None
            s.add(app)
        s.commit()
        app_id, ready = app.id, app.status in ("READY", "APPLIED")
    if not ready:
        await asyncio.to_thread(_write_in_background, app_id)
    with SessionLocal() as s:
        a = s.get(Application, app_id)
        cv = a.cv or {}
        return {"status": a.status, "error": a.error, "company": job.company, "role": job.title,
                "headline": cv.get("headline"), "summary": " ".join(x["text"] for x in cv.get("summary") or []),
                "bullet_points": sum(len(b["bullets"]) for b in cv.get("experience") or []),
                "removed_by_fact_check": len(a.notes or []), "view_and_download": f"{APP_URL}/applications"}


@mcp.tool(annotations=READ)
def my_cvs() -> list[dict]:
    """The tailored CVs written so far (right swipes), newest first."""
    with SessionLocal() as s:
        user = _user(s)
        rows = s.execute(select(Application, Job).join(Job, Job.id == Application.job_id)
                         .where(Application.user_id == user.id).order_by(Application.id.desc())).all()
        return [{"company": j.company, "role": j.title, "status": a.status, "headline": (a.cv or {}).get("headline"),
                 "created": a.created_at.isoformat()[:16]} for a, j in rows]


@mcp.tool(annotations=READ)
def my_profile() -> dict:
    """The candidate's verified profile: headline, roles, top skills and a few achievements (the only source for CVs)."""
    with SessionLocal() as s:
        u = _user(s)
        facts = u.facts or []
        per_role = {r["id"]: sum(1 for f in facts if f.get("role_id") == r["id"]) for r in u.roles or []}
        skills: dict[str, int] = {}
        for f in facts:  # skills the candidate rated STRONG first, then by how many facts show them
            bonus = 100 if f.get("category") == "SKILL" and f.get("skill_level") == "STRONG" else 1
            for sk in f.get("skills") or []:
                skills[sk] = skills.get(sk, 0) + bonus
        return {"name": (u.header or {}).get("full_name"), "headline": (u.header or {}).get("headline"),
                "verified_facts": len(facts),
                "roles": [{"title": r["title"], "employer": r["employer"], "from": r.get("start"), "to": r.get("end") or "present",
                           "facts": per_role.get(r["id"], 0)} for r in u.roles or []],
                "top_skills": [k for k, _ in sorted(skills.items(), key=lambda kv: -kv[1])[:15]],
                "sample_achievements": [f["text"] for f in facts if f.get("category") == "ACHIEVEMENT"][:5]}
