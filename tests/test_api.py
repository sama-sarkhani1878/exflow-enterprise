"""API tests — FastAPI endpoints (in-process, no server needed)."""
import os
import sys
import secrets

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient  # noqa: E402

from db import init_db, get_db  # noqa: E402
from api import app as fastapi_app  # noqa: E402

init_db()

client = TestClient(fastapi_app)


def _make_key(company_id=1):
    """Create an API key directly in DB."""
    c = get_db()
    key = secrets.token_hex(32)
    c.execute("INSERT INTO api_keys(company_id, key) VALUES(?,?)", (company_id, key))
    c.commit()
    c.close()
    return key


def test_root():
    r = client.get("/")
    assert r.status_code == 200
    assert "running" in r.json()["status"]


def test_expenses_requires_auth():
    # No API key -> FastAPI rejects with 422 (missing header)
    r = client.get("/expenses")
    assert r.status_code in (401, 422)


def test_expenses_wrong_key_rejected():
    r = client.get("/expenses", headers={"X-API-Key": "wrong-key"})
    assert r.status_code == 401


def test_stats_requires_auth():
    r = client.get("/stats")
    assert r.status_code in (401, 422)


def test_post_expense_with_key():
    key = _make_key()
    r = client.post("/expenses",
                    json={"amount": 25.0, "category": "Food", "description": "test", "date": "2026-07-30"},
                    headers={"X-API-Key": key})
    assert r.status_code == 200
    assert r.json()["amount"] == 25.0


def test_post_expense_negative_rejected():
    key = _make_key()
    r = client.post("/expenses",
                    json={"amount": -5, "category": "Food", "description": "bad", "date": "2026-07-30"},
                    headers={"X-API-Key": key})
    assert r.status_code == 400


def test_post_expense_bad_date():
    key = _make_key()
    r = client.post("/expenses",
                    json={"amount": 10, "category": "Food", "description": "bad", "date": "not-a-date"},
                    headers={"X-API-Key": key})
    assert r.status_code == 400


def test_post_income():
    key = _make_key()
    r = client.post("/income",
                    json={"amount": 1000, "source": "Consulting", "date": "2026-07-30"},
                    headers={"X-API-Key": key})
    assert r.status_code == 200


def test_get_stats():
    key = _make_key()
    r = client.get("/stats?month=2026-07", headers={"X-API-Key": key})
    assert r.status_code == 200
    data = r.json()
    assert "total_expenses" in data
    assert "total_income" in data


def test_delete_expense_not_found():
    key = _make_key()
    r = client.delete("/expenses/99999", headers={"X-API-Key": key})
    assert r.status_code == 404


def test_delete_expense_success():
    key = _make_key()
    r = client.post("/expenses",
                    json={"amount": 5.0, "category": "Other", "description": "to delete", "date": "2026-07-30"},
                    headers={"X-API-Key": key})
    expense_id = r.json()["id"]
    r = client.delete(f"/expenses/{expense_id}", headers={"X-API-Key": key})
    assert r.status_code == 200
    assert r.json()["status"] == "deleted"
