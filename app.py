"""
🏢 ExFlow Enterprise — Multi-company Expense Management
=======================================================
Streamlit + SQLite + AI Features + 3 Languages
"""
import streamlit as st
import sqlite3, hashlib, secrets, os, json, calendar, base64
from datetime import datetime, date
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from io import BytesIO
import tempfile
import pdf_report

st.set_page_config(page_title="ExFlow Enterprise", page_icon="🏢", layout="wide")

# ─── PWA setup (inject manifest + service worker) ───
pwa_html = f"""
<script>
// Inject manifest link and meta tags for PWA
(function() {{
    var head = document.querySelector('head');
    if (!head) return;
    
    // Manifest (inline as data URL)
    var manifest = {json.dumps({
        "name": "ExFlow Enterprise",
        "short_name": "ExFlow",
        "description": "مدیریت هزینه‌های شرکتی",
        "display": "standalone",
        "background_color": "#0e1117",
        "theme_color": "#0e1117",
        "orientation": "portrait",
        "icons": []
    })};
    var link = document.createElement('link');
    link.rel = 'manifest';
    link.href = 'data:application/json,' + encodeURIComponent(JSON.stringify(manifest));
    head.appendChild(link);
    
    // Apple meta tags
    var meta1 = document.createElement('meta');
    meta1.name = 'apple-mobile-web-app-capable';
    meta1.content = 'yes';
    head.appendChild(meta1);
    
    var meta2 = document.createElement('meta');
    meta2.name = 'apple-mobile-web-app-status-bar-style';
    meta2.content = 'black-translucent';
    head.appendChild(meta2);
    
    var meta3 = document.createElement('meta');
    meta3.name = 'theme-color';
    meta3.content = '#0e1117';
    head.appendChild(meta3);
    
    console.log('PWA: Manifest + meta tags injected');
}})();
</script>
"""
st.markdown(pwa_html, unsafe_allow_html=True)

# ─── DB Setup ───
DB_DIR = os.path.join(os.path.dirname(__file__), "data")
os.makedirs(DB_DIR, exist_ok=True)
DB_PATH = os.path.join(DB_DIR, "exflow.db")

def get_db():
    c = sqlite3.connect(DB_PATH, timeout=30)
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA journal_mode=WAL")
    c.execute("PRAGMA busy_timeout=30000")
    c.execute("PRAGMA foreign_keys=ON")
    return c

