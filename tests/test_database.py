"""Database tests — schema, seed data, and integrity."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from db import init_db, get_db, DB_PATH


def setup_module():
    """Initialize a fresh test DB before all tests."""
    init_db()


def test_tables_exist():
    c = get_db()
    tables = [r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
    c.close()
    for t in ["companies", "users", "categories", "expenses", "income", "budget", "sessions", "api_keys"]:
        assert t in tables, f"Missing table: {t}"


def test_admin_user_exists():
    c = get_db()
    admin = c.execute("SELECT * FROM users WHERE username='admin'").fetchone()
    c.close()
    assert admin is not None
    assert admin["role"] == "admin"


def test_demo_company_exists():
    c = get_db()
    comp = c.execute("SELECT * FROM companies WHERE slug='demo'").fetchone()
    c.close()
    assert comp is not None
    assert comp["currency"] == "EUR"


def test_default_categories():
    c = get_db()
    cats = c.execute("SELECT COUNT(*) as cnt FROM categories WHERE company_id=1").fetchone()
    c.close()
    assert cats["cnt"] >= 5


def test_sample_expenses():
    c = get_db()
    exps = c.execute("SELECT COUNT(*) as cnt FROM expenses WHERE company_id=1").fetchone()
    c.close()
    assert exps["cnt"] > 0


def test_db_path_isolation():
    """Ensure tests use a temp DB, never the real one."""
    assert "exflow_test_" in DB_PATH or "test.db" in DB_PATH, f"Tests must not use real DB: {DB_PATH}"
