"""
🏢 ExFlow Enterprise — Multi-company Expense Management
=======================================================
Streamlit + SQLite + AI Features + 3 Languages
"""
import streamlit as st
import sqlite3, hashlib, secrets, os, json, calendar, base64, subprocess, sys
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

# ─── Modern theme (custom CSS) ───
MODERN_CSS = """
<style>
/* ── Base ── */
.stApp {
    background: linear-gradient(160deg, #0f172a 0%, #1e293b 55%, #0f172a 100%) !important;
}
[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #0b1220 0%, #111c30 100%) !important;
    border-right: 1px solid rgba(255,255,255,0.06);
}
/* ── Headings ── */
h1, h2, h3 { font-weight: 700 !important; letter-spacing: -0.02em; }
h1 { background: linear-gradient(90deg, #60a5fa, #a78bfa); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
/* ── Cards / metrics ── */
[data-testid="stMetric"] {
    background: rgba(255,255,255,0.04);
    border: 1px solid rgba(255,255,255,0.08);
    border-radius: 14px;
    padding: 14px 16px;
    transition: transform .15s ease, border-color .15s ease;
}
[data-testid="stMetric"]:hover { transform: translateY(-2px); border-color: rgba(96,165,250,0.5); }
[data-testid="stMetricLabel"] { color: #94a3b8 !important; font-size: .8rem; }
[data-testid="stMetricValue"] { color: #f8fafc !important; font-size: 1.7rem !important; font-weight: 700; }
/* ── Buttons ── */
.stButton > button, .stFormSubmitButton > button {
    border-radius: 10px !important;
    font-weight: 600 !important;
    border: 1px solid rgba(96,165,250,0.35) !important;
    transition: all .15s ease;
}
.stButton > button:hover, .stFormSubmitButton > button:hover {
    background: rgba(96,165,250,0.15) !important;
    border-color: #60a5fa !important;
    transform: translateY(-1px);
}
/* ── Expanders ── */
[data-testid="stExpander"] {
    background: rgba(255,255,255,0.03);
    border: 1px solid rgba(255,255,255,0.07);
    border-radius: 12px;
}
/* ── Inputs ── */
.stTextInput input, .stNumberInput input, .stDateInput input, .stSelectbox div[data-baseweb="select"] > div {
    border-radius: 10px !important;
    background: rgba(255,255,255,0.05) !important;
    border-color: rgba(255,255,255,0.1) !important;
    color: #f8fafc !important;
}
/* ── Tabs / radio ── */
[data-testid="stRadio"] label { color: #cbd5e1 !important; }
[data-testid="stRadio"] label:hover { color: #60a5fa !important; }
/* ── Scrollbars ── */
::-webkit-scrollbar { width: 8px; height: 8px; }
::-webkit-scrollbar-thumb { background: rgba(255,255,255,0.15); border-radius: 8px; }
::-webkit-scrollbar-track { background: transparent; }
</style>
"""
st.markdown(MODERN_CSS, unsafe_allow_html=True)

