"""Who to reach out to about a job: free, deterministic, no lookups.

1. Contacts the posting itself gives for this role (a named person, or the recruiting team when the email is
   offered for questions or applications). Boilerplate addresses are dropped: accessibility and accommodation
   requests, fraud warnings, privacy and data-protection, press, and similar.
2. LinkedIn people searches for the company's recruiters, for the user to open (LinkedIn has no API for this
   and must not be scraped).
"""
from __future__ import annotations

import json
import re
from urllib.parse import quote_plus

EMAIL = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)*\.[a-z]{2,}", re.I)
_BOILERPLATE_CONTEXT = re.compile(
    r"accommodat|accessib|disabilit|adjustment|reasonable|fraud|scam|phish|authentic|impersonat|privacy|personal data|"
    r"data protection|gdpr|dpo\b|contest a decision|automated decision|unsubscribe|press|media enquir|investor|"
    r"report it|whistleblow|ethics|complaint|concern|consultation|authorit|processing|equal opportunit|veteran|"
    r"benefits enquir|it support|helpdesk|exercise your|your rights|retention|delete your", re.I)
_BOILERPLATE_LOCAL = re.compile(  # anywhere in the local part: talentdata.privacy@, jobs.accommodations@
    r"accommodat|accessib|privacy|dpo|gdpr|data|legal|security|abuse|fraud|noreply|no-reply|donotreply|press|media|"
    r"investor|^ir$|^info$|support|help|billing|ethics|compliance|benefits|payroll|unsubscribe|adjust", re.I)
_TEAM_LOCAL = re.compile(r"^(jobs?|careers?|recruit\w*|talent\w*|hiring|people|hr|resourcing|vacanc\w*|apply|cv|werk\w*|vacatures?)", re.I)
_ROLE_CONTEXT = re.compile(
    r"question|enquir|inquir|information|more about|contact|reach out|get in touch|speak|talk|apply|application|send (us )?"
    r"your|cv|resume|position|role|vacanc|opportunit|hiring|recruit|talent", re.I)
_NAME = re.compile(r"(?i:from|contact|to|with|email|recruiter|talent partner|hiring manager|reach|met)\s*[:\-]?\s*"
                   r"((?:[A-Z][a-zà-ÿ'\-]+)(?:\s+(?:van|de|der|den|von)?\s*[A-Z][a-zà-ÿ'\-]+){1,2})"
                   r"\s*(?:via|at|on|by|op|e-?mail:?)?\s*[(,:]?\s*$")
COUNTRY_NAMES = {"GB": "United Kingdom", "NL": "Netherlands", "DE": "Germany", "IE": "Ireland"}


def _person_from_local(local: str) -> str | None:
    """jane.doe / jane_doe -> 'Jane Doe' (only clear first.last shapes)."""
    m = re.fullmatch(r"([a-z]{2,})[._]([a-z]{2,})", local, re.I)
    return f"{m.group(1).title()} {m.group(2).title()}" if m and not _TEAM_LOCAL.match(local) else None


def extract_contacts(text: str) -> list[dict]:
    """Role contacts in a posting, best first: [{email, name, kind: PERSON|RECRUITING_TEAM, context}]."""
    out: dict[str, dict] = {}
    for m in EMAIL.finditer(text or ""):
        email = m.group(0).rstrip(".").lower()
        local = email.split("@")[0]
        before = text[max(0, m.start() - 160):m.start()]
        context = (before + text[m.start():m.end() + 40]).replace("\n", " ").strip()
        after = text[m.end():m.end() + 100]
        if email in out or _BOILERPLATE_LOCAL.search(local) or _BOILERPLATE_CONTEXT.search(before[-120:] + " " + after):
            continue
        named = _NAME.search(before[-90:])
        name = named.group(1).strip() if named else _person_from_local(local)
        if name:
            kind = "PERSON"
        elif _TEAM_LOCAL.match(local) and _ROLE_CONTEXT.search(before[-120:]):
            kind = "RECRUITING_TEAM"
        else:
            continue
        out[email] = {"email": email, "name": name, "kind": kind, "context": re.sub(r"\s+", " ", context)[-220:]}
    return sorted(out.values(), key=lambda c: c["kind"] != "PERSON")


# LinkedIn region ids (geoUrn) for the location filter
GEO_URN = {"GB": "101165590", "NL": "102890719", "DE": "101282230", "IE": "104738515"}


def linkedin_searches(company: str, country: str | None) -> list[dict]:
    """People searches using LinkedIn's company and region filters plus one plain search word. Tested 2026-11-26:
    titleFreeText is dropped from links, and OR / quoted phrases return nothing, so keep the words simple.
    Recruiters search every country: a talent team often sits outside the role's country."""
    geo = f"&geoUrn={quote_plus(json.dumps([GEO_URN[country]]))}" if country in GEO_URN else ""
    where = COUNTRY_NAMES.get(country or "", "")
    out = []
    for label, words, local in (("Recruiters (any country)", "recruiter", False),
                                (f"Engineering managers{f' ({where})' if where else ''}", "engineering manager", True),
                                (f"Everyone{f' ({where})' if where else ''}", "", True)):
        q = f"company={quote_plus(company)}" + (f"&keywords={quote_plus(words)}" if words else "")
        out.append({"label": label, "url": f"https://www.linkedin.com/search/results/people/?{q}{geo if local else ''}&origin=FACETED_SEARCH"})
    return out