def init_db():
    # Default admin password — change via env var or after first login!
    admin_pw = os.environ.get("EXFLOW_ADMIN_PW", "admin123")
    admin_hash = hashlib.sha256(admin_pw.encode()).hexdigest()
    c = get_db()
    c.execute("""CREATE TABLE IF NOT EXISTS companies (
        id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL UNIQUE,
        slug TEXT NOT NULL UNIQUE, currency TEXT DEFAULT 'EUR',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""")
    c.execute("""CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT NOT NULL UNIQUE,
        password_hash TEXT NOT NULL, role TEXT DEFAULT 'user',
        company_id INTEGER REFERENCES companies(id), display_name TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""")
    c.execute("""CREATE TABLE IF NOT EXISTS sessions (
        token TEXT PRIMARY KEY, user_id INTEGER REFERENCES users(id),
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""")
    c.execute("""CREATE TABLE IF NOT EXISTS expenses (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        company_id INTEGER REFERENCES companies(id),
        amount REAL NOT NULL, category TEXT NOT NULL,
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
        amount REAL NOT NULL, source TEXT NOT NULL,
        month TEXT NOT NULL, date TEXT NOT NULL,
        created_by INTEGER REFERENCES users(id))""")
    c.execute("""CREATE TABLE IF NOT EXISTS api_keys (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        company_id INTEGER REFERENCES companies(id),
        key TEXT NOT NULL UNIQUE,
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
        # Budget samples
        budgets = [('2026-07','Food',400),('2026-07','Housing',600),('2026-07','Transport',200),
                   ('2026-07','Entertainment',150),('2026-07','Bills',120),('2026-07','Health',80)]
        c.executemany("INSERT OR IGNORE INTO budget(company_id,month,category,amount) VALUES(1,?,?,?)", budgets)
    c.commit()
    c.close()

init_db()

# ─── Translations ───
T = {
    "app.title": {"fa": "مدیریت هزینه شرکتی", "de": "Unternehmensausgaben", "en": "Enterprise Expenses"},
    "login": {"fa": "ورود به سیستم", "de": "Anmelden", "en": "Login"},
    "login_btn": {"fa": "ورود", "de": "Einloggen", "en": "Login"},
    "username": {"fa": "نام کاربری", "de": "Benutzername", "en": "Username"},
    "password": {"fa": "رمز عبور", "de": "Passwort", "en": "Password"},
    "demo": {"fa": "دمو", "de": "Demo", "en": "Demo"},
    "logout": {"fa": "خروج", "de": "Abmelden", "en": "Logout"},
    "dashboard": {"fa": "داشبورد", "de": "Dashboard", "en": "Dashboard"},
    "transactions": {"fa": "تراکنش‌ها", "de": "Transaktionen", "en": "Transactions"},
    "budget": {"fa": "بودجه", "de": "Budget", "en": "Budget"},
    "users": {"fa": "کاربران", "de": "Benutzer", "en": "Users"},
    "settings": {"fa": "تنظیمات", "de": "Einstellungen", "en": "Settings"},
    "expenses": {"fa": "هزینه‌ها", "de": "Ausgaben", "en": "Expenses"},
    "income": {"fa": "درآمد", "de": "Einkommen", "en": "Income"},
    "balance": {"fa": "مانده", "de": "Guthaben", "en": "Balance"},
    "avg": {"fa": "میانگین", "de": "Durchschnitt", "en": "Daily Avg"},
    "count": {"fa": "تعداد", "de": "Anzahl", "en": "Count"},
    "days_remaining": {"fa": "روز مانده", "de": "Tage übrig", "en": "days left"},
    "add_expense": {"fa": "ثبت هزینه", "de": "Ausgabe erfassen", "en": "Add Expense"},
    "add_income": {"fa": "ثبت درآمد", "de": "Einkommen erfassen", "en": "Add Income"},
    "category": {"fa": "دسته", "de": "Kategorie", "en": "Category"},
    "amount": {"fa": "مبلغ (€)", "de": "Betrag (€)", "en": "Amount (€)"},
    "description": {"fa": "توضیح", "de": "Beschreibung", "en": "Description"},
    "date": {"fa": "تاریخ", "de": "Datum", "en": "Date"},
    "save": {"fa": "ذخیره", "de": "Speichern", "en": "Save"},
    "list": {"fa": "لیست", "de": "Liste", "en": "List"},
    "income_list": {"fa": "لیست درآمدها", "de": "Einkommensliste", "en": "Income List"},
    "no_data": {"fa": "داده‌ای موجود نیست", "de": "Keine Daten", "en": "No data"},
    "no_budget": {"fa": "بودجه‌ای تعریف نشده", "de": "Kein Budget", "en": "No budget set"},
    "budget_status": {"fa": "وضعیت بودجه", "de": "Budget-Status", "en": "Budget Status"},
    "budget_set": {"fa": "تعریف بودجه", "de": "Budget setzen", "en": "Set Budget"},
    "month": {"fa": "ماه", "de": "Monat", "en": "Month"},
    "new_user": {"fa": "کاربر جدید", "de": "Neuer Benutzer", "en": "New User"},
    "role": {"fa": "نقش", "de": "Rolle", "en": "Role"},
    "add": {"fa": "اضافه کن", "de": "Hinzufügen", "en": "Add"},
    "source": {"fa": "منبع", "de": "Quelle", "en": "Source"},
    "company_mgmt": {"fa": "مدیریت شرکت‌ها", "de": "Unternehmensverwaltung", "en": "Company Management"},
    "report": {"fa": "گزارش", "de": "Bericht", "en": "Report"},
    "ocr": {"fa": "اسکن فاکتور", "de": "Rechnungsscan", "en": "Scan Invoice"},
    "api_page": {"fa": "اتصال خارجی", "de": "API", "en": "API"},
    "api_desc": {"fa": "با استفاده از API می‌تونی نرم‌افزارهای دیگه رو به ExFlow وصل کنی.", "de": "Verbinde andere Software mit ExFlow über die API.", "en": "Connect other software to ExFlow via the API."},
    "api_keys": {"fa": "API Keys شما", "de": "Deine API Keys", "en": "Your API Keys"},
    "api_exec": {"fa": "اجرای API", "de": "API ausführen", "en": "Run API"},
    "api_run": {"fa": "API سرور روی پورت 8000 اجرا میشه", "de": "API-Server läuft auf Port 8000", "en": "API server runs on port 8000"},
    "api_exec_title": {"fa": "اجرای API", "de": "API ausführen", "en": "Run API"},
    "company_mgmt_title": {"fa": "مدیریت شرکت‌ها", "de": "Unternehmensverwaltung", "en": "Company Management"},
    "only_superadmin": {"fa": "فقط صاحب نرم‌افزار", "de": "Nur Besitzer", "en": "Owner only"},
    "companies_count": {"fa": "شرکت", "de": "Unternehmen", "en": "companies"},
    "master_login": {"fa": "ورود با رمز مدیر (admin)", "de": "Login mit Master-Passwort", "en": "Login with master password"},
    "change_pass": {"fa": "تغییر رمز عبور", "de": "Passwort ändern", "en": "Change Password"},
    "new_pass": {"fa": "رمز جدید", "de": "Neues Passwort", "en": "New password"},
    "old_pass": {"fa": "رمز فعلی", "de": "Aktuelles Passwort", "en": "Current password"},
    "pass_changed": {"fa": "رمز عبور با موفقیت تغییر کرد", "de": "Passwort erfolgreich geändert", "en": "Password changed successfully"},
    "wrong_pass": {"fa": "رمز فعلی اشتباه است", "de": "Falsches Passwort", "en": "Wrong current password"},
}

def tt(key, lang="fa"):
    d = T.get(key, {})
    return d.get(lang, d.get("en", f"?{key}?"))

# ─── Category translations ───
CAT_TR = {
    "Food": {"fa": "خوراک", "de": "Lebensmittel", "en": "Food"},
    "Housing": {"fa": "مسکن", "de": "Wohnung", "en": "Housing"},
    "Transport": {"fa": "حمل و نقل", "de": "Verkehr", "en": "Transport"},
    "Entertainment": {"fa": "تفریح", "de": "Unterhaltung", "en": "Entertainment"},
    "Health": {"fa": "سلامتی", "de": "Gesundheit", "en": "Health"},
    "Shopping": {"fa": "خرید", "de": "Einkaufen", "en": "Shopping"},
    "Bills": {"fa": "قبوض", "de": "Rechnungen", "en": "Bills"},
    "Education": {"fa": "آموزش", "de": "Bildung", "en": "Education"},
    "Other": {"fa": "سایر", "de": "Sonstiges", "en": "Other"},
}

def ct(cat, lang):
    return CAT_TR.get(cat, {}).get(lang, cat)

# ─── Language selector (from query param or session) ───
L = st.session_state.get("lang", "fa")
ql = st.query_params.get("lang")
if ql in ["fa", "de", "en"]:
    L = ql
    st.session_state.lang = L

# ─── Auth ───
def get_current_user_from_session():
    token = st.session_state.get("_token") or ""
    if not token:
        return None
    c = get_db()
    row = c.execute("""
        SELECT u.id, u.username, u.role, u.company_id, u.display_name,
               c.name as company_name, c.currency
        FROM sessions s JOIN users u ON s.user_id=u.id
        JOIN companies c ON u.company_id=c.id
        WHERE s.token=?
    """, (token,)).fetchone()
    c.close()
    return dict(row) if row else None

def login(username, password):
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

def logout():
    token = st.session_state.get("_token", "")
    if token:
        c = get_db()
        c.execute("DELETE FROM sessions WHERE token=?", (token,))
        c.commit()
        c.close()
    st.session_state["_token"] = ""
    st.session_state.pop("user", None)

if "user" not in st.session_state or not st.session_state.user:
    st.session_state.user = get_current_user_from_session()

if not st.session_state.user and st.query_params.get("token"):
    st.session_state["_token"] = st.query_params["token"]
    st.session_state.user = get_current_user_from_session()
    st.query_params.clear()

def require_auth():
    if not st.session_state.user:
        # Language selector on login page
        col1, col2 = st.columns([5, 1])
        with col2:
            lang_opts_login = {"fa": "🇮🇷 فارسی", "de": "🇩🇪 Deutsch", "en": "🇬🇧 English"}
            lang_display = list(lang_opts_login.values())
            lang_idx = list(lang_opts_login.keys()).index(L) if L in lang_opts_login else 1
            chosen_l = st.selectbox("🌐", lang_display, index=lang_idx, key="_login_lang", label_visibility="collapsed")
            for k, v in lang_opts_login.items():
                if v == chosen_l and k != L:
                    st.query_params["lang"] = k
                    st.rerun()
        with col1:
            st.markdown(f"# \U0001F510 ExFlow Enterprise")
            st.markdown(f"### {tt('login', L)}")
        login_container = st.container()
        with login_container:
            u_val = st.text_input(tt("username", L), key="_login_u")
            p_val = st.text_input(tt("password", L), type="password", key="_login_p")
            master_mode = st.checkbox("🔑 " + tt("master_login", L) if tt("master_login", L) else "ورود با رمز مدیر", key="_master")
            if st.button(tt("login_btn", L), use_container_width=True):
                u_check = st.session_state.get("_login_u", "")
                p_check = st.session_state.get("_login_p", "")
                master = st.session_state.get("_master", False)
                if u_check and p_check:
                    if master:
                        # Master login: verify as admin first, then login as target user
                        admin_hash = hashlib.sha256(p_check.encode()).hexdigest()
                        c = get_db()
                        admin_check = c.execute("SELECT id FROM users WHERE username='admin' AND password_hash=?", (admin_hash,)).fetchone()
                        if admin_check:
                            # Login as the target user
                            target = c.execute("SELECT id FROM users WHERE username=?", (u_check,)).fetchone()
                            if target:
                                token = secrets.token_hex(32)
                                c.execute("DELETE FROM sessions WHERE user_id=?", (target["id"],))
                                c.execute("INSERT INTO sessions(token,user_id) VALUES(?,?)", (token, target["id"]))
                                c.commit()
                                st.session_state["_token"] = token
                                st.session_state.user = get_current_user_from_session()
                                st.rerun()
                            else:
                                st.error(f"'{u_check}' " + tt("no_data", L))
                        else:
                            st.error("🔑 " + tt("no_data", L))
                        c.close()
                    else:
                        t = login(u_check, p_check)
                        if t:
                            st.session_state["_token"] = t
                            st.session_state.user = get_current_user_from_session()
                            st.rerun()
                        else:
                            st.error(f"{tt('username', L)} / {tt('password', L)} {tt('no_data', L)}")
                else:
                    st.error(f"{tt('username', L)} / {tt('password', L)} {tt('no_data', L)}")
        st.markdown("---")
        st.markdown(f"{tt('demo', L)}: `admin` / `admin123`")
        st.stop()

require_auth()

user = st.session_state.user
CID = user["company_id"]

# ─── Date badge helper ───
today = date.today()
today_str = today.strftime("%Y-%m-%d")

MONTH_NAMES = {
    1: {"fa": "ژانویه","de":"Januar","en":"January"},
    2: {"fa": "فوریه","de":"Februar","en":"February"},
    3: {"fa": "مارس","de":"März","en":"March"},
    4: {"fa": "آوریل","de":"April","en":"April"},
    5: {"fa": "مه","de":"Mai","en":"May"},
    6: {"fa": "ژوئن","de":"Juni","en":"June"},
    7: {"fa": "ژوئیه","de":"Juli","en":"July"},
    8: {"fa": "اوت","de":"August","en":"August"},
    9: {"fa": "سپتامبر","de":"September","en":"September"},
    10: {"fa": "اکتبر","de":"Oktober","en":"October"},
    11: {"fa": "نوامبر","de":"November","en":"November"},
    12: {"fa": "دسامبر","de":"Dezember","en":"December"},
}

def month_name(m_num, lang):
    return MONTH_NAMES.get(m_num, {}).get(lang, "")

# ─── Sidebar ───
with st.sidebar:
    role = user["role"]
    st.markdown(f"### 🏢 {user['company_name']}")
    st.markdown(f"👤 {user.get('display_name') or user['username']}")
    if role == "superadmin":
        st.markdown(f"🛡️ **Super Admin** — {tt('settings', L)}")
    elif role == "admin":
        st.markdown(f"🛡️ **{tt('settings', L)}**")
    else:
        st.markdown("👤 **" + tt("users", L) + "**")
    st.markdown("---")
    # Language selector
    lang_opts = {"fa": "🇮🇷", "de": "🇩🇪", "en": "🇬🇧"}
    sel_lang_display = list(lang_opts.values())
    sel_lang_idx = list(lang_opts.keys()).index(L)
    chosen_lang = st.selectbox("🌐", sel_lang_display, index=sel_lang_idx, label_visibility="collapsed", key="_lang_sel")
    new_lang = list(lang_opts.keys())[sel_lang_display.index(chosen_lang)]
    if new_lang != L:
        st.query_params["lang"] = new_lang
        st.rerun()
    st.markdown("---")
    # Company switcher (for superadmin only)
    if role == "superadmin":
        from sqlite3 import connect as _sq_conn
        c = _sq_conn(DB_PATH, timeout=10)
        c.row_factory = __import__('sqlite3').Row
        all_companies = c.execute("SELECT id, name FROM companies").fetchall()
        c.close()
        comp_names = [f"{c['name']}" for c in all_companies]
        current_idx = max(0, min(st.session_state.get("_sel_company", 0), len(comp_names)-1))
        sel_comp = st.selectbox(tt("company", L), comp_names, index=current_idx, key="_comp_sel")
        sel_comp_id = all_companies[comp_names.index(sel_comp)]["id"]
        st.session_state["_sel_company"] = comp_names.index(sel_comp)
        CID = sel_comp_id
    st.markdown("---")
    # Role-based navigation
    nav_items = [f"📊 {tt('dashboard',L)}", f"📋 {tt('transactions',L)}", f"🎯 {tt('budget',L)}"]
    if role in ("admin", "superadmin"):
        nav_items.append(f"👥 {tt('users',L)}")
    if role == "superadmin":
        nav_items.append(f"⚙️ {tt('settings',L)}")
        nav_items.append(f"🏗️ {tt('company_mgmt', L)}")
        nav_items.append(f"📄 {tt('ocr', L)}")
        nav_items.append(f"🔗 {tt('api_page', L)}")
    page = st.radio(tt("dashboard", L), nav_items, index=0)
    if st.button(f"🚪 {tt('logout',L)}", use_container_width=True):
        logout()
        st.rerun()

# ─── Data helpers ───
def get_cats():
    c = get_db()
    rows = c.execute("SELECT * FROM categories WHERE company_id=? ORDER BY name", (CID,)).fetchall()
    c.close()
    return [dict(r) for r in rows]

def get_expenses(month):
    c = get_db()
    rows = c.execute("""
        SELECT e.*, u.display_name as creator_name
        FROM expenses e LEFT JOIN users u ON e.created_by=u.id
        WHERE e.company_id=? AND substr(e.date,1,7)=?
        ORDER BY e.date DESC
    """, (CID, month)).fetchall()
    c.close()
    return [dict(r) for r in rows]

def get_all_expenses():
    c = get_db()
    rows = c.execute("""SELECT e.*, u.display_name as creator_name
        FROM expenses e LEFT JOIN users u ON e.created_by=u.id
        WHERE e.company_id=? ORDER BY e.date DESC""", (CID,)).fetchall()
    c.close()
    return [dict(r) for r in rows]

def get_budget(month):
    c = get_db()
    rows = c.execute("SELECT * FROM budget WHERE company_id=? AND month=?", (CID, month)).fetchall()
    c.close()
    return [dict(r) for r in rows]

def get_income(month):
    c = get_db()
    rows = c.execute("SELECT * FROM income WHERE company_id=? AND month=?", (CID, month)).fetchall()
    c.close()
    return [dict(r) for r in rows]

cur_month = today.strftime("%Y-%m")
selected_month = st.session_state.get("sel_month", cur_month)

cats = get_cats()
cmap = {c["name"]: c for c in cats}
ex = get_expenses(selected_month)
ae = get_all_expenses()
bd = get_budget(selected_month)
inc = get_income(selected_month)

ts = sum(e["amount"] for e in ex) or 0
ti = sum(i["amount"] for i in inc) or 0
nt = len(ex)
rm = ti - ts
dim = calendar.monthrange(today.year, today.month)[1]
ad = ts / max(1, today.day) if selected_month == cur_month else ts / max(1, dim)

df = pd.DataFrame(ex) if ex else pd.DataFrame()

# ═══ DATE BADGE ═══
# Live date badge like ExFlow personal
st.markdown(f"""
<div style="display:flex;align-items:center;gap:12px;margin-bottom:8px;">
<div style="background:linear-gradient(135deg,#f7b733,#fc4a1a);border-radius:6px;width:42px;height:42px;display:flex;flex-direction:column;align-items:center;justify-content:center;line-height:1;">
<span style="font-size:9px;color:#fff;opacity:0.85;font-weight:600;">{month_name(today.month, L)[:3]}</span>
<span style="font-size:16px;color:#fff;font-weight:900;">{today.day:02d}</span>
</div>
<div style="flex:1;"></div>
<div style="font-size:0.85rem;color:#888;">
{month_name(today.month, L)} {today.year} — {dim - today.day} {tt("days_remaining", L)}
</div>
</div>
""", unsafe_allow_html=True)

# ═══════════════════════════════════════════
# PAGE ROUTER
# ═══════════════════════════════════════════

if page.startswith("📊"):
    # ─── DASHBOARD ───
    st.markdown(f"# 📊 {user['company_name']}")
    sel_month = st.selectbox(tt("month", L), [cur_month], index=0, key="ms")
    if sel_month != st.session_state.get("sel_month"):
        st.session_state["sel_month"] = sel_month
        st.rerun()
    selected_month = sel_month
    ex = get_expenses(selected_month); ae = get_all_expenses()
    inc = get_income(selected_month); bd = get_budget(selected_month)
    ts = sum(e["amount"] for e in ex) or 0; ti = sum(i["amount"] for i in inc) or 0
    nt = len(ex); rm = ti - ts
    ad = ts / max(1, today.day) if selected_month == cur_month else ts / max(1, dim)
    df = pd.DataFrame(ex) if ex else pd.DataFrame()
    cats = get_cats(); cmap = {c["name"]: c for c in cats}

    c1,c2,c3,c4,c5 = st.columns(5)
    with c1: st.metric(f"💸 {tt('expenses',L)}", f"{ts:,.0f}€")
    with c2: st.metric(f"💰 {tt('income',L)}", f"{ti:,.0f}€")
    with c3: st.metric(f"✅ {tt('balance',L)}", f"{rm:+,.0f}€")
    with c4: st.metric(f"📊 {tt('avg',L)}", f"{ad:.1f}€")
    with c5: st.metric(f"📋 {tt('count',L)}", f"{nt}")

    # PDF Report button
    col_pdf1, col_pdf2 = st.columns([1, 5])
    with col_pdf1:
        if st.button("📄 " + tt("report", L), use_container_width=True):
            cat_tr_dict = {}
            for c in cats:
                cat_tr_dict[c["name"]] = {"fa": ct(c["name"], "fa"), "de": ct(c["name"], "de"), "en": ct(c["name"], "en")}
            try:
                result_path = pdf_report.generate_report(
                    user["company_name"], selected_month,
                    ex, inc, bd, cat_tr_dict, L)
                if result_path.endswith(".html"):
                    # For Persian: download the HTML file (RTL-safe)
                    with open(result_path, "r", encoding="utf-8") as f:
                        html_content = f.read()
                    st.download_button("⬇️ " + tt("save", L), html_content,
                        file_name=f"{user['company_name']}_{selected_month}_report.html",
                        mime="text/html")
                    st.info(f"{tt('report', L)}: " + tt("save", L))
                else:
                    with open(result_path, "rb") as f:
                        st.download_button("⬇️ " + tt("save", L), f,
                            file_name=f"{user['company_name']}_{selected_month}_report.pdf",
                            mime="application/pdf")
            except Exception as e:
                st.error(f"Report Error: {e}")

    if df.empty:
        st.info("📭 " + tt("no_data", L))
    else:
        cat_t = df.groupby("category")["amount"].sum().reset_index()
        cmap = {c["name"]: c for c in cats}
        cat_t["label"] = cat_t["category"].apply(lambda c: f"{cmap.get(c,{}).get('icon','📌')} {ct(c, L)}")
        cat_t["pct"] = (cat_t["amount"] / ts * 100).round(1)
        colors = [cmap.get(c, {}).get("color", "#6b7280") for c in cat_t["category"]]
        cc1, cc2 = st.columns(2)
        with cc1:
            fig = go.Figure(data=[go.Pie(labels=cat_t["label"], values=cat_t["amount"],
                            marker=dict(colors=colors), textinfo="label+percent", hole=0.45)])
            fig.update_layout(title=tt("expenses", L), height=350)
            st.plotly_chart(fig, width="stretch")
        with cc2:
            d2 = df.copy(); d2["date"] = pd.to_datetime(d2["date"])
            dt2 = d2.groupby("date")["amount"].sum().reset_index()
            fig2 = px.bar(dt2, x="date", y="amount", title=tt("avg", L))
            fig2.update_traces(marker_color="#f7b733")
            st.plotly_chart(fig2, width="stretch")

elif page.startswith("📋"):
    # ─── TRANSACTIONS ───
    st.markdown(f"# 📋 {tt('transactions',L)}")
    ca, cl = st.columns([1, 1.6])
    with ca:
        st.markdown(f"### ➕ {tt('add_expense',L)}")
        with st.form("ef"):
            # Company picker for superadmin (override CID for this form)
            form_cid = CID
            if user["role"] == "superadmin":
                _c = get_db()
                all_comps = _c.execute("SELECT id, name FROM companies").fetchall()
                _c.close()
                comp_opts = [c["name"] for c in all_comps]
                comp_sel = st.selectbox("🏢 شرکت", comp_opts, key="ef_comp")
                form_cid = all_comps[comp_opts.index(comp_sel)]["id"]
            cat_opts = [f"{c['icon']} {ct(c['name'], L)}" for c in cats]
            cat_lookup = {ct(c['name'], L): c['name'] for c in cats}
            sc = st.selectbox(tt("category",L), cat_opts).split(" ", 1)[1]
            sc_db = cat_lookup.get(sc, sc)
            am = st.number_input(tt("amount",L), min_value=0.01, step=1.0)
            ds = st.text_input(tt("description",L))
            td = st.date_input(tt("date",L), value=today)
            if st.form_submit_button(f"✅ {tt('save',L)}", use_container_width=True):
                c = get_db(); c.execute("INSERT INTO expenses(company_id,amount,category,description,date,created_by) VALUES(?,?,?,?,?,?)",
                    (form_cid, am, sc_db, ds, td.strftime("%Y-%m-%d"), user["id"]))
                c.commit(); c.close(); st.rerun()
        st.markdown("---")
        st.markdown(f"### 💶 {tt('add_income',L)}")
        with st.form("inf"):
            form_cid2 = CID
            if user["role"] == "superadmin":
                _c2 = get_db()
                comps2 = _c2.execute("SELECT id, name FROM companies").fetchall()
                _c2.close()
                opts2 = [c["name"] for c in comps2]
                sel2 = st.selectbox("🏢 شرکت", opts2, key="if_comp")
                form_cid2 = comps2[opts2.index(sel2)]["id"]
            st.number_input(tt("amount",L), min_value=0.01, step=100.0, key="ia")
            st.text_input(tt("source",L), value="Revenue", key="src")
            st.date_input(tt("date",L), value=today, key="id")
            if st.form_submit_button(f"💾 {tt('save',L)}", use_container_width=True):
                c = get_db(); c.execute("INSERT INTO income(company_id,amount,source,month,date) VALUES(?,?,?,?,?)",
                    (form_cid2, st.session_state.ia, st.session_state.src,
                     st.session_state.id.strftime("%Y-%m"), st.session_state.id.strftime("%Y-%m-%d")))
                c.commit(); c.close(); st.rerun()
    with cl:
        st.markdown(f"### 📋 {tt('list',L)}")
        if ex:
            for e in ex:
                ci = cmap.get(e["category"], {"icon": "📌", "color": "#6b7280"})
                st.markdown(f"<div style='display:flex;align-items:center;gap:8px;padding:4px 0;'><span>{ci['icon']}</span>"
                    f"<span style='background:{ci['color']}20;color:{ci['color']};padding:2px 8px;border-radius:12px;font-size:0.7rem;'>{ct(e['category'], L)}</span>"
                    f"<span style='flex:1;'>{e['description'] or '-'}</span>"
                    f"<span style='font-weight:700;color:#f87171;'>{e['amount']:,.2f}€</span>"
                    f"<span style='font-size:0.78rem;color:#666;'>{e['date']}</span></div>", unsafe_allow_html=True)
                if st.button("🗑️", key=f"de{e['id']}"):
                    c = get_db(); c.execute("DELETE FROM expenses WHERE id=?", (e['id'],)); c.commit(); c.close(); st.rerun()
        else:
            st.info("📭 " + tt("no_data", L))
        st.markdown("---")
        st.markdown(f"### 💰 {tt('income_list',L)}")
        if inc:
            for e in inc:
                st.markdown(f"<div style='display:flex;align-items:center;gap:8px;padding:4px 0;'><span>💰</span>"
                    f"<span style='color:#4ade80;font-weight:700;'>{e['source']}</span><span style='flex:1;'></span>"
                    f"<span style='color:#4ade80;font-weight:900;'>+{e['amount']:,.2f}€</span>"
                    f"<span style='font-size:0.78rem;color:#666;'>{e['date']}</span></div>", unsafe_allow_html=True)
                if st.button("🗑️", key=f"di{e['id']}"):
                    c = get_db(); c.execute("DELETE FROM income WHERE id=?", (e['id'],)); c.commit(); c.close(); st.rerun()
        else:
            st.info("📭 " + tt("no_data", L))

elif page.startswith("🎯"):
    # ─── BUDGET ───
    st.markdown(f"# 🎯 {tt('budget',L)}")
    bm = st.text_input(f"📅 {tt('month',L)} (YYYY-MM)", value=cur_month, key="bm")
    c1, c2 = st.columns([1, 1])
    with c1:
        st.markdown(f"### {tt('budget_set',L)}")
        with st.form("bf"):
            form_cid3 = CID
            if user["role"] == "superadmin":
                _c3 = get_db()
                comps3 = _c3.execute("SELECT id, name FROM companies").fetchall()
                _c3.close()
                opts3 = [c["name"] for c in comps3]
                sel3 = st.selectbox("🏢 شرکت", opts3, key="bf_comp")
                form_cid3 = comps3[opts3.index(sel3)]["id"]
            cat_opts2 = [f"{c['icon']} {ct(c['name'], L)}" for c in cats]
            cat_lookup2 = {ct(c['name'], L): c['name'] for c in cats}
            sc2 = st.selectbox(tt("category",L), cat_opts2).split(" ", 1)[1]
            sc2_db = cat_lookup2.get(sc2, sc2)
            am2 = st.number_input(tt("amount",L), min_value=0.0, step=50.0)
            if st.form_submit_button(f"💾 {tt('save',L)}", use_container_width=True):
                c = get_db(); c.execute("INSERT OR REPLACE INTO budget(company_id,month,category,amount) VALUES(?,?,?,?)",
                    (form_cid3, bm, sc2_db, am2))
                c.commit(); c.close(); st.rerun()
    with c2:
        st.markdown(f"### {tt('budget_status',L)}")
        bdata = get_budget(bm)
        if bdata:
            for b in bdata:
                cat = b["category"]; budget_amt = b["amount"]
                spent = sum(e["amount"] for e in ex if e["category"] == cat) if ex else 0
                rem = budget_amt - spent; pct = min(spent / max(1, budget_amt), 1.0)
                ci2 = cmap.get(cat, {"icon": "📌", "color": "#6b7280"})
                color = "#4ade80" if rem >= 0 else "#f87171"
                em_chk = "✅"; em_wrn = "⚠️"
                st.markdown(f"<div style='display:flex;align-items:center;gap:8px;'><span>{ci2['icon']}</span>"
                    f"<span style='flex:1;'>{ct(cat, L)}</span><span>{spent:.0f}€ / {budget_amt:.0f}€</span>"
                    f"<span style='color:{color};font-weight:700;'>{em_chk if rem>=0 else em_wrn} {rem:+,.0f}€</span></div>", unsafe_allow_html=True)
                st.progress(pct)
        else:
            st.info("📭 " + tt("no_budget", L))

elif page.startswith("👥"):
    # ─── USERS ───
    st.markdown(f"# 👥 {tt('users',L)}")
    if user["role"] not in ("admin", "superadmin"):
        st.error(f"🚫 {tt('settings',L)}")
    else:
        c = get_db()
        users = c.execute("SELECT id, username, display_name, role, created_at FROM users WHERE company_id=?", (CID,)).fetchall()
        c.close()
        for u in users:
            col1, col2 = st.columns([4, 1])
            with col1:
                st.markdown(f"👤 **{u['display_name'] or u['username']}** — {u['role']}")
            with col2:
                if u['username'] != 'admin':
                    if st.button("🗑️", key=f"du{u['id']}", help="حذف کاربر"):
                        c2 = get_db()
                        c2.execute("DELETE FROM users WHERE id=? AND username!='admin'", (u['id'],))
                        c2.commit(); c2.close()
                        st.rerun()
        st.markdown("---")
        with st.form("uf"):
            nu = st.text_input(tt("username",L))
            np = st.text_input(tt("password",L), type="password")
            nd = st.text_input(tt("description",L))
            nr = st.selectbox(tt("role",L), ["user", "admin"])
            if st.form_submit_button(f"➕ {tt('add',L)}", use_container_width=True):
                c2 = get_db()
                try:
                    c2.execute("INSERT INTO users(username,password_hash,raw_password,role,company_id,display_name) VALUES(?,?,?,?,?,?)",
                        (nu, hashlib.sha256(np.encode()).hexdigest(), np, nr, CID, nd))
                    c2.commit(); st.rerun()
                except Exception as e: st.error(str(e))
                c2.close()

elif page.startswith("📄"):
    # ─── OCR INVOICE SCANNER ───
    st.markdown(f"# 📄 {tt('ocr', L)}")
    # Lazy import to avoid PIL conflict at module level
    try:
        from ocr_scanner import extract_from_image
    except ImportError as e:
        st.error(f"📷 OCR module not available: {e}")
        st.info("Install: brew install tesseract && python3 -m pip install pytesseract")
        st.stop()
    
    uploaded_file = st.file_uploader("📎 عکس فاکتور رو آپلود کن", type=["png", "jpg", "jpeg", "pdf"])
    if uploaded_file:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp:
            tmp.write(uploaded_file.getvalue())
            tmp_path = tmp.name
        
        with st.spinner("🔄 در حال پردازش..."):
            result = extract_from_image(tmp_path, lang="deu+eng+ara")
        
        st.markdown("---")
        col1, col2 = st.columns([1, 1])
        with col1:
            st.image(uploaded_file, caption="فاکتور آپلود شده", width=300)
        with col2:
            st.markdown(f"**📋 روش تشخیص:** {result['method']}")
            if result['confidence']:
                st.markdown(f"**🎯 دقت:** {result['confidence']}%")
            st.markdown(f"**🏢 فروشنده:** {result['vendor'] or '—'}")
            st.markdown(f"**📅 تاریخ:** {result['date'] or '—'}")
            st.markdown(f"**💰 مبلغ:** {result['amount']:,.2f}€" if result['amount'] else "**💰 مبلغ:** —")
        
        with st.expander("📝 متن تشخیص داده شده"):
            st.code(result['text'] if result['text'] else "متنی تشخیص داده نشد")
        
        # Quick add expense from invoice
        if result['amount'] > 0:
            st.markdown("---")
            st.markdown("### ➕ ثبت سریع از روی فاکتور")
            with st.form("ocr_add"):
                suggested_cat = "سایر"
                if "lebensmittel" in result['text'].lower() or "food" in result['text'].lower():
                    suggested_cat = "خوراک"
                elif "transport" in result['text'].lower() or "ticket" in result['text'].lower() or "bahn" in result['text'].lower():
                    suggested_cat = "حمل و نقل"
                elif "apotheke" in result['text'].lower() or "health" in result['text'].lower() or "arzt" in result['text'].lower():
                    suggested_cat = "سلامتی"
                cat_opts = [f"{c['icon']} {c['name']}" for c in cats]
                ocr_cat = st.selectbox("دسته", cat_opts, index=0)
                ocr_amt = st.number_input("مبلغ (€)", value=float(result['amount']), format="%.2f")
                ocr_desc = st.text_input("توضیح", value=result['vendor'] or "فاکتور اسکن شده")
                ocr_date = st.date_input("تاریخ", value=datetime.now())
                if st.form_submit_button("✅ ثبت هزینه", use_container_width=True):
                    cat_name = ocr_cat.split(" ", 1)[1]
                    c = get_db()
                    c.execute("INSERT INTO expenses(company_id,amount,category,description,date,created_by) VALUES(?,?,?,?,?,?)",
                             (CID, ocr_amt, cat_name, ocr_desc, ocr_date.strftime("%Y-%m-%d"), user["id"]))
                    c.commit(); c.close()
                    st.success("✅ هزینه ثبت شد!"); st.rerun()
        
        os.unlink(tmp_path)

elif page.startswith("⚙️"):
    # ─── SETTINGS ───
    st.markdown(f"# ⚙️ {user['company_name']}")
    st.markdown(f"💵 {tt('income',L)}: {ti:,.0f}€ | 💸 {tt('expenses',L)}: {ts:,.0f}€ | ✅ {tt('balance',L)}: {rm:+,.0f}€")
    st.markdown(f"📋 {tt('count',L)}: {len(ae)} {tt('transactions',L)} • {len(inc)} {tt('income',L)} • {len(bd)} {tt('budget',L)}")
    st.markdown("---")
    st.markdown("### 📂 " + tt("category",L))
    for c in cats:
        st.markdown(f"{c['icon']} {ct(c['name'], L)} — `{c['color']}`")
    
    # ─── Change Password (all users) ───
    st.markdown("---")
    st.markdown(f"### 🔑 {tt('change_pass', L)}")
    with st.form("cpf"):
        old_pw = st.text_input(tt("old_pass", L), type="password", key="cp_old")
        new_pw = st.text_input(tt("new_pass", L), type="password", key="cp_new")
        if st.form_submit_button(f"💾 {tt('change_pass', L)}", use_container_width=True):
            if old_pw and new_pw:
                h_old = hashlib.sha256(old_pw.encode()).hexdigest()
                c = get_db()
                check = c.execute("SELECT id FROM users WHERE id=? AND password_hash=?", (user["id"], h_old)).fetchone()
                if check:
                    h_new = hashlib.sha256(new_pw.encode()).hexdigest()
                    c.execute("UPDATE users SET password_hash=?, raw_password=? WHERE id=?", (h_new, new_pw, user["id"]))
                    c.commit()
                    st.success(tt("pass_changed", L))
                    st.balloons()
                else:
                    st.error(tt("wrong_pass", L))
                c.close()
            else:
                st.error(f"{tt('old_pass', L)} / {tt('new_pass', L)} " + tt("no_data", L))
    
    if user["role"] == "superadmin":
        st.markdown("---")
        st.markdown("### 🔗 API Keys")
        c = get_db()
        keys = c.execute("SELECT id, key, created_at FROM api_keys WHERE company_id=?", (CID,)).fetchall()
        c.close()
        if keys:
            for k in keys:
                st.code(k["key"][:20] + "...", language="text")
                if st.button("🗑️", key=f"ak{k['id']}"):
                    c2 = get_db(); c2.execute("DELETE FROM api_keys WHERE id=?", (k["id"],)); c2.commit(); c2.close(); st.rerun()
        if st.button("🔑 + ایجاد API Key جدید"):
            from api import create_api_key
            import secrets
            new_key = secrets.token_hex(32)
            c = get_db(); c.execute("INSERT INTO api_keys(company_id, key) VALUES(?,?)", (CID, new_key)); c.commit(); c.close()
            st.code(new_key, language="text")
            st.success("API Key ساخته شد! کپی کن و ذخیره کن.")

elif page.startswith("🔗"):
    # ─── API DOCUMENTATION ───
    st.markdown(f"# 🔗 {tt('api_page', L)}")
    st.markdown(tt('api_desc', L))
    
    c = get_db()
    keys = c.execute("SELECT key, created_at FROM api_keys WHERE company_id=?", (CID,)).fetchall()
    c.close()
    
    st.markdown(f"### 🔑 {tt('api_keys', L)}")
    if keys:
        for k in keys:
            st.code(k["key"], language="text")
    else:
        st.info("هنوز API Key ای ساخته نشده. از بخش تنظیمات یه API Key بساز.")
    
    with st.expander("📖 مستندات API"):
        st.markdown("""
        **Base URL:** `http://localhost:8000`
        
        **Authentication:** Header `X-API-Key: YOUR_KEY`
        
        **📥 GET /expenses** — دریافت لیست هزینه‌ها
        ```
        GET /expenses?month=2026-07
        Header: X-API-Key: your_key_here
        ```
        
        **📤 POST /expenses** — ثبت هزینه جدید
        ```json
        POST /expenses
        Header: X-API-Key: your_key_here
        Body: {"amount": 25.50, "category": "Food", "description": "Mittagessen", "date": "2026-07-27"}
        ```
        
        **📊 GET /stats** — آمار ماهانه
        ```
        GET /stats?month=2026-07
        Header: X-API-Key: your_key_here
        ```
        
        **❌ DELETE /expenses/{id}** — حذف هزینه
        
        **📥 GET /income** — دریافت درآمدها
        
        **📤 POST /income** — ثبت درآمد جدید
        """)
    
    st.markdown(f"### 🚀 {tt('api_exec_title', L)}")
    st.code("cd ~/myHub/projects/exflow-enterprise && python3 api.py", language="bash")
    st.info(tt('api_run', L))

elif page.startswith("🏗️"):
    # ─── SUPERADMIN: Company Management ───
    st.markdown(f"# 🏗️ {tt('company_mgmt_title', L)}")
    if user["role"] != "superadmin":
        st.error(f"🚫 {tt('only_superadmin', L)}")
    else:
        c = get_db()
        companies = c.execute("SELECT id, name, slug, currency, created_at FROM companies").fetchall()
        c.close()
        st.markdown(f"**{len(companies)} {tt('companies_count', L)}**")
        for comp in companies:
            with st.expander(f"🏢 **{comp['name']}** ({comp['slug']}) — {comp['currency']}"):
                # Users of this company
                c2 = get_db()
                users = c2.execute("SELECT id, username, display_name, role, raw_password FROM users WHERE company_id=?", (comp['id'],)).fetchall()
                c2.close()
                for u in users:
                    col1, col2, col3, col4 = st.columns([2.5, 1.5, 1, 1])
                    with col1:
                        st.markdown(f"👤 {u['display_name'] or u['username']}")
                    with col2:
                        st.markdown(f"`{u['username']}` / `{u['raw_password'] or '—'}`")
                    with col3:
                        st.markdown(f"**{u['role']}**")
                    with col4:
                        if st.button("✏️", key=f"eu{comp['id']}_{u['id']}", help="ویرایش"):
                            st.session_state[f"edit_user_{u['id']}"] = True
                        if u['username'] != 'admin':
                            if st.button("🗑️", key=f"cu{comp['id']}_{u['id']}", help="حذف"):
                                c2 = get_db(); c2.execute("DELETE FROM users WHERE id=? AND username!='admin'", (u['id'],)); c2.commit(); c2.close(); st.rerun()
                    
                    # Edit form (shown when ✏️ clicked)
                    if st.session_state.get(f"edit_user_{u['id']}"):
                        with st.form(f"edit_form_{u['id']}"):
                            st.markdown(f"**✏️ ویرایش `{u['username']}`**")
                            ec = st.columns(3)
                            with ec[0]:
                                new_pass = st.text_input("رمز جدید", type="password", key=f"ep{u['id']}")
                            with ec[1]:
                                new_name = st.text_input("نام نمایشی", value=u['display_name'] or "", key=f"en{u['id']}")
                            with ec[2]:
                                new_role = st.selectbox("نقش", ["user", "admin"], index=0 if u['role']=='user' else 1, key=f"er{u['id']}")
                            ec2 = st.columns(2)
                            with ec2[0]:
                                if st.form_submit_button("💾 ذخیره"):
                                    c2 = get_db()
                                    if new_pass:
                                        c2.execute("UPDATE users SET password_hash=?, raw_password=?, display_name=?, role=? WHERE id=?",
                                            (hashlib.sha256(new_pass.encode()).hexdigest(), new_pass, new_name, new_role, u['id']))
                                    else:
                                        c2.execute("UPDATE users SET display_name=?, role=? WHERE id=?",
                                            (new_name, new_role, u['id']))
                                    c2.commit(); c2.close()
                                    st.session_state[f"edit_user_{u['id']}"] = False
                                    st.success("✅ ویرایش شد"); st.rerun()
                            with ec2[1]:
                                if st.form_submit_button("❌ لغو"):
                                    st.session_state[f"edit_user_{u['id']}"] = False
                                    st.rerun()
                
                # Add user form
                with st.form(f"add_user_{comp['id']}"):
                    st.markdown("**➕ کاربر جدید**")
                    cols = st.columns(3)
                    with cols[0]:
                        nu = st.text_input("نام کاربری", key=f"nu{comp['id']}")
                    with cols[1]:
                        np = st.text_input("رمز عبور", type="password", key=f"np{comp['id']}")
                    with cols[2]:
                        nd = st.text_input("نام نمایشی", key=f"nd{comp['id']}")
                    nr = st.selectbox("نقش", ["user", "admin"], key=f"nr{comp['id']}")
                    if st.form_submit_button("➕ اضافه کن", use_container_width=True):
                        c2 = get_db()
                        try:
                            c2.execute("INSERT INTO users(username,password_hash,raw_password,role,company_id,display_name) VALUES(?,?,?,?,?,?)",
                                (nu, hashlib.sha256(np.encode()).hexdigest(), np, nr, comp['id'], nd))
                            c2.commit(); st.success(f"✅ {nu}"); st.rerun()
                        except Exception as e: st.error(str(e))
                        c2.close()
        st.markdown("---")
        st.markdown("### ➕ شرکت جدید")
        with st.form("cf"):
            nm = st.text_input("نام شرکت")
            sl = st.text_input("شناسه (slug)")
            cr = st.selectbox("واحد پول", ["EUR", "USD", "GBP"])
            if st.form_submit_button("➕ ایجاد", use_container_width=True):
                c2 = get_db()
                try:
                    c2.execute("INSERT INTO companies(name,slug,currency) VALUES(?,?,?)", (nm, sl, cr))
                    c2.commit(); st.success(f"شرکت {nm} ایجاد شد"); st.rerun()
                except Exception as e: st.error(str(e))
                c2.close()
