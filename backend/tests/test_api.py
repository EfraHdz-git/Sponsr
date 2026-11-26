"""Main flow: sign in, feed, swipe right writes a CV (Claude stubbed), undo, applications, profile; and the guard."""
import os
import tempfile
import time

os.environ["SPONSR_DATABASE_URL"] = f"sqlite:///{tempfile.mkdtemp()}/test.db"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app import api as api_module  # noqa: E402
from app.cli import add_user  # noqa: E402
from app.cv.generate import guard  # noqa: E402
from app.db import SessionLocal, init_db  # noqa: E402
from app.main import app  # noqa: E402
from app.models import Job, User  # noqa: E402

PROFILE = {"header": {"full_name": "Ana Example", "email": "a@x.io", "links": ["https://x.io/"]},
           "roles": [{"id": 1, "employer": "Acme", "title": "Lead Architect", "start": "2020", "end": None, "location": None}],
           "facts": [{"id": 10, "role_id": 1, "category": "ACHIEVEMENT", "text": "Cut costs by 40% on AWS", "skills": ["AWS"]},
                     {"id": 11, "role_id": None, "category": "EDUCATION", "text": "BSc Software Engineering", "skills": []}]}


@pytest.fixture(scope="module")
def client():
    init_db()
    add_user("ana", "secret-pass")
    with SessionLocal() as s:
        u = s.query(User).filter_by(username="ana").one()
        u.header, u.roles, u.facts = PROFILE["header"], PROFILE["roles"], PROFILE["facts"]
        for i, (co, fit) in enumerate((("Northwind", 94), ("Contoso", 76))):
            s.add(Job(source_id=i + 1, company=co, title="Staff Engineer", location="London", country="GB", url="https://x",
                      description="Senior role", data={"rank": fit, "summary": "Strong — fit", "strengths": ["a"], "gaps": [],
                                                      "licence": {"status": "LICENSED"}, "sponsorship": {"status": "CONFIRMED"}}))
        s.commit()
    with TestClient(app) as c:
        yield c


def test_needs_sign_in(client):
    assert client.get("/api/feed").status_code == 401
    assert client.post("/api/login", json={"username": "ana", "password": "nope"}).status_code == 401


def test_feed_swipe_cv_undo_profile(client, monkeypatch):
    def fake_write(job, profile):
        cv = {"headline": "Architect", "summary": [{"text": "Cut costs by 40% on AWS.", "fact_ids": [10]}], "skills": [],
              "experience": [{"role_id": 1, "bullets": [{"text": "Cut AWS costs by 40%.", "fact_ids": [10]}]}]}
        return cv, [], 0.05
    monkeypatch.setattr(api_module, "write_cv", fake_write)
    assert client.post("/api/login", json={"username": "ANA", "password": "secret-pass"}).status_code == 200
    feed = client.get("/api/feed").json()
    assert [c["company"] for c in feed["cards"]] == ["Northwind", "Contoso"] and "—" not in feed["cards"][0]["summary"]
    top = feed["cards"][0]["id"]
    assert client.post("/api/swipe", json={"job_id": top, "direction": "RIGHT"}).json()["application_id"]
    for _ in range(50):
        apps = client.get("/api/applications").json()
        if apps[0]["status"] != "WRITING":
            break
        time.sleep(0.1)
    assert apps[0]["status"] == "READY" and apps[0]["bullets"] == 1
    pdf = client.get(f"/api/applications/{apps[0]['id']}/cv.pdf")
    assert pdf.status_code == 200 and pdf.content[:4] == b"%PDF"
    assert [c["company"] for c in client.get("/api/feed").json()["cards"]] == ["Contoso"]
    client.post("/api/undo")
    assert len(client.get("/api/feed").json()["cards"]) == 2 and client.get("/api/applications").json() == []
    prof = client.get("/api/profile").json()
    assert prof["facts"] == 2 and prof["roles"][0]["facts"][0]["id"] == 10


def test_guard_removes_unsupported_lines():
    cv = {"summary": [{"text": "Cut costs by 40%.", "fact_ids": [10]}, {"text": "Led 500 engineers.", "fact_ids": [10]},
                      {"text": "Invented.", "fact_ids": [99]}], "skills": [{"label": "Cloud", "items": ["AWS", "Kubernetes"]}],
          "experience": [{"role_id": 1, "bullets": []}, {"role_id": 77, "bullets": []}]}
    out, notes = guard(cv, PROFILE)
    assert [s["text"] for s in out["summary"]] == ["Cut costs by 40%."]
    assert out["skills"][0]["items"] == ["AWS"] and [b["role_id"] for b in out["experience"]] == [1]
    assert len(notes) == 3


def test_reset_and_protected_import(client, monkeypatch):
    from app.config import get_settings
    client.post("/api/login", json={"username": "ana", "password": "secret-pass"})
    first = client.get("/api/feed").json()["cards"][0]["id"]
    client.post("/api/swipe", json={"job_id": first, "direction": "LEFT"})
    assert client.post("/api/reset").json()["swipes"] >= 1
    assert len(client.get("/api/feed").json()["cards"]) == 2
    bundle = {"jobs": [{"source_id": 99, "company": "NewCo", "title": "Staff Engineer", "location": "London", "country": "GB",
                        "url": "https://x", "description": "We sponsor visas.", "rank": 80}], "profile": {}}
    assert client.post("/api/admin/import", json=bundle).status_code == 403  # no key configured / sent
    monkeypatch.setattr(get_settings(), "import_key", __import__("pydantic").SecretStr("k1"))
    monkeypatch.setattr(get_settings(), "import_user", "ana")
    assert client.post("/api/admin/import", json=bundle, headers={"X-Import-Key": "wrong"}).status_code == 403
    r = client.post("/api/admin/import", json=bundle, headers={"X-Import-Key": "k1"}).json()
    assert r == {"jobs": 1, "new": 1, "retired": 2}
    assert [c["company"] for c in client.get("/api/feed").json()["cards"]] == ["NewCo"]
    assert client.post("/api/admin/import", json={"jobs": [], "profile": {}}, headers={"X-Import-Key": "k1"}).json()["kept_previous"]
    assert len(client.get("/api/feed").json()["cards"]) == 1  # an empty push never wipes the deck
