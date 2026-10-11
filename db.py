"""
ExFlow Enterprise — DB & Auth helpers (shared by app.py, api.py, tests)
========================================================================
"""
import os
import sqlite3
import hashlib
import secrets

DB_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
os.makedirs(DB_DIR, exist_ok=True)
DB_PATH = os.environ.get("EXFLOW_TEST_DB", os.path.join(DB_DIR, "exflow.db"))


def get_db():
    c = sqlite3.connect(DB_PATH, timeout=30)
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA journal_mode=WAL")
    c.execute("PRAGMA busy_timeout=30000")
    c.execute("PRAGMA foreign_keys=ON")
    return c


def init_db():
    """Create schema + seed demo data if missing."""
    admin_pw = os.environ.get("EXFLOW_ADMIN_PW", "admin123")
    admin_hash = hashlib.sha256(admin_pw.encode()).hexdigest()
    c = get_db()
    c.execute("""CREATE TABLE IF NOT EXISTS companies (
        id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL UNIQUE,
        slug TEXT NOT NULL UNIQUE, currency TEXT DEFAULT 'EUR',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""")

    # Add currency column to tables if missing
    try:
        c.execute("ALTER TABLE expenses ADD COLUMN currency TEXT DEFAULT 'EUR'")
    except sqlite3.OperationalError:
        pass
    try:
        c.execute("ALTER TABLE income ADD COLUMN currency TEXT DEFAULT 'EUR'")
    except sqlite3.OperationalError:
        pass
    try:
        c.execute("ALTER TABLE companies ADD COLUMN brand_color TEXT DEFAULT '#4e8cff'")
    except sqlite3.OperationalError:
        pass  # column already exists

    c.execute("""CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT NOT NULL UNIQUE,
        password_hash TEXT NOT NULL, raw_password TEXT DEFAULT '',
        role TEXT DEFAULT 'user',
        company_id INTEGER REFERENCES companies(id), display_name TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""")
    c.execute("""CREATE TABLE IF NOT EXISTS sessions (
        token TEXT PRIMARY KEY, user_id INTEGER REFERENCES users(id),
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""")
    c.execute("""CREATE TABLE IF NOT EXISTS expenses (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        company_id INTEGER REFERENCES companies(id),
        amount REAL NOT NULL, currency TEXT DEFAULT 'EUR',
        category TEXT NOT NULL,
        description TEXT DEFAULT '', date TEXT NOT NULL,
        created_by INTEGER REFERENCES users(id),
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""")
    c.execute("""CREATE TABLE IF NOT EXISTS categories (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        company_id INTEGER REFERENCES companies(id),
        name TEXT NOT NULL, icon TEXT DEFAULT '📌',
        color TEXT DEFAULT '#6b7280', UNIQUE(company_id, name))""")
    c.execute("""CREATE TABLE IF NOT EXISTS budget (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        company_id INTEGER REFERENCES companies(id),
        month TEXT NOT NULL, category TEXT NOT NULL,
        amount REAL NOT NULL, UNIQUE(company_id, month, category))""")
    c.execute("""CREATE TABLE IF NOT EXISTS income (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        company_id INTEGER REFERENCES companies(id),
        amount REAL NOT NULL, currency TEXT DEFAULT 'EUR',
        source TEXT NOT NULL,
        month TEXT NOT NULL, date TEXT NOT NULL,
        created_by INTEGER REFERENCES users(id))""")
    c.execute("""CREATE TABLE IF NOT EXISTS api_keys (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        company_id INTEGER REFERENCES companies(id),
        key TEXT NOT NULL UNIQUE,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""")

    c.execute("""CREATE TABLE IF NOT EXISTS activity_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        company_id INTEGER REFERENCES companies(id),
        user_id INTEGER REFERENCES users(id),
        username TEXT, action TEXT, detail TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""")

    c.execute("PRAGMA journal_mode=WAL")
    c.commit()

    c.execute("INSERT OR IGNORE INTO companies(id,name,slug,currency,created_at) VALUES(1,'Demo Company','demo','EUR',datetime('now'))")
    c.execute("INSERT OR IGNORE INTO users(id,username,password_hash,raw_password,role,company_id,display_name,created_at) VALUES(1,'admin',?,?,'admin',1,'Admin',datetime('now'))", (admin_hash, admin_pw))

    existing = c.execute("SELECT COUNT(*) FROM categories WHERE company_id=1").fetchone()[0]
    if existing == 0:
        defaults = [
            (1,'Food','🍔','#f97316'),(1,'Housing','🏠','#8b5cf6'),
            (1,'Transport','🚗','#3b82f6'),(1,'Entertainment','🎮','#ec4899'),
            (1,'Health','💊','#10b981'),(1,'Shopping','🛍️','#f59e0b'),
            (1,'Bills','📄','#ef4444'),(1,'Education','📚','#6366f1'),
            (1,'Other','📌','#6b7280'),
        ]
        c.executemany("INSERT INTO categories(company_id,name,icon,color) VALUES(?,?,?,?)", defaults)
        samples = [
            (1,15.0,'Health','Pharmacy','2026-07-10',1),
            (1,22.0,'Transport','Gas','2026-07-12',1),
            (1,95.0,'Food','Weekly shopping','2026-07-13',1),
            (1,65.0,'Bills','Electric bill','2026-07-15',1),
            (1,35.0,'Entertainment','Cinema','2026-07-19',1),
            (1,49.0,'Transport','Monthly ticket','2026-07-01',1),
        ]
        c.executemany("INSERT INTO expenses(company_id,amount,category,description,date,created_by) VALUES(?,?,?,?,?,?)", samples)
        c.execute("INSERT INTO income(company_id,amount,source,month,date) VALUES(1,1500,'Monthly Revenue','2026-07','2026-07-01')")
        budgets = [('2026-07','Food',400),('2026-07','Housing',600),('2026-07','Transport',200),
                   ('2026-07','Entertainment',150),('2026-07','Bills',120),('2026-07','Health',80)]
        c.executemany("INSERT OR IGNORE INTO budget(company_id,month,category,amount) VALUES(1,?,?,?)", budgets)
    c.commit()
    c.close()


