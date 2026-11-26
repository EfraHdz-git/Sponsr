"""Load a bundle exported from the upstream matching engine: the verified job set + the user's verified profile.

Used by the CLI (import-bundle) and by the daily push from the upstream matching engine (POST /api/admin/import).
No Claude calls: everything in the bundle was already evaluated by the upstream matching engine.
"""
from __future__ import annotations

import json
from pathlib import Path

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.config import ROOT
from app.models import Job, User

LOGOS = ROOT / "data" / "logos.json"
JOB_KEYS = ("summary", "strengths", "gaps", "decision", "rank", "strategic", "technical", "interview",
            "role_family", "work_arrangement", "licence", "sponsorship", "ats")


def load_logos(path: Path | None = None) -> dict:
    for p in (path, LOGOS):
        if p and p.exists():
            return json.loads(p.read_text(encoding="utf-8"))
    return {}


def apply_bundle(s: Session, bundle: dict, username: str, logos: dict) -> dict:
    """The bundle becomes the active set (jobs no longer in it are retired; swipes are kept by upstream id,
    so a job you already swiped never comes back). An empty job list never wipes the deck."""
    user = s.scalar(select(User).where(User.username == username.lower()))
    if user is None:
        raise ValueError(f"no user {username}")
    jobs = bundle.get("jobs") or []
    p = bundle.get("profile") or {}
    if p.get("facts"):
        user.header = (p.get("header") or {}) | {"employer_logos": {
            r["employer"]: logos[r["employer"]] for r in p.get("roles") or [] if r["employer"] in logos}}
        user.roles, user.facts = p.get("roles") or [], p["facts"]
    if not jobs:
        s.commit()
        return {"jobs": 0, "kept_previous": True}
    before = {j.source_id for j in s.scalars(select(Job).where(Job.active.is_(True)))}
    s.execute(update(Job).values(active=False))
    for j in jobs:
        job = s.scalar(select(Job).where(Job.source_id == j["source_id"])) or Job(source_id=j["source_id"])
        job.company, job.title, job.location, job.country = j["company"], j["title"], j["location"], j["country"]
        job.url, job.apply_url, job.posted_at, job.salary = j["url"], j.get("apply_url"), j.get("posted_at"), j.get("salary")
        job.description, job.active = j.get("description") or "", True
        brand = logos.get(j["company"]) or {}
        job.data = {k: j.get(k) for k in JOB_KEYS} | {"logo": brand.get("logo"), "color": brand.get("color")}
        s.add(job)
    s.commit()
    now = {j["source_id"] for j in jobs}
    return {"jobs": len(jobs), "new": len(now - before), "retired": len(before - now)}
