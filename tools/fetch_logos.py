"""Fetch employer logos (each company's own site icon) and a brand colour for the cards.

Run with the backend venv from the repository root:
    python tools/fetch_logos.py [COMPANY ...]
Reads data/logo_domains.json ({company: domain}, covering job employers and profile employers), writes
frontend/public/logos/<slug>.png (256 px) and data/logos.json {company: {logo, color}}.
Unknown companies fall back to a monogram in the UI.
"""
from __future__ import annotations

import io
import json
import re
import sys
import urllib.parse
import urllib.request
from collections import Counter
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "frontend" / "public" / "logos"
MANIFEST = ROOT / "data" / "logos.json"
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0 Safari/537.36"}
DOMAINS_FILE = ROOT / "data" / "logo_domains.json"  # {"Company name as in the bundle": "company-domain.com", ...}
DOMAINS: dict[str, str] = json.loads(DOMAINS_FILE.read_text(encoding="utf-8")) if DOMAINS_FILE.exists() else {}


def slug(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


def get(url: str, limit: int = 3_000_000) -> bytes | None:
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=15) as r:
            return r.read(limit)
    except Exception:
        return None


def candidates(domain: str) -> list[str]:
    base = f"https://{domain}/"
    html = (get(base, 600_000) or b"").decode("utf-8", "ignore")
    found: list[tuple[int, str]] = []
    for tag in re.findall(r"<link[^>]+>", html, re.I):
        rel = (re.search(r'rel=["\']([^"\']+)', tag, re.I) or [None, ""])[1].lower()
        href = (re.search(r'href=["\']([^"\']+)', tag, re.I) or [None, ""])[1]
        if "icon" not in rel or not href or href.lower().endswith(".svg") or href.startswith("data:"):
            continue
        size = max([int(n) for n in re.findall(r"(\d+)x\d+", tag)] or [180 if "apple" in rel else 32])
        found.append((size + (1000 if "apple" in rel else 0), urllib.parse.urljoin(base, href)))
    urls = [u for _, u in sorted(found, reverse=True)]
    urls += [base + "apple-touch-icon.png", f"https://www.google.com/s2/favicons?domain={domain}&sz=256"]
    return list(dict.fromkeys(urls))


def brand_color(img: Image.Image) -> str | None:
    small = img.convert("RGBA").resize((64, 64))
    counts: Counter = Counter()
    for r, g, b, a in small.getdata():
        mx, mn = max(r, g, b), min(r, g, b)
        if a < 200 or mx < 40 or (mx - mn) < 45:  # transparent, near-black, or grey/white
            continue
        counts[(r // 24 * 24, g // 24 * 24, b // 24 * 24)] += 1
    if not counts or counts.most_common(1)[0][1] < 30:
        return None
    r, g, b = counts.most_common(1)[0][0]
    return f"#{min(r + 12, 255):02x}{min(g + 12, 255):02x}{min(b + 12, 255):02x}"


def fetch(name: str, domain: str) -> dict | None:
    for url in candidates(domain):
        data = get(url)
        if not data:
            continue
        try:
            img = Image.open(io.BytesIO(data))
            img.load()
        except Exception:
            continue
        if min(img.size) < (64 if "s2/favicons" in url else 96):
            continue
        img = img.convert("RGBA")
        img.thumbnail((256, 256))
        canvas = Image.new("RGBA", (256, 256), (0, 0, 0, 0))
        canvas.paste(img, ((256 - img.width) // 2, (256 - img.height) // 2))
        path = OUT / f"{slug(name)}.png"
        canvas.save(path)
        return {"logo": f"/logos/{path.name}", "color": brand_color(canvas), "source": url}
    return None


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8")) if MANIFEST.exists() else {}
    only = set(sys.argv[1:])
    for name, domain in DOMAINS.items():
        if only and name not in only:
            continue
        hit = fetch(name, domain)
        print(f"{'ok ' if hit else '-- '}{name:<28} {domain:<22} {(hit or {}).get('color')} {(hit or {}).get('source', '')[:70]}")
        if hit:
            manifest[name] = hit
    MANIFEST.write_text(json.dumps(manifest, indent=1), encoding="utf-8")
