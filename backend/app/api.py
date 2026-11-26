"""Sponsr API: sign in, the swipe feed, right swipe = tailored CV, applications, profile."""
from __future__ import annotations

import base64
import hmac
import io
import logging
import re
import threading
from pathlib import Path

from fastapi import APIRouter, Depends, Header, HTTPException, Response
from fastapi.responses import FileResponse
from PIL import Image, ImageOps
from pydantic import BaseModel
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.auth import COOKIE, check_password, current_user, issue_token
from app.config import ROOT, get_settings
from app.cv.generate import extras, write_cv
from app.cv.render import render_cv
from app.db import SessionLocal, get_session, utcnow
from app.models import Application, Job, Swipe, User

log = logging.getLogger("sponsr")
router = APIRouter(prefix="/api")


class LoginIn(BaseModel):
    username: str
    password: str


class SwipeIn(BaseModel):
    job_id: int
    direction: str  # LEFT / RIGHT


def _me(u: User) -> dict:
    h = u.header or {}
    return {"username": u.username, "name": h.get("full_name") or u.username, "headline": h.get("headline"),
            "location": h.get("location"), "facts": len(u.facts or []), "roles": len(u.roles or [])}


@router.post("/login")
def login(body: LoginIn, response: Response, session: Session = Depends(get_session)):
    user = session.scalar(select(User).where(User.username == body.username.strip().lower()))
    if user is None or not check_password(body.password, user.password_hash):
        raise HTTPException(401, "Wrong username or password")
    s = get_settings()
    response.set_cookie(COOKIE, issue_token(user), httponly=True, secure=s.cookie_secure, samesite="lax",
                        max_age=s.session_days * 86400)
    return _me(user)


@router.post("/logout")
def logout(response: Response):
    response.delete_cookie(COOKIE)
    return {"ok": True}


@router.get("/me")
def me(user: User = Depends(current_user)):
    return _me(user)


def clean(v):
    """No em dashes anywhere in the UI (text comes from evaluations and CVs)."""
    if isinstance(v, str):
        return re.sub(r"\s*—\s*", ", ", v).replace("–", "-")
    if isinstance(v, list):
        return [clean(x) for x in v]
    if isinstance(v, dict):
        return {k: clean(x) for k, x in v.items()}
    return v


def _card(j: Job) -> dict:
    return clean(_raw_card(j))


PALETTE = ["#2F5BD3", "#7C3AED", "#0E9F6E", "#E11D48", "#0891B2", "#EA580C", "#4F46E5", "#16A34A"]


def brand(name: str, color: str | None) -> str:
    """The employer's colour (from its logo), or a stable palette colour for the monogram."""
    return color or PALETTE[sum(map(ord, name or "?")) % len(PALETTE)]


def _raw_card(j: Job) -> dict:
    d = j.data or {}
    return {"id": j.id, "company": j.company, "title": j.title, "location": j.location, "country": j.country,
            "logo": d.get("logo"), "color": brand(j.company, d.get("color")), "work": d.get("work_arrangement"),
            "url": j.url, "salary": j.salary, "posted_at": j.posted_at, "summary": d.get("summary"),
            "strengths": d.get("strengths") or [], "gaps": d.get("gaps") or [], "fit": d.get("rank"),
            "scores": {"strategy": d.get("strategic"), "skills": d.get("technical"), "interview": d.get("interview")},
            "licence": d.get("licence") or {}, "sponsorship": d.get("sponsorship") or {}, "description": j.description}


@router.get("/feed")
def feed(user: User = Depends(current_user), session: Session = Depends(get_session)):
    swiped = select(Swipe.job_id).where(Swipe.user_id == user.id)
    jobs = session.scalars(select(Job).where(Job.active.is_(True), Job.id.not_in(swiped))).all()
    jobs.sort(key=lambda j: -((j.data or {}).get("rank") or 0))
    return {"cards": [_card(j) for j in jobs[:20]], "remaining": len(jobs)}


