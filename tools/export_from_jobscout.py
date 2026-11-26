"""Import contract with the upstream matching engine (not part of this repository).

The engine owns the evaluated job set and the candidate's verified profile; its module app/sponsr_push.py builds the
bundle that it also pushes to Sponsr once a day (POST /api/admin/import with the X-Import-Key header). This script
writes the same bundle to a file for a manual refresh. Run it from the engine's folder, with its environment:
    python path/to/sponsr/tools/export_from_jobscout.py path/to/sponsr/data/bundle.json
Bundle shape: see data/sample-bundle.json.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path.cwd()))

from app.db import SessionLocal  # noqa: E402
from app.sponsr_push import build_bundle  # noqa: E402

if __name__ == "__main__":
    out = Path(sys.argv[1])
    with SessionLocal() as s:
        bundle = build_bundle(s)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(bundle, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{len(bundle['jobs'])} jobs, {len(bundle['profile']['facts'])} facts -> {out}")
