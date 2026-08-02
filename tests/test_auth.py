"""Auth tests — login, wrong password, session creation."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from db import init_db, get_db, login, logout, get_user_by_token


def setup_module():
    init_db()


def test_login_success():
    """Correct credentials return a token."""
    token = login("admin", "test-admin-pass")
    assert token is not None
    assert len(token) == 64


def test_login_wrong_password():
    assert login("admin", "wrong-password") is None


def test_login_unknown_user():
    assert login("ghost", "whatever") is None


def test_session_created_on_login():
    token = login("admin", "test-admin-pass")
    c = get_db()
    sess = c.execute("SELECT user_id FROM sessions WHERE token=?", (token,)).fetchone()
    c.close()
    assert sess is not None


def test_get_user_by_token():
    token = login("admin", "test-admin-pass")
    user = get_user_by_token(token)
    assert user is not None
    assert user["username"] == "admin"
    assert user["role"] == "admin"


def test_get_user_by_token_invalid():
    assert get_user_by_token("bogus-token") is None


def test_logout_removes_session():
    token = login("admin", "test-admin-pass")
    logout(token)
    assert get_user_by_token(token) is None