def _write_in_background(app_id: int) -> None:
    with SessionLocal() as s:
        app = s.get(Application, app_id)
        user, job = s.get(User, app.user_id), s.get(Job, app.job_id)
        profile = {"header": user.header, "roles": user.roles, "facts": user.facts}
        try:
            cv, notes, cost = write_cv(job, profile)
            content, pdf, trims = render_cv(user.header, cv, {r["id"]: r for r in user.roles}, extras(profile))
            app.cv, app.pdf, app.notes, app.cost_usd = content, pdf, notes + trims, cost
            app.status, app.ready_at = "READY", utcnow()
        except Exception as exc:  # shown in the UI; the user can retry
            log.exception("CV for application %s failed", app_id)
            app.status, app.error = "FAILED", f"{type(exc).__name__}: {str(exc)[:300]}"
        s.commit()


def _start(app: Application) -> None:
    threading.Thread(target=_write_in_background, args=(app.id,), daemon=True).start()


@router.post("/swipe")
def swipe(body: SwipeIn, user: User = Depends(current_user), session: Session = Depends(get_session)):
    direction = body.direction.upper()
    if direction not in ("LEFT", "RIGHT") or session.get(Job, body.job_id) is None:
        raise HTTPException(422, "unknown job or direction")
    if session.scalar(select(Swipe.id).where(Swipe.user_id == user.id, Swipe.job_id == body.job_id)) is None:
        session.add(Swipe(user_id=user.id, job_id=body.job_id, direction=direction))
    app = None
    if direction == "RIGHT":
        app = session.scalar(select(Application).where(Application.user_id == user.id, Application.job_id == body.job_id))
        if app is None:
            app = Application(user_id=user.id, job_id=body.job_id)
            session.add(app)
    session.commit()
    if app is not None and app.status == "WRITING":
        _start(app)
    return {"ok": True, "application_id": app.id if app else None}


@router.post("/undo")
def undo(user: User = Depends(current_user), session: Session = Depends(get_session)):
    """Undo the last swipe (and its CV if it was a right swipe)."""
    last = session.scalar(select(Swipe).where(Swipe.user_id == user.id).order_by(Swipe.id.desc()).limit(1))
    if last is None:
        raise HTTPException(404, "nothing to undo")
    app = session.scalar(select(Application).where(Application.user_id == user.id, Application.job_id == last.job_id))
    if app is not None and app.status != "APPLIED":
        session.delete(app)
    session.delete(last)
    session.commit()
    return {"job_id": last.job_id}


def _app_out(a: Application, j: Job) -> dict:
    return {"id": a.id, "status": a.status, "job": _card(j) | {"description": None}, "created_at": a.created_at,
            "ready_at": a.ready_at, "error": a.error, "notes": a.notes or [],
            "headline": (a.cv or {}).get("headline"), "summary": " ".join(x["text"] for x in (a.cv or {}).get("summary") or []),
            "bullets": sum(len(b["bullets"]) for b in (a.cv or {}).get("experience") or [])}


@router.post("/reset")
def reset(user: User = Depends(current_user), session: Session = Depends(get_session)):
    """Demo reset: clears your swipes and demo CVs so the whole deck is back."""
    apps = session.execute(delete(Application).where(Application.user_id == user.id)).rowcount
    swipes = session.execute(delete(Swipe).where(Swipe.user_id == user.id)).rowcount
    session.commit()
    return {"swipes": swipes, "applications": apps}


@router.post("/admin/import")
def admin_import(bundle: dict, x_import_key: str | None = Header(default=None), session: Session = Depends(get_session)):
    """Daily push from the upstream matching engine (already-evaluated jobs only; no Claude calls here)."""
    key = get_settings().import_key.get_secret_value()
    if not key or not x_import_key or not hmac.compare_digest(key, x_import_key):
        raise HTTPException(403, "forbidden")
    from app.bundle import apply_bundle, load_logos
    result = apply_bundle(session, bundle, get_settings().import_user, load_logos())
    log.info("daily import: %s", result)
    return result


@router.get("/applications")
def applications(user: User = Depends(current_user), session: Session = Depends(get_session)):
    rows = session.execute(select(Application, Job).join(Job, Job.id == Application.job_id)
                           .where(Application.user_id == user.id).order_by(Application.id.desc())).all()
    return clean([_app_out(a, j) for a, j in rows])


def _own(session: Session, user: User, app_id: int) -> Application:
    app = session.get(Application, app_id)
    if app is None or app.user_id != user.id:
        raise HTTPException(404, "not found")
    return app