def login(username, password):
    """Verify credentials; returns session token or None."""
    h = hashlib.sha256(password.encode()).hexdigest()
    c = get_db()
    user = c.execute("SELECT id FROM users WHERE username=? AND password_hash=?", (username, h)).fetchone()
    if not user:
        c.close()
        return None
    token = secrets.token_hex(32)
    c.execute("DELETE FROM sessions WHERE user_id=?", (user["id"],))
    c.execute("INSERT INTO sessions(token,user_id) VALUES(?,?)", (token, user["id"]))
    c.commit()
    c.close()
    return token


def get_user_by_token(token):
    """Resolve session token -> user dict (or None)."""
    if not token:
        return None
    c = get_db()
    row = c.execute("""
        SELECT u.id, u.username, u.role, u.company_id, u.display_name,
               c.name as company_name, c.currency, COALESCE(c.brand_color,'#4e8cff') as brand_color
        FROM sessions s JOIN users u ON s.user_id=u.id
        JOIN companies c ON u.company_id=c.id
        WHERE s.token=?
    """, (token,)).fetchone()
    c.close()
    return dict(row) if row else None


def logout(token):
    """Delete the session."""
    if token:
        c = get_db()
        c.execute("DELETE FROM sessions WHERE token=?", (token,))
        c.commit()
        c.close()


def log_activity(company_id, user_id, username, action, detail=""):
    """Record an audit-log entry."""
    try:
        c = get_db()
        c.execute("INSERT INTO activity_log(company_id,user_id,username,action,detail) VALUES(?,?,?,?,?)",
                  (company_id, user_id, username, action, detail))
        c.commit()
        c.close()
    except Exception:
        # Never let logging crash the main flow
        pass
