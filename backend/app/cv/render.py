"""ATS-friendly PDF CV (one column, real text). Employer, title and dates come
from the verified roles, never from the model. Trims the least relevant bullet until it fits 2 pages."""
from __future__ import annotations

import copy
import io
from xml.sax.saxutils import escape

from pypdf import PdfReader
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import HRFlowable, ListFlowable, ListItem, Paragraph, SimpleDocTemplate

MAX_PAGES = 2
_INK, _MUTED, _RULE, _LINK = "#1a1a1a", "#555555", "#bbbbbb", "#2f5bd3"
_BASE = ParagraphStyle("base", fontName="Helvetica", fontSize=10, leading=14, alignment=TA_LEFT, spaceAfter=3, textColor=_INK)
_NAME = ParagraphStyle("name", parent=_BASE, fontName="Helvetica-Bold", fontSize=20, leading=24, spaceAfter=2)
_HEADLINE = ParagraphStyle("headline", parent=_BASE, fontSize=10.5, leading=14.5, spaceAfter=3)
_HEAD = ParagraphStyle("head", parent=_BASE, fontName="Helvetica-Bold", fontSize=11, leading=14, spaceBefore=12, spaceAfter=1)
_ROLE = ParagraphStyle("role", parent=_BASE, fontName="Helvetica-Bold", fontSize=10.5, spaceBefore=8, spaceAfter=0)
_SUB = ParagraphStyle("sub", parent=_BASE, fontName="Helvetica-Oblique", textColor=_MUTED, spaceAfter=3)
_BULLET = ParagraphStyle("bullet", parent=_BASE, spaceAfter=2.5)


def _label(url: str) -> str:
    return url.split("://", 1)[-1].removeprefix("www.").rstrip("/")


def _contact(header: dict, relocating_to: str | None) -> str:
    head = [f"Relocating to {relocating_to}", header.get("email")] if relocating_to else [header.get("location"), header.get("email")]
    links = [u for u in header.get("links") or [] if u]
    return "  |  ".join([escape(x) for x in head if x] +
                        [f'<link href="{escape(u)}" color="{_LINK}">{escape(_label(u))}</link>' for u in links])


def _dates(r: dict) -> str:
    return f"{r.get('start') or ''} - {r.get('end') or 'Present'}".strip(" -")


def _pdf(header: dict, content: dict, roles: dict[int, dict], extras: dict[str, list[str]]) -> bytes:
    flow = [Paragraph(escape(header.get("full_name") or ""), _NAME)]
    if content.get("headline"):
        flow.append(Paragraph(escape(content["headline"]), _HEADLINE))
    flow.append(Paragraph(_contact(header, content.get("relocating_to")), _SUB))

    def heading(text: str) -> None:
        flow.extend([Paragraph(text.upper(), _HEAD),
                     HRFlowable(width="100%", thickness=0.6, color=_RULE, spaceBefore=1, spaceAfter=5)])
    if content.get("summary"):
        heading("Profile")
        flow.append(Paragraph(escape(" ".join(s["text"] for s in content["summary"])), _BASE))
    if content.get("skills"):
        heading("Skills")
        flow += [Paragraph(escape(f"{g['label']}: {', '.join(g['items'])}"), _BASE) for g in content["skills"]]
    blocks = [b for b in content.get("experience", []) if b["role_id"] in roles]
    if blocks:
        heading("Experience")
        for b in blocks:
            r = roles[b["role_id"]]
            flow += [Paragraph(escape(f"{r['title']}, {r['employer']}"), _ROLE),
                     Paragraph(escape("  |  ".join(x for x in (_dates(r), r.get("location")) if x)), _SUB)]
            if b.get("bullets"):
                flow.append(ListFlowable([ListItem(Paragraph(escape(x["text"]), _BULLET), leftIndent=12) for x in b["bullets"]],
                                         bulletType="bullet", start="•", leftIndent=12, bulletFontSize=8))
    for title, values in (("Education", extras.get("education")), ("Certifications", extras.get("certifications")),
                          ("Languages", extras.get("languages"))):
        if values:
            heading(title)
            flow += [Paragraph(escape(v), _BASE) for v in values]
    buf = io.BytesIO()
    SimpleDocTemplate(buf, pagesize=A4, leftMargin=18 * mm, rightMargin=18 * mm, topMargin=15 * mm, bottomMargin=15 * mm,
                      title=header.get("full_name") or "CV").build(flow)
    return buf.getvalue()


def _trim_once(content: dict) -> str | None:
    exp = content.get("experience", [])
    candidates = [i for i, b in enumerate(exp) if len(b["bullets"]) > 1]
    if candidates:
        i = max(candidates, key=lambda i: (len(exp[i]["bullets"]), i))
        return f"trimmed for length: {exp[i]['bullets'].pop()['text'][:80]}"
    if len(content.get("summary", [])) > 2:
        return f"trimmed summary: {content['summary'].pop()['text'][:80]}"
    return None


def render_cv(header: dict, content: dict, roles: dict[int, dict], extras: dict[str, list[str]]) -> tuple[dict, bytes, list[str]]:
    content, notes = copy.deepcopy(content), []
    for _ in range(60):
        pdf = _pdf(header, content, roles, extras)
        if len(PdfReader(io.BytesIO(pdf)).pages) <= MAX_PAGES:
            break
        note = _trim_once(content)
        if note is None:
            break
        notes.append(note)
    return content, pdf, notes