# ─── DB & Auth helpers (shared module — also used by api.py & tests) ───
from db import get_db, init_db, login as _db_login, logout as _db_logout, get_user_by_token, log_activity, DB_PATH

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
    "import_file": {"fa": "ورود فایل (Excel/CSV)", "de": "Datei importieren (Excel/CSV)", "en": "Import file (Excel/CSV)"},
    "source_ph": {"fa": "مثلاً: فروش، قرارداد، مشاوره...", "de": "z.B. Verkauf, Vertrag, Beratung...", "en": "e.g. Sales, Contract, Consulting..."},
    "import_hint": {"fa": "فایل CSV یا Excel رو آپلود کن (ستون‌ها: amount, category, date, description)", "de": "CSV- oder Excel-Datei hochladen (Spalten: amount, category, date, description)", "en": "Upload CSV or Excel file (columns: amount, category, date, description)"},
    "import_run": {"fa": "شروع ورود", "de": "Import starten", "en": "Start import"},
    "imported": {"fa": "ثبت شد", "de": "importiert", "en": "imported"},
    "skipped": {"fa": "رد شد (خطا)", "de": "übersprungen", "en": "skipped"},
    "edit": {"fa": "ویرایش", "de": "Bearbeiten", "en": "Edit"},
    "description": {"fa": "توضیح", "de": "Beschreibung", "en": "Description"},
    "adv_report": {"fa": "گزارش پیشرفته (مقایسه ماه‌ها + خروجی Excel)", "de": "Erweiterter Bericht (Monatsvergleich + Excel)", "en": "Advanced report (monthly comparison + Excel)"},
    "cmp_months": {"fa": "مقایسه ۶ ماه اخیر", "de": "Vergleich letzte 6 Monate", "en": "Last 6 months comparison"},
    "trend6": {"fa": "روند هزینه/درآمد", "de": "Trend Ausgaben/Einnahmen", "en": "Expense/Income trend"},
    "export": {"fa": "خروجی Excel", "de": "Excel-Export", "en": "Excel export"},
    "budget_over": {"fa": "بودجه این دسته تمام شد", "de": "Budget für diese Kategorie aufgebraucht", "en": "Budget used up for this category"},
    "budget_soon": {"fa": "نزدیک به پایان بودجه", "de": "Budget fast aufgebraucht", "en": "Budget nearly used up"},
    "activity_log": {"fa": "گزارش فعالیت", "de": "Aktivitätsprotokoll", "en": "Activity log"},
    "brand_color": {"fa": "رنگ برند شرکت", "de": "Markenfarbe", "en": "Brand color"},
    "save_color": {"fa": "ذخیره رنگ", "de": "Farbe speichern", "en": "Save color"},
    "backup": {"fa": "پشتیبان‌گیری", "de": "Backup", "en": "Backup"},
    "backup_hint": {"fa": "یک نسخه پشتیبان از دیتابیس در پوشه backups گرفته می‌شود.", "de": "Eine Datenbank-Sicherung wird im backups-Ordner erstellt.", "en": "A database backup is created in the backups folder."},
    "do_backup": {"fa": "ایجاد نسخه پشتیبان", "de": "Backup erstellen", "en": "Create backup"},
    "company": {"fa": "شرکت", "de": "Unternehmen", "en": "Company"},
    "ocr_upload": {"fa": "📎 عکس فاکتور رو آپلود کن", "de": "📎 Rechnungsfoto hochladen", "en": "📎 Upload invoice photo"},
    "ocr_processing": {"fa": "در حال پردازش...", "de": "Verarbeitung...", "en": "Processing..."},
    "ocr_uploaded_cap": {"fa": "فاکتور آپلود شده", "de": "Hochgeladene Rechnung", "en": "Uploaded invoice"},
    "ocr_method": {"fa": "روش تشخیص", "de": "Erkennungsmethode", "en": "Detection method"},
    "ocr_confidence": {"fa": "دقت", "de": "Genauigkeit", "en": "Confidence"},
    "ocr_vendor": {"fa": "فروشنده", "de": "Anbieter", "en": "Vendor"},
    "ocr_date_lbl": {"fa": "تاریخ", "de": "Datum", "en": "Date"},
    "ocr_amount_lbl": {"fa": "مبلغ", "de": "Betrag", "en": "Amount"},
    "ocr_detected_text": {"fa": "متن تشخیص داده شده", "de": "Erkannter Text", "en": "Detected text"},
    "ocr_no_text": {"fa": "متنی تشخیص داده نشد", "de": "Kein Text erkannt", "en": "No text detected"},
    "ocr_quick_add": {"fa": "ثبت سریع از روی فاکتور", "de": "Schnell aus Rechnung erfassen", "en": "Quick add from invoice"},
    "ocr_saved": {"fa": "هزینه ثبت شد!", "de": "Ausgabe erfasst!", "en": "Expense saved!"},
    "api_no_key": {"fa": "هنوز API Key ای ساخته نشده. از بخش تنظیمات یه API Key بساز.", "de": "Noch kein API-Key erstellt. Erstellen Sie einen in den Einstellungen.", "en": "No API key yet. Create one in Settings."},
    "api_docs": {"fa": "مستندات API", "de": "API-Dokumentation", "en": "API documentation"},
    "api_new_key": {"fa": "ایجاد API Key جدید", "de": "Neuen API Key erstellen", "en": "Create new API key"},
    "api_key_created": {"fa": "API Key ساخته شد! کپی کن و ذخیره کن.", "de": "API Key erstellt! Kopieren und speichern.", "en": "API key created! Copy and save it."},
    "new_company": {"fa": "شرکت جدید", "de": "Neues Unternehmen", "en": "New company"},
    "company_name": {"fa": "نام شرکت", "de": "Unternehmensname", "en": "Company name"},
    "slug": {"fa": "شناسه (slug)", "de": "Kennung (slug)", "en": "Slug"},
    "currency": {"fa": "واحد پول", "de": "Währung", "en": "Currency"},
    "role": {"fa": "نقش", "de": "Rolle", "en": "Role"},
    "display_name": {"fa": "نام نمایشی", "de": "Anzeigename", "en": "Display name"},
    "add_user": {"fa": "افزودن کاربر", "de": "Benutzer hinzufügen", "en": "Add user"},
    "delete": {"fa": "حذف", "de": "Löschen", "en": "Delete"},
    "delete_user": {"fa": "حذف کاربر", "de": "Benutzer löschen", "en": "Delete user"},
    "search": {"fa": "جستجو", "de": "Suchen", "en": "Search"},
    "search_ph": {"fa": "توضیح، دسته یا تاریخ...", "de": "Beschreibung, Kategorie oder Datum...", "en": "Description, category or date..."},
    "ai_insights": {"fa": "دستیار هوشمند", "de": "KI-Assistent", "en": "AI Assistant"},
    "ai_cat": {"fa": "پیشنهاد هوشمند دسته", "de": "KI-Kategorievorschlag", "en": "AI category suggestion"},
    "ai_assistant": {"fa": "دستیار هوشمند", "de": "KI-Assistent", "en": "AI Assistant"},
    "ai_caption": {"fa": "از دستیار هوشمند بپرس — تحلیل، پیش‌بینی و پیشنهاد", "de": "Frag den KI-Assistenten — Analyse, Prognose, Empfehlung", "en": "Ask the AI assistant — analysis, forecast, suggestions"},
    "ai_chat": {"fa": "گفتگو با داده‌ها", "de": "Chat mit deinen Daten", "en": "Chat with your data"},
    "ai_ask": {"fa": "سوال تو", "de": "Deine Frage", "en": "Your question"},
    "ai_ask_ph": {"fa": "مثلاً: این ماه چقدر خرج کردم؟", "de": "z.B. Wie viel habe ich ausgegeben?", "en": "e.g. How much did I spend this month?"},
    "ai_send": {"fa": "ارسال", "de": "Senden", "en": "Send"},
    "ai_forecast": {"fa": "پیش‌بینی ماه آینده", "de": "Prognose nächster Monat", "en": "Next month forecast"},
    "ai_inspire": {"fa": "بینش‌های این ماه", "de": "Einblicke diesen Monat", "en": "This month's insights"},
    "ai_cat_lbl": {"fa": "دسته‌بندی هوشمند", "de": "Intelligente Kategorisierung", "en": "Smart categorization"},
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
    return get_user_by_token(st.session_state.get("_token") or "")

