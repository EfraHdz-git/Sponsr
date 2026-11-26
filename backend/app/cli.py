"""Admin commands.

python -m app.cli add-user USERNAME [PASSWORD]      prints a random password when none is given
python -m app.cli import-bundle BUNDLE.json USERNAME  jobs (replaces the active set) + that user's profile
"""
import json
import secrets
import sys
from pathlib import Path

from sqlalchemy import select

from app.auth import hash_password
from app.db import SessionLocal, init_db
from app.models import User


def add_user(username: str, password: str | None) -> str:
    password = password or secrets.token_urlsafe(10)
    with SessionLocal() as s:
        user = s.scalar(select(User).where(User.username == username.lower()))
        if user is None:
            s.add(User(username=username.lower(), password_hash=hash_password(password)))
        else:
            user.password_hash = hash_password(password)
        s.commit()
    return password


def import_bundle(path: str, username: str) -> str:
    from app.bundle import apply_bundle, load_logos
    with SessionLocal() as s:
        r = apply_bundle(s, json.load(open(path, encoding="utf-8")), username, load_logos(Path(path).with_name("logos.json")))
    return f"{r['jobs']} jobs active ({r.get('new', 0)} new, {r.get('retired', 0)} retired)"


if __name__ == "__main__":
    init_db()
    args = sys.argv[1:]
    if args[:1] == ["add-user"] and len(args) >= 2:
        print(f"{args[1]} password: {add_user(args[1], args[2] if len(args) > 2 else None)}")
    elif args[:1] == ["import-bundle"] and len(args) == 3:
        print(import_bundle(args[1], args[2]))
    else:
        print(__doc__)
