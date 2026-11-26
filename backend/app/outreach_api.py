"""Who to contact about a job, and an on-demand outreach draft (web app routes; the MCP tools reuse these helpers)."""
from __future__ import annotations

import asyncio
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.auth import current_user
from app.contacts import extract_contacts, linkedin_searches
from app.cv.outreach import draft_outreach
from app.db import get_session
from app.models import Job, User

router = APIRouter(prefix="/api")
LINKEDIN_NOTE = ("These open LinkedIn in your own browser, so you need to be signed in to LinkedIn. Sponsr never "
                 "logs in to LinkedIn or reads it for you; it builds the right search, you choose who to contact.")


def contacts_for(job: Job) -> dict:
    return {"company": job.company, "contacts": extract_contacts(job.description or ""),
            "linkedin_searches": linkedin_searches(job.company, job.country), "how_it_works": LINKEDIN_NOTE}


def profile_of(user: User) -> dict:
    return {"header": user.header, "roles": user.roles or [], "facts": user.facts or []}


class OutreachIn(BaseModel):
    recipient: Literal["RECRUITER", "ENGINEERING_LEADER"] = "RECRUITER"
    name: str | None = Field(default=None, max_length=80)


def _job(session: Session, job_id: int) -> Job:
    job = session.get(Job, job_id)
    if job is None:
        raise HTTPException(404, "job not found")
    return job


@router.get("/jobs/{job_id}/contacts")
def job_contacts(job_id: int, _: User = Depends(current_user), session: Session = Depends(get_session)):
    return contacts_for(_job(session, job_id))


@router.post("/jobs/{job_id}/outreach")
async def job_outreach(job_id: int, body: OutreachIn, user: User = Depends(current_user),
                       session: Session = Depends(get_session)):
    job = _job(session, job_id)
    return await asyncio.to_thread(draft_outreach, job, profile_of(user), body.recipient,
                                   (body.name or "").strip() or None)