def login(username, password):
    return _db_login(username, password)

def logout():
    _db_logout(st.session_state.get("_token", ""))
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


JALALI_MONTHS = {
    1: "فروردین", 2: "اردیبهشت", 3: "خرداد", 4: "تیر", 5: "مرداد", 6: "شهریور",
    7: "مهر", 8: "آبان", 9: "آذر", 10: "دی", 11: "بهمن", 12: "اسفند",
}

def jalali_now_str():
    """Return today as 'YYYY-MM-DD' in the Persian (Jalali) calendar."""
    try:
        import jdatetime
        t = jdatetime.date.today()
        return f"{t.year:04d}-{t.month:02d}-{t.day:02d}"
    except Exception:
        return today_str

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
    nav_items = [f"🤖 {tt('ai_assistant',L)}", f"📊 {tt('dashboard',L)}", f"📋 {tt('transactions',L)}", f"🎯 {tt('budget',L)}"]
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
if L == "fa":
    try:
        import jdatetime
        jt = jdatetime.date.today()
        date_line = f"{JALALI_MONTHS.get(jt.month, '')} {jt.year} — {dim - today.day} {tt('days_remaining', L)}"
        month_short = JALALI_MONTHS.get(jt.month, "")[:3]
        day_num = jt.day
    except Exception:
        date_line = f"{month_name(today.month, L)} {today.year} — {dim - today.day} {tt('days_remaining', L)}"
        month_short = month_name(today.month, L)[:3]
        day_num = today.day
else:
    date_line = f"{month_name(today.month, L)} {today.year} — {dim - today.day} {tt('days_remaining', L)}"
    month_short = month_name(today.month, L)[:3]
    day_num = today.day

st.markdown(f"""
<div style="display:flex;align-items:center;gap:12px;margin-bottom:8px;">
<div style="background:linear-gradient(135deg,#f7b733,#fc4a1a);border-radius:6px;width:42px;height:42px;display:flex;flex-direction:column;align-items:center;justify-content:center;line-height:1;">
<span style="font-size:9px;color:#fff;opacity:0.85;font-weight:600;">{month_short}</span>
<span style="font-size:16px;color:#fff;font-weight:900;">{day_num:02d}</span>
</div>
<div style="flex:1;"></div>
<div style="font-size:0.85rem;color:#888;">
{date_line}
</div>
</div>
""", unsafe_allow_html=True)

# ═══════════════════════════════════════════
# PAGE ROUTER
# ═══════════════════════════════════════════

if page.startswith("🤖"):
    # ─── AI ASSISTANT ───
    from ai_assistant import chat, forecast_next_month, monthly_insights, suggest_budget, suggest_category
    st.markdown(f"# 🤖 {tt('ai_assistant', L)}")
    st.caption(tt("ai_caption", L))

    col_chat, col_ai = st.columns([1, 1])
    with col_chat:
        st.markdown(f"### 💬 {tt('ai_chat', L)}")
        q = st.text_input(tt("ai_ask", L), key="ai_q", placeholder=tt("ai_ask_ph", L))
        if q and st.button(f"🚀 {tt('ai_send', L)}"):
            st.markdown(f"> **You:** {q}")
            ans = chat(CID, q, lang=L)
            st.success(f"🤖 {ans}")
        with st.expander(f"📈 {tt('ai_forecast', L)}"):
            st.markdown("🧠 " + forecast_next_month(CID, lang=L))
            # smart budget suggestion
            for cat in [c["name"] for c in cats]:
                sug, spent = suggest_budget(CID, cat, month=cur_month)
                if sug:
                    st.markdown(f"• **{cat}**: پیشنهاد {sug:,.0f}€ (ماه قبل {spent:,.0f}€)")
    with col_ai:
        st.markdown(f"### ✨ {tt('ai_inspire', L)}")
        ins = monthly_insights(CID, lang=L, month=cur_month)
        if ins:
            for it in ins:
                st.markdown(f"- {it['icon']} {it['text']}")
        st.markdown("---")
        st.markdown(f"### 🏷️ {tt('ai_cat_lbl', L)}")