@router.post("/applications/{app_id}/retry")
def retry(app_id: int, user: User = Depends(current_user), session: Session = Depends(get_session)):
    app = _own(session, user, app_id)
    app.status, app.error = "WRITING", None
    session.commit()
    _start(app)
    return {"ok": True}


@router.post("/applications/{app_id}/applied")
def mark_applied(app_id: int, user: User = Depends(current_user), session: Session = Depends(get_session)):
    app = _own(session, user, app_id)
    if app.status != "READY":
        raise HTTPException(409, "the CV is not ready yet")
    app.status = "APPLIED"
    session.commit()
    return {"ok": True}


@router.get("/applications/{app_id}/cv.pdf")
def cv_pdf(app_id: int, download: bool = False, user: User = Depends(current_user), session: Session = Depends(get_session)):
    app = _own(session, user, app_id)
    if not app.pdf:
        raise HTTPException(404, "the CV is not ready yet")
    job = session.get(Job, app.job_id)
    name = re.sub(r'[\\/:*?"<>|]+', " ", f"{(user.header or {}).get('full_name') or 'CV'} - {job.company} - {job.title}.pdf")
    disposition = "attachment" if download else "inline"
    return Response(app.pdf, media_type="application/pdf",
                    headers={"Content-Disposition": f'{disposition}; filename="{name.encode("ascii", "ignore").decode()}"'})


@router.get("/profile")
def profile(user: User = Depends(current_user), session: Session = Depends(get_session)):
    roles = sorted(user.roles or [], key=lambda r: (r.get("end") is not None, -(int((r.get("start") or "0")[:4] or 0))))
    by_role: dict = {}
    for f in user.facts or []:
        by_role.setdefault(f.get("role_id"), []).append(f)
    skills: dict[str, str] = {}
    for f in user.facts or []:
        for sk in f.get("skills") or []:
            skills.setdefault(sk, f.get("skill_level") or "")
    logos = (user.header or {}).get("employer_logos") or {}
    header = {k: v for k, v in (user.header or {}).items() if k != "employer_logos"}
    header["photo"] = f"/api/profile/photo?v={int(_photo_path(user).stat().st_mtime)}" if _photo_path(user).exists() else None
    cvs = session.scalar(select(func.count()).select_from(Application).where(Application.user_id == user.id,
                                                                             Application.status.in_(["READY", "APPLIED"]))) or 0
    return clean({"header": header, "skills": sorted(skills, key=str.lower), "facts": len(user.facts or []), "cvs": cvs,
                  "roles": [r | {"facts": by_role.get(r["id"], []), "logo": (logos.get(r["employer"]) or {}).get("logo"),
                                 "color": brand(r["employer"], (logos.get(r["employer"]) or {}).get("color"))} for r in roles],
                  "other": [f for f in by_role.get(None, []) if f["category"] not in ("MOTIVATION",)]})


def _photo_path(user: User) -> Path:
    return ROOT / "data" / "photos" / f"{user.id}.jpg"


class PhotoIn(BaseModel):
    data_url: str  # "data:image/...;base64,..." from the browser


@router.post("/profile/photo")
def upload_photo(body: PhotoIn, user: User = Depends(current_user)):
    """Square-cropped 480 px JPEG; the original file is not kept."""
    try:
        raw = base64.b64decode(body.data_url.split(",", 1)[1], validate=True)
        if len(raw) > 8_000_000:
            raise ValueError("too large")
        img = ImageOps.exif_transpose(Image.open(io.BytesIO(raw))).convert("RGB")
    except Exception:
        raise HTTPException(422, "Please choose a JPG or PNG photo under 8 MB") from None
    side = min(img.size)
    img = img.crop(((img.width - side) // 2, (img.height - side) // 2, (img.width + side) // 2, (img.height + side) // 2))
    path = _photo_path(user)
    path.parent.mkdir(parents=True, exist_ok=True)
    img.resize((480, 480), Image.LANCZOS).save(path, "JPEG", quality=88)
    return {"photo": f"/api/profile/photo?v={int(path.stat().st_mtime)}"}


@router.get("/profile/photo")
def photo(user: User = Depends(current_user)):
    path = _photo_path(user)
    if not path.exists():
        raise HTTPException(404, "no photo")
    return FileResponse(path, media_type="image/jpeg", headers={"Cache-Control": "private, max-age=86400"})
