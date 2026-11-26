"""OAuth 2.1 for the Sponsr MCP server, so claude.ai (web) can add it as a custom connector.

claude.ai registers itself (dynamic client registration), sends the user to /authorize, we show a Sponsr
sign-in page, and on a good username + password we hand back a code it swaps for tokens (PKCE is checked by
the MCP SDK). Clients, pending requests, codes and tokens live in SQLite; codes and tokens are stored only as
SHA-256 hashes. The static SPONSR_MCP_TOKEN keeps working for Claude Code.
"""
from __future__ import annotations

import hashlib
import hmac
import html
import secrets
import time
from urllib.parse import parse_qs

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from mcp.server.auth.provider import (AccessToken, AuthorizationCode, AuthorizationParams, RefreshToken,
                                      construct_redirect_uri)
from mcp.shared.auth import OAuthClientInformationFull, OAuthToken
from sqlalchemy import JSON, Float, String, delete, select
from sqlalchemy.orm import Mapped, mapped_column

from app.auth import check_password
from app.config import get_settings
from app.db import Base, SessionLocal
from app.models import User

APP_URL = "https://sponsr.codetrend.com"
PENDING_TTL, CODE_TTL = 600, 300
ACCESS_TTL, REFRESH_TTL = 24 * 3600, 30 * 86400


class OAuthItem(Base):
    __tablename__ = "oauth_items"
    key: Mapped[str] = mapped_column(String(128), primary_key=True)  # "<kind>:<id or sha256>"
    data: Mapped[dict] = mapped_column(JSON)
    expires_at: Mapped[float | None] = mapped_column(Float, nullable=True)


def _h(secret: str) -> str:
    return hashlib.sha256(secret.encode()).hexdigest()


def _put(key: str, data: dict, ttl: int | None) -> None:
    with SessionLocal() as s:
        s.merge(OAuthItem(key=key, data=data, expires_at=time.time() + ttl if ttl else None))
        s.commit()


def _get(key: str) -> dict | None:
    with SessionLocal() as s:
        item = s.get(OAuthItem, key)
        if item is None:
            return None
        if item.expires_at and item.expires_at < time.time():
            s.delete(item)
            s.commit()
            return None
        return item.data


def _drop(*keys: str) -> None:
    with SessionLocal() as s:
        s.execute(delete(OAuthItem).where(OAuthItem.key.in_(keys)))
        s.execute(delete(OAuthItem).where(OAuthItem.expires_at < time.time()))  # housekeeping
        s.commit()


def _issue(client_id: str, scopes: list[str], subject: str | None, resource: str | None) -> OAuthToken:
    access, refresh = secrets.token_urlsafe(32), secrets.token_urlsafe(32)
    base = {"client_id": client_id, "scopes": scopes, "subject": subject, "resource": resource}
    _put(f"access:{_h(access)}", base | {"expires_at": int(time.time()) + ACCESS_TTL, "refresh": _h(refresh)}, ACCESS_TTL)
    _put(f"refresh:{_h(refresh)}", base | {"expires_at": int(time.time()) + REFRESH_TTL, "access": _h(access)}, REFRESH_TTL)
    return OAuthToken(access_token=access, token_type="Bearer", expires_in=ACCESS_TTL, refresh_token=refresh,
                      scope=" ".join(scopes) or None)


class SponsrOAuthProvider:
    """OAuthAuthorizationServerProvider for the MCP SDK (structural protocol)."""

    async def get_client(self, client_id: str) -> OAuthClientInformationFull | None:
        data = _get(f"client:{client_id}")
        return OAuthClientInformationFull.model_validate(data) if data else None

    async def register_client(self, client_info: OAuthClientInformationFull) -> None:
        _put(f"client:{client_info.client_id}", client_info.model_dump(mode="json"), None)

    async def authorize(self, client: OAuthClientInformationFull, params: AuthorizationParams) -> str:
        req = secrets.token_urlsafe(24)
        _put(f"pending:{req}", {"client_id": client.client_id, "client_name": client.client_name,
                                "params": params.model_dump(mode="json")}, PENDING_TTL)
        return f"{APP_URL}/api/oauth/login?req={req}"

    async def load_authorization_code(self, client: OAuthClientInformationFull, authorization_code: str):
        data = _get(f"code:{_h(authorization_code)}")
        if not data or data["client_id"] != client.client_id:
            return None
        return AuthorizationCode.model_validate(data | {"code": authorization_code})

    async def exchange_authorization_code(self, client: OAuthClientInformationFull,
                                          authorization_code: AuthorizationCode) -> OAuthToken:
        _drop(f"code:{_h(authorization_code.code)}")  # single use
        return _issue(client.client_id, authorization_code.scopes, authorization_code.subject,
                      authorization_code.resource)

    async def load_refresh_token(self, client: OAuthClientInformationFull, refresh_token: str):
        data = _get(f"refresh:{_h(refresh_token)}")
        if not data or data["client_id"] != client.client_id:
            return None
        return RefreshToken(token=refresh_token, client_id=data["client_id"], scopes=data["scopes"],
                            expires_at=data["expires_at"])

    async def exchange_refresh_token(self, client: OAuthClientInformationFull, refresh_token: RefreshToken,
                                     scopes: list[str]) -> OAuthToken:
        old = _get(f"refresh:{_h(refresh_token.token)}") or {}
        _drop(f"refresh:{_h(refresh_token.token)}", f"access:{old.get('access', '')}")  # rotate
        return _issue(client.client_id, scopes or refresh_token.scopes, old.get("subject"), old.get("resource"))

    async def load_access_token(self, token: str) -> AccessToken | None:
        static = get_settings().mcp_token.get_secret_value()
        if static and hmac.compare_digest(token, static):  # Claude Code demo token
            return AccessToken(token=token, client_id="claude-code", scopes=[], subject=get_settings().import_user)
        data = _get(f"access:{_h(token)}")
        if not data:
            return None
        return AccessToken(token=token, client_id=data["client_id"], scopes=data["scopes"],
                           expires_at=data["expires_at"], resource=data.get("resource"), subject=data.get("subject"))

    async def revoke_token(self, token: AccessToken | RefreshToken) -> None:
        for kind in ("access", "refresh"):
            data = _get(f"{kind}:{_h(token.token)}")
            if data:
                _drop(f"{kind}:{_h(token.token)}", f"access:{data.get('access', '')}", f"refresh:{data.get('refresh', '')}")