if page.startswith("📊"):
    # ─── DASHBOARD ───
    st.markdown(f"# 📊 <span style='color:{user.get('brand_color','#4e8cff')}'>{user['company_name']}</span>", unsafe_allow_html=True)
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

    # ─── 🤖 AI Insights ───
    from ai_assistant import monthly_insights
    ins = monthly_insights(CID, lang=L, month=selected_month)
    if ins:
        with st.expander(f"🤖 {tt('ai_insights', L)}", expanded=True):
            for it in ins:
                st.markdown(f"<div style='display:flex;gap:10px;align-items:flex-start;padding:6px 0;'>"
                            f"<span style='font-size:1.1rem;'>{it['icon']}</span>"
                            f"<span style='color:#e2e8f0;'>{it['text']}</span></div>", unsafe_allow_html=True)

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

    # ─── Advanced Reports (monthly comparison + Excel export) ───
    with st.expander(f"📈 {tt('adv_report', L)}"):
        # Load all months for this company
        c_adv = get_db()
        all_exp = c_adv.execute("SELECT date, amount, category FROM expenses WHERE company_id=? AND date LIKE ?", (CID, selected_month[:7]+"%")).fetchall()
        c_adv.close()
        exp_df = pd.DataFrame([{"date": r["date"], "amount": r["amount"], "category": r["category"]} for r in all_exp]) if all_exp else pd.DataFrame(columns=["date","amount","category"])
        
        if exp_df.empty:
            st.info("📭 " + tt("no_data", L))
        else:
            # Monthly comparison across last 6 months
            cmp_months = []
            for m_offset in range(5, -1, -1):
                ym = datetime.strptime(selected_month[:7], "%Y-%m").replace(day=1)
                from dateutil.relativedelta import relativedelta
                m_target = (ym - relativedelta(months=m_offset)).strftime("%Y-%m")
                c2 = get_db()
                e_sum = c2.execute("SELECT COALESCE(SUM(amount),0) FROM expenses WHERE company_id=? AND date LIKE ?", (CID, m_target+"%")).fetchone()[0]
                i_sum = c2.execute("SELECT COALESCE(SUM(amount),0) FROM income WHERE company_id=? AND date LIKE ?", (CID, m_target+"%")).fetchone()[0]
                c2.close()
                cmp_months.append({"month": m_target, "expenses": e_sum, "income": i_sum})
            cmp_df = pd.DataFrame(cmp_months)
            
            ccol1, ccol2 = st.columns(2)
            with ccol1:
                st.markdown(f"### {tt('cmp_months', L)}")
                st.dataframe(cmp_df.style.format({"expenses": "{:,.0f}", "income": "{:,.0f}"}), width="stretch", hide_index=True)
            with ccol2:
                fig_m = go.Figure()
                fig_m.add_bar(x=cmp_df["month"], y=cmp_df["expenses"], name=tt("expenses",L), marker_color="#f87171")
                fig_m.add_bar(x=cmp_df["month"], y=cmp_df["income"], name=tt("income",L), marker_color="#4ade80")
                fig_m.update_layout(title=tt("trend6", L), barmode="group", height=300)
                st.plotly_chart(fig_m, width="stretch")
            
            # Excel export
            st.markdown("---")
            st.markdown(f"### 🧾 {tt('export', L)}")
            export_df = pd.DataFrame([{"date": r["date"], "category": r["category"], "amount": r["amount"], "type": tt("expenses",L)} for r in all_exp])
            export_df = export_df[["date","category","amount","type"]]
            if selected_month[:7]:
                inc_df = pd.DataFrame([{"date": r["date"], "category": r["source"], "amount": r["amount"], "type": tt("income",L)}
                                       for r in c_adv2_inc]) if (c_adv2_inc := get_db().execute("SELECT date, source, amount FROM income WHERE company_id=? AND date LIKE ?", (CID, selected_month[:7]+"%")).fetchall()) else pd.DataFrame(columns=["date","category","amount","type"])
            if 'inc_df' in locals() and not inc_df.empty:
                export_df = pd.concat([export_df, inc_df], ignore_index=True)
            buffer = BytesIO()
            with pd.ExcelWriter(buffer, engine="openpyxl") as xw:
                export_df.to_excel(xw, sheet_name=tt("transactions", L), index=False)
            excel_bytes = buffer.getvalue()
            st.download_button(f"⬇️ {tt('save',L)} .xlsx", excel_bytes,
                file_name=f"{user['company_name']}_{selected_month}_export.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

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
    
    # ─── File Import (CSV/Excel) ───
    with st.expander("📂 " + tt("import_file", L)):
        from importer import import_file
        import io as _io
        up_file = st.file_uploader(tt("import_hint", L), type=["csv", "xlsx", "xls"], key="import_up")
        if up_file:
            content = up_file.getvalue()
            st.markdown(f"📄 {up_file.name} — {len(content)/1024:.1f} KB")
            if st.button(f"🚀 {tt('import_run', L)}", use_container_width=True):
                with st.spinner("..."):
                    res = import_file(content, up_file.name, company_id=CID, created_by=user["id"])
                if res.get("ok"):
                    st.success(f"✅ {res['inserted']} / {res['total']} " + tt("imported", L))
                    if res["skipped"]:
                        st.warning(f"⚠️ {res['skipped']} " + tt("skipped", L))
                        for e in res["errors"]:
                            st.caption(f"  • {e}")
                    st.rerun()
                else:
                    st.error(res.get("error", "Import failed"))
    
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
                comp_sel = st.selectbox(tt("company", L), comp_opts, key="ef_comp")
                form_cid = all_comps[comp_opts.index(comp_sel)]["id"]
            cat_opts = [f"{c['icon']} {ct(c['name'], L)}" for c in cats]
            cat_lookup = {ct(c['name'], L): c['name'] for c in cats}
            ds0 = st.text_input(tt("description",L), key="ai_desc")
            # AI auto-categorize
            from ai_assistant import suggest_category
            _sug = suggest_category(ds0)
            cat_order = [c['name'] for c in cats]
            _def_idx = cat_order.index(_sug) if _sug in cat_order else 0
                
            col1, col2, col3 = st.columns(3)
            am = col1.number_input(tt("amount",L), min_value=0.01, step=1.0)
            cur = col2.selectbox("Currency", ["EUR", "USD", "IRR"], index=0)
            cat_sel = col3.selectbox(tt("category",L), cat_opts, index=_def_idx)
            sc_db = cat_lookup.get(cat_sel.split(" ", 1)[1], cat_sel.split(" ", 1)[1])
                
            td = st.date_input(tt("date",L), value=today)
            if st.form_submit_button(f"✅ {tt('save',L)}", use_container_width=True):
                c = get_db(); c.execute("INSERT INTO expenses(company_id,amount,currency,category,description,date,created_by) VALUES(?,?,?,?,?,?,?)",
                    (form_cid, am, cur, sc_db, ds0, td.strftime("%Y-%m-%d"), user["id"]))
                c.commit()
                log_activity(form_cid, user["id"], user["username"], "add_expense", f"{am}{cur} {sc_db}")
                # ── Budget warning check ──
                month_ym = td.strftime("%Y-%m")
                b_row = c.execute("SELECT amount as budget FROM budget WHERE company_id=? AND month=? AND category=?", (form_cid, month_ym, sc_db)).fetchone()
                if b_row:
                    used = c.execute("SELECT COALESCE(SUM(amount),0) FROM expenses WHERE company_id=? AND date LIKE ? AND category=?", (form_cid, month_ym+"%", sc_db)).fetchone()[0]
                    pct = used / b_row["budget"] * 100 if b_row["budget"] else 100
                    if pct >= 100:
                        st.warning(f"⚠️ {tt('budget_over', L)}: {used:.0f}{cur} / {b_row['budget']:.0f}{cur} ({pct:.0f}%)")
                c.close()
                st.rerun()
                c.close(); st.rerun()
        st.markdown(f"### 💶 {tt('add_income',L)}")
        with st.form("ii"):
            # Company picker for superadmin
            form_cid2 = CID
            if user["role"] == "superadmin":
                _c = get_db()
                all_comps2 = _c.execute("SELECT id, name FROM companies").fetchall()
                _c.close()
                opts2 = [c["name"] for c in all_comps2]
                sel2 = st.selectbox(tt("company", L), opts2, key="if_comp")
                form_cid2 = all_comps2[opts2.index(sel2)]["id"]
                
            col1, col2 = st.columns(2)
            ia = col1.number_input(tt("amount",L), min_value=0.01, step=100.0)
            cur_i = col2.selectbox("Currency", ["EUR", "USD", "IRR"], index=0, key="cur_inc")
            st.text_input(tt("source",L), placeholder=tt("source_ph", L), key="src")
            id_date = st.date_input(tt("date",L), value=today)
            if st.form_submit_button(f"💾 {tt('save',L)}", use_container_width=True):
                c = get_db(); c.execute("INSERT INTO income(company_id,amount,currency,source,month,date,created_by) VALUES(?,?,?,?,?,?,?)",
                    (form_cid2, ia, cur_i, st.session_state.src, id_date.strftime("%Y-%m"), id_date.strftime("%Y-%m-%d"), user["id"]))
                c.commit()
                log_activity(form_cid2, user["id"], user["username"], "add_income", f"{ia}{cur_i} {st.session_state.src}")
                c.close(); st.rerun()
    with cl:
        st.markdown(f"### 📋 {tt('list',L)}")
        # ── Search / filter ──
        search_q = st.text_input("🔍 " + tt("search", L), key="exp_search", placeholder=tt("search_ph", L))
        shown = ex
        if search_q:
            q = search_q.lower()
            shown = [e for e in ex if q in (e.get('description') or '').lower() or q in e.get('category', '').lower() or q in e.get('date', '')]
        st.caption(f"{tt('count', L)}: {len(shown)}")
        if shown:
            for e in shown:
                ci = cmap.get(e["category"], {"icon": "📌", "color": "#6b7280"})
                col_e, col_btn = st.columns([5, 1])
                cur_sym = {"EUR": "€", "USD": "$", "IRR": "تومان"}.get(e.get('currency', 'EUR'), '€')
                st.markdown(f"<div style='display:flex;align-items:center;gap:10px;padding:6px 0;border-bottom:1px solid #222;'>"
                f"<span>{ci.get('icon','📌')}</span>"
                f"<span style='background:{ci['color']}20;color:{ci['color']};padding:2px 8px;border-radius:12px;font-size:0.7rem;'>{ct(e['category'], L)}</span>"
                f"<span style='flex:1;'>{e['description'] or '-'}</span>"
                f"<span style='font-weight:700;color:#f87171;'>{e['amount']:,.2f} {cur_sym}</span>"
                f"<span style='font-size:0.78rem;color:#666;'>{e['date']}</span></div>", unsafe_allow_html=True)
                with col_btn:
                    st.markdown("")
                    b1, b2 = st.columns(2)
                    with b1:
                        if st.button("✏️", key=f"ee{e['id']}", help=tt("edit", L)):
                            st.session_state[f"edit_exp_{e['id']}"] = True
                    with b2:
                        if st.button("🗑️", key=f"de{e['id']}"):
                            c = get_db(); c.execute("DELETE FROM expenses WHERE id=?", (e['id'],)); c.commit()
                            log_activity(CID, user["id"], user["username"], "delete_expense", f"id={e['id']} {e['description']}")
                            c.close(); st.rerun()
                # Edit form
                if st.session_state.get(f"edit_exp_{e['id']}"):
                    e_amt = st.number_input(tt("amount",L), value=float(e['amount']), min_value=0.01, key=f"ea{e['id']}")
                    e_cat = st.selectbox(tt("category",L), [c['name'] for c in cats],
                                         index=[c['name'] for c in cats].index(e['category']) if e['category'] in [c['name'] for c in cats] else 0, key=f"ec{e['id']}")
                    e_desc = st.text_input(tt("description",L), value=e['description'] or "", key=f"ed{e['id']}")
                    e_date = st.date_input(tt("date",L), value=datetime.strptime(e['date'], "%Y-%m-%d").date() if e['date'] else today, key=f"edt{e['id']}")
                    e_ok, e_cancel = st.columns(2)
                    with e_ok:
                        if st.button(f"💾 {tt('save',L)}", key=f"esave{e['id']}"):
                            c = get_db(); c.execute("UPDATE expenses SET amount=?, category=?, description=?, date=? WHERE id=?",
                                (st.session_state[f"ea{e['id']}"], st.session_state[f"ec{e['id']}"],
                                 st.session_state[f"ed{e['id']}"], st.session_state[f"edt{e['id']}"].strftime("%Y-%m-%d"), e['id']))
                            c.commit()
                            _det = "id=%s → %s€ %s" % (e['id'], st.session_state['ea' + str(e['id'])], st.session_state['ec' + str(e['id'])])
                            log_activity(CID, user["id"], user["username"], "edit_expense", _det)
                            c.close()
                            st.session_state[f"edit_exp_{e['id']}"] = False
                            st.rerun()
                    with e_cancel:
                        if st.button("❌", key=f"ecancel{e['id']}"):
                            st.session_state[f"edit_exp_{e['id']}"] = False
                            st.rerun()
        else:
            st.info("📭 " + tt("no_data", L))
        st.markdown("---")
        st.markdown(f"### 💰 {tt('income_list',L)}")
        if inc:
            for e in inc:
                col_i, col_ibtn = st.columns([5, 1])
                with col_i:
                    st.markdown(f"<div style='display:flex;align-items:center;gap:8px;padding:4px 0;'><span>💰</span>"
                        f"<span style='color:#4ade80;font-weight:700;'>{e['source']}</span><span style='flex:1;'></span>"
                        f"<span style='color:#4ade80;font-weight:900;'>+{e['amount']:,.2f}€</span>"
                        f"<span style='font-size:0.78rem;color:#666;'>{e['date']}</span></div>", unsafe_allow_html=True)
                with col_ibtn:
                    st.markdown("")
                    b1, b2 = st.columns(2)
                    with b1:
                        if st.button("✏️", key=f"ei{e['id']}", help=tt("edit", L)):
                            st.session_state[f"edit_inc_{e['id']}"] = True
                    with b2:
                        if st.button("🗑️", key=f"di{e['id']}"):
                            c = get_db(); c.execute("DELETE FROM income WHERE id=?", (e['id'],)); c.commit()
                            log_activity(CID, user["id"], user["username"], "delete_income", f"id={e['id']} {e['source']}")
                            c.close(); st.rerun()
                if st.session_state.get(f"edit_inc_{e['id']}"):
                    i_amt = st.number_input(tt("amount",L), value=float(e['amount']), min_value=0.01, key=f"ia{e['id']}")
                    i_src = st.text_input(tt("source",L), value=e['source'], key=f"is{e['id']}")
                    i_date = st.date_input(tt("date",L), value=datetime.strptime(e['date'], "%Y-%m-%d").date() if e['date'] else today, key=f"idt{e['id']}")
                    i_ok, i_cancel = st.columns(2)
                    with i_ok:
                        if st.button(f"💾 {tt('save',L)}", key=f"isave{e['id']}"):
                            c = get_db(); c.execute("UPDATE income SET amount=?, source=?, date=? WHERE id=?",
                                (st.session_state[f"ia{e['id']}"], st.session_state[f"is{e['id']}"],
                                 st.session_state[f"idt{e['id']}"].strftime("%Y-%m-%d"), e['id']))
                            c.commit()
                            log_activity(CID, user["id"], user["username"], "edit_income",
                                         "id=%s → %s€ %s" % (e['id'], st.session_state['ia' + str(e['id'])], st.session_state['is' + str(e['id'])]))
                            c.close()
                            st.session_state[f"edit_inc_{e['id']}"] = False
                            st.rerun()
                    with i_cancel:
                        if st.button("❌", key=f"icancel{e['id']}"):
                            st.session_state[f"edit_inc_{e['id']}"] = False
                            st.rerun()
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
                sel3 = st.selectbox(tt("company", L), opts3, key="bf_comp")
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
                    if st.button("🗑️", key=f"du{u['id']}", help=tt("delete_user", L)):
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
    
    uploaded_file = st.file_uploader(tt("ocr_upload", L), type=["png", "jpg", "jpeg", "pdf"])
    if uploaded_file:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp:
            tmp.write(uploaded_file.getvalue())
            tmp_path = tmp.name
        
        with st.spinner("🔄 " + tt("ocr_processing", L)):
            result = extract_from_image(tmp_path, lang="deu+eng+ara")
        
        st.markdown("---")
        col1, col2 = st.columns([1, 1])
        with col1:
            st.image(uploaded_file, caption=tt("ocr_uploaded_cap", L), width=300)
        with col2:
            st.markdown(f"**📋 {tt('ocr_method', L)}:** {result['method']}")
            if result['confidence']:
                st.markdown(f"**🎯 {tt('ocr_confidence', L)}:** {result['confidence']}%")
            st.markdown(f"**🏢 {tt('ocr_vendor', L)}:** {result['vendor'] or '—'}")
            st.markdown(f"**📅 {tt('ocr_date_lbl', L)}:** {result['date'] or '—'}")
            st.markdown(f"**💰 {tt('ocr_amount_lbl', L)}:** {result['amount']:,.2f}€" if result['amount'] else f"**💰 {tt('ocr_amount_lbl', L)}:** —")
        
        with st.expander("📝 " + tt("ocr_detected_text", L)):
            st.code(result['text'] if result['text'] else tt("ocr_no_text", L))
        
        # Quick add expense from invoice
        if result['amount'] > 0:
            st.markdown("---")
            st.markdown(f"### ➕ {tt('ocr_quick_add', L)}")
            with st.form("ocr_add"):
                suggested_cat = "Other"
                if "lebensmittel" in result['text'].lower() or "food" in result['text'].lower():
                    suggested_cat = "Food"
                elif "transport" in result['text'].lower() or "ticket" in result['text'].lower() or "bahn" in result['text'].lower():
                    suggested_cat = "Transport"
                elif "apotheke" in result['text'].lower() or "health" in result['text'].lower() or "arzt" in result['text'].lower():
                    suggested_cat = "Health"
                cat_opts = [f"{c['icon']} {c['name']}" for c in cats]
                ocr_cat = st.selectbox(tt("category", L), cat_opts, index=0)
                ocr_amt = st.number_input(tt("amount", L) + " (€)", value=float(result['amount']), format="%.2f")
                ocr_desc = st.text_input(tt("description", L), value=result['vendor'] or tt("ocr_uploaded_cap", L))
                ocr_date = st.date_input(tt("date", L), value=datetime.now())
                if st.form_submit_button(f"✅ {tt('add_expense', L)}", use_container_width=True):
                    cat_name = ocr_cat.split(" ", 1)[1]
                    c = get_db()
                    c.execute("INSERT INTO expenses(company_id,amount,category,description,date,created_by) VALUES(?,?,?,?,?,?)",
                             (CID, ocr_amt, cat_name, ocr_desc, ocr_date.strftime("%Y-%m-%d"), user["id"]))
                    c.commit()
                    log_activity(CID, user["id"], user["username"], "add_expense_ocr", f"{ocr_amt}€ {cat_name}")
                    c.close()
                    st.success("✅ " + tt("ocr_saved", L)); st.rerun()
        
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
    
    # ─── Activity Log (superadmin + admin) ───
    if user["role"] in ("superadmin", "admin"):
        with st.expander(f"📜 {tt('activity_log', L)}"):
            c_log = get_db()
            logs = c_log.execute("SELECT username, action, detail, created_at FROM activity_log WHERE company_id=? ORDER BY id DESC LIMIT 50", (CID,)).fetchall()
            c_log.close()
            if logs:
                log_df = pd.DataFrame([{"user": r["username"], "action": r["action"], "detail": r["detail"], "when": r["created_at"]} for r in logs])
                st.dataframe(log_df, width="stretch", hide_index=True)
            else:
                st.info("📭 " + tt("no_data", L))
    
    # ─── Backup (superadmin) ───
    if user["role"] in ("superadmin", "admin"):
        with st.expander(f"💾 {tt('backup', L)}"):
            st.caption(tt("backup_hint", L))
            import subprocess as _sub
            if st.button(f"🔄 {tt('do_backup', L)}"):
                r = subprocess.run([sys.executable, "backup.py"], capture_output=True, text=True)
                if r.returncode == 0:
                    st.success(r.stdout.strip().splitlines()[-1])
                else:
                    st.error(r.stderr or r.stdout or "Backup failed")
    
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
        if st.button("🔑 + " + tt("api_new_key", L)):
            from api import create_api_key
            import secrets
            new_key = secrets.token_hex(32)
            c = get_db(); c.execute("INSERT INTO api_keys(company_id, key) VALUES(?,?)", (CID, new_key)); c.commit(); c.close()
            st.code(new_key, language="text")
            st.success(tt("api_key_created", L))

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
        st.info(tt("api_no_key", L))
    
    with st.expander("📖 " + tt("api_docs", L)):
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
        companies = c.execute("SELECT id, name, slug, currency, brand_color, created_at FROM companies").fetchall()
        c.close()
        st.markdown(f"**{len(companies)} {tt('companies_count', L)}**")
        for comp in companies:
            with st.expander(f"🏢 **{comp['name']}** ({comp['slug']}) — {comp['currency']}"):
                # Brand color picker
                bc = st.color_picker(tt("brand_color", L), value=comp['brand_color'] or '#4e8cff', key=f"bc_{comp['id']}")
                if st.button("💾 " + tt("save_color", L), key=f"bcs_{comp['id']}"):
                    c2 = get_db(); c2.execute("UPDATE companies SET brand_color=? WHERE id=?", (bc, comp['id'])); c2.commit(); c2.close()
                    st.success("✅"); st.rerun()
                st.markdown("---")
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
                        if st.button("✏️", key=f"eu{comp['id']}_{u['id']}", help=tt("edit", L)):
                            st.session_state[f"edit_user_{u['id']}"] = True
                        if u['username'] != 'admin':
                            if st.button("🗑️", key=f"cu{comp['id']}_{u['id']}", help=tt("delete", L)):
                                c2 = get_db(); c2.execute("DELETE FROM users WHERE id=? AND username!='admin'", (u['id'],)); c2.commit(); c2.close(); st.rerun()
                    
                    # Edit form (shown when ✏️ clicked)
                    if st.session_state.get(f"edit_user_{u['id']}"):
                        with st.form(f"edit_form_{u['id']}"):
                            st.markdown(f"**✏️ {tt('edit', L)} `{u['username']}`**")
                            ec = st.columns(3)
                            with ec[0]:
                                new_pass = st.text_input(tt("new_pass", L), type="password", key=f"ep{u['id']}")
                            with ec[1]:
                                new_name = st.text_input(tt("display_name", L), value=u['display_name'] or "", key=f"en{u['id']}")
                            with ec[2]:
                                new_role = st.selectbox(tt("role", L), ["user", "admin"], index=0 if u['role']=='user' else 1, key=f"er{u['id']}")
                            ec2 = st.columns(2)
                            with ec2[0]:
                                if st.form_submit_button("💾 " + tt("save", L)):
                                    c2 = get_db()
                                    if new_pass:
                                        c2.execute("UPDATE users SET password_hash=?, raw_password=?, display_name=?, role=? WHERE id=?",
                                            (hashlib.sha256(new_pass.encode()).hexdigest(), new_pass, new_name, new_role, u['id']))
                                    else:
                                        c2.execute("UPDATE users SET display_name=?, role=? WHERE id=?",
                                            (new_name, new_role, u['id']))
                                    c2.commit(); c2.close()
                                    st.session_state[f"edit_user_{u['id']}"] = False
                                    st.success("✅"); st.rerun()
                            with ec2[1]:
                                if st.form_submit_button("❌"):
                                    st.session_state[f"edit_user_{u['id']}"] = False
                                    st.rerun()
                
                # Add user form
                with st.form(f"add_user_{comp['id']}"):
                    st.markdown(f"**➕ {tt('add_user', L)}**")
                    cols = st.columns(3)
                    with cols[0]:
                        nu = st.text_input(tt("username", L), key=f"nu{comp['id']}")
                    with cols[1]:
                        np = st.text_input(tt("password", L), type="password", key=f"np{comp['id']}")
                    with cols[2]:
                        nd = st.text_input(tt("display_name", L), key=f"nd{comp['id']}")
                    nr = st.selectbox(tt("role", L), ["user", "admin"], key=f"nr{comp['id']}")
                    if st.form_submit_button("➕ " + tt("add", L), use_container_width=True):
                        c2 = get_db()
                        try:
                            c2.execute("INSERT INTO users(username,password_hash,raw_password,role,company_id,display_name) VALUES(?,?,?,?,?,?)",
                                (nu, hashlib.sha256(np.encode()).hexdigest(), np, nr, comp['id'], nd))
                            c2.commit(); st.success(f"✅ {nu}"); st.rerun()
                        except Exception as e: st.error(str(e))
                        c2.close()
        st.markdown("---")
        st.markdown(f"### ➕ {tt('new_company', L)}")
        with st.form("cf"):
            nm = st.text_input(tt("company_name", L))
            sl = st.text_input(tt("slug", L))
            cr = st.selectbox(tt("currency", L), ["EUR", "USD", "GBP"])
            if st.form_submit_button("➕ " + tt("add", L), use_container_width=True):
                c2 = get_db()
                try:
                    c2.execute("INSERT INTO companies(name,slug,currency) VALUES(?,?,?)", (nm, sl, cr))
                    c2.commit(); st.success(f"✅ {nm}"); st.rerun()
                except Exception as e: st.error(str(e))
                c2.close()