# ---- the sign-in page claude.ai sends the user to ----

router = APIRouter(prefix="/api/oauth")

LOGO = ('<svg width="44" height="44" viewBox="0 0 48 48" aria-hidden="true"><rect width="48" height="48" rx="13" '
        'fill="#0f172a"/><path d="M31 15.5c-1.8-1.6-4.3-2.5-7-2.5-4.4 0-7.5 2.4-7.5 5.8 0 7.6 15 4.4 15 11.6 0 3.4-3.2 '
        '5.6-7.6 5.6-3 0-5.7-1-7.6-2.8" fill="none" stroke="#fff" stroke-width="3.4" stroke-linecap="round"/>'
        '<circle cx="34" cy="34" r="4" fill="#22c55e"/></svg>')


def _page(req: str, client_name: str | None, error: str = "") -> HTMLResponse:
    who = html.escape(client_name or "An app")
    err = f'<p class="err">{html.escape(error)}</p>' if error else ""
    return HTMLResponse(f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>Sign in to Sponsr</title>
<link rel="icon" href="/favicon.svg"><style>
*{{box-sizing:border-box}}body{{margin:0;min-height:100vh;display:grid;place-items:center;padding:16px;
font-family:Inter,system-ui,-apple-system,Segoe UI,sans-serif;background:#f1f5f9;color:#0f172a}}
.card{{width:100%;max-width:380px;background:#fff;border-radius:20px;padding:32px 28px;box-shadow:0 10px 40px rgba(15,23,42,.08)}}
h1{{font-size:22px;margin:18px 0 6px}}p{{margin:0 0 20px;color:#475569;font-size:14px;line-height:1.5}}
label{{display:block;font-size:13px;font-weight:600;margin:14px 0 6px}}
input{{width:100%;padding:12px 14px;border:1px solid #cbd5e1;border-radius:12px;font-size:15px}}
input:focus{{outline:2px solid #22c55e;border-color:transparent}}
button{{width:100%;margin-top:22px;padding:13px;border:0;border-radius:12px;background:#0f172a;color:#fff;font-size:15px;font-weight:600;cursor:pointer}}
.err{{background:#fef2f2;color:#b91c1c;padding:10px 12px;border-radius:10px;font-size:13px}}
.fine{{margin:18px 0 0;font-size:12px;color:#94a3b8;text-align:center}}</style></head><body>
<form class="card" method="post" action="/api/oauth/login">{LOGO}
<h1>Sign in to Sponsr</h1><p><b>{who}</b> wants to use your Sponsr account: find verified sponsored jobs and
write tailored CVs.</p>{err}<input type="hidden" name="req" value="{html.escape(req)}">
<label for="u">Username</label><input id="u" name="username" autocomplete="username" required autofocus>
<label for="p">Password</label><input id="p" name="password" type="password" autocomplete="current-password" required>
<button type="submit">Allow access</button><p class="fine">You can disconnect it any time from the app's settings.</p>
</form></body></html>""", headers={"X-Frame-Options": "DENY", "Cache-Control": "no-store"})


def _expired() -> HTMLResponse:
    return HTMLResponse("<p style='font-family:system-ui;padding:24px'>This sign-in link expired. "
                        "Go back to Claude and click Connect again.</p>", status_code=400)


@router.get("/login")
def login_page(req: str):
    pending = _get(f"pending:{req}")
    return _page(req, pending.get("client_name")) if pending else _expired()


@router.post("/login")
async def login_submit(request: Request):
    form = {k: v[0] for k, v in parse_qs((await request.body()).decode()).items()}
    req = form.get("req", "")
    pending = _get(f"pending:{req}")
    if not pending:
        return _expired()
    with SessionLocal() as s:
        user = s.scalar(select(User).where(User.username == form.get("username", "").strip().lower()))
        ok = user is not None and check_password(form.get("password", ""), user.password_hash)
    if not ok:
        return _page(req, pending.get("client_name"), "Wrong username or password.")
    _drop(f"pending:{req}")
    p = AuthorizationParams.model_validate(pending["params"])
    code = secrets.token_urlsafe(32)
    _put(f"code:{_h(code)}", {"client_id": pending["client_id"], "scopes": p.scopes or [],
                              "expires_at": time.time() + CODE_TTL, "code_challenge": p.code_challenge,
                              "redirect_uri": str(p.redirect_uri),
                              "redirect_uri_provided_explicitly": p.redirect_uri_provided_explicitly,
                              "resource": p.resource, "subject": user.username}, CODE_TTL)
    return RedirectResponse(construct_redirect_uri(str(p.redirect_uri), code=code, state=p.state), status_code=302)
