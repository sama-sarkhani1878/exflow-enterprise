"""
ExFlow Enterprise — File Importer (CSV / Excel)
=================================================
Parse expense/income files from accountants or external sources.
Supports: .csv, .xlsx, .xls

Expected CSV columns (case-insensitive, flexible):
  - amount / betrag / مبلغ
  - category / kategorie / دسته
  - description / beschreibung / توضیح
  - date / datum / تاریخ  (YYYY-MM-DD or DD.MM.YYYY or DD/MM/YYYY)
  - type / art / نوع      (optional: expense | income)
"""
import os
import csv
import io
import re
from datetime import datetime

try:
    import pandas as pd
    HAS_PANDAS = True
except ImportError:
    HAS_PANDAS = False

# Column name synonyms -> canonical keys
COLUMN_MAP = {
    "amount": ["amount", "betrag", "summe", "sum", "مبلغ", "قیمت", "wert", "value"],
    "category": ["category", "kategorie", "categorie", "cat", "دسته", "دسته‌بندی", "kategorie"],
    "description": ["description", "beschreibung", "note", "notes", "text", "توضیح", "شرح", "kommentar", "bemerkung"],
    "date": ["date", "datum", "تاریخ", "zeitpunkt", "booked_at"],
    "type": ["type", "art", "نوع", "typ"],
    "source": ["source", "quelle", "منبع", "einnahme", "income"],
}


def _normalize_key(key: str) -> str:
    """Map a raw column name to canonical key."""
    k = key.strip().lower()
    for canon, synonyms in COLUMN_MAP.items():
        if k in [s.lower() for s in synonyms]:
            return canon
    return None


def parse_amount(value):
    """Parse '5,00' / '5.00' / '1.234,56' / '1,234.56' -> float."""
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    s = str(value).strip().replace("€", "").replace("EUR", "").replace(" ", "")
    if not s:
        return None
    # German style: 1.234,56
    if re.match(r"^-?\d{1,3}(\.\d{3})+(,\d+)?$", s):
        s = s.replace(".", "").replace(",", ".")
        try:
            return float(s)
        except ValueError:
            return None
    # German simple: 5,00
    if "," in s and "." not in s:
        s = s.replace(",", ".")
    # US style: 1,234.56
    elif "," in s and "." in s:
        # last separator is decimal
        if s.rfind(",") > s.rfind("."):
            s = s.replace(".", "").replace(",", ".")
        else:
            s = s.replace(",", "")
    try:
        return float(s)
    except ValueError:
        return None


def parse_date(value):
    """Parse common date formats -> 'YYYY-MM-DD' or None."""
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.strftime("%Y-%m-%d")
    s = str(value).strip()
    for fmt in ("%Y-%m-%d", "%d.%m.%Y", "%d/%m/%Y", "%Y/%m/%d", "%d-%m-%Y", "%Y.%m.%d"):
        try:
            return datetime.strptime(s, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    return None


def normalize_categories(row, existing_categories=None):
    """Map free-text category to a known category name if close."""
    cat = row.get("category", "").strip()
    if not cat:
        return "Other"
    if existing_categories:
        cat_lower = cat.lower()
        for known in existing_categories:
            if known.lower() == cat_lower or known.lower() in cat_lower or cat_lower in known.lower():
                return known
    # Fallback: capitalize first letter
    return cat[:1].upper() + cat[1:] if cat else "Other"


def parse_csv(content: bytes, filename: str):
    """Parse CSV content -> list of row dicts with canonical keys."""
    text = content.decode("utf-8-sig", errors="replace")
    reader = csv.DictReader(io.StringIO(text))
    if not reader.fieldnames:
        return []
    col_map = {}
    for raw in reader.fieldnames:
        canon = _normalize_key(raw)
        if canon:
            col_map[raw] = canon
    rows = []
    for r in reader:
        row = {}
        for raw, canon in col_map.items():
            row[canon] = r.get(raw, "")
        if "amount" in row and row["amount"] not in (None, ""):
            rows.append(row)
    return rows


def parse_excel(content: bytes):
    """Parse Excel content -> list of row dicts."""
    if not HAS_PANDAS:
        return []
    df = pd.read_excel(io.BytesIO(content))
    col_map = {}
    for raw in df.columns:
        canon = _normalize_key(str(raw))
        if canon:
            col_map[raw] = canon
    rows = []
    for _, r in df.iterrows():
        row = {}
        for raw, canon in col_map.items():
            row[canon] = r[raw]
        if "amount" in row and row["amount"] not in (None, "", float("nan")):
            rows.append(row)
    return rows


def import_rows(rows, company_id, created_by=1, default_type="expense"):
    """
    Insert parsed rows into DB.
    Returns (inserted, skipped, errors).
    """
    from db import get_db

    inserted = 0
    skipped = 0
    errors = []

    c = get_db()
    existing_cats = [r[0] for r in c.execute(
        "SELECT name FROM categories WHERE company_id=?", (company_id,)).fetchall()]

    for i, row in enumerate(rows):
        amount = parse_amount(row.get("amount"))
        if amount is None or amount <= 0:
            skipped += 1
            errors.append(f"Row {i+1}: invalid amount '{row.get('amount')}'")
            continue

        date_str = parse_date(row.get("date")) or datetime.now().strftime("%Y-%m-%d")
        category = normalize_categories(row, existing_cats)
        description = str(row.get("description", "") or "").strip()

        row_type = str(row.get("type", "") or "").strip().lower()
        if row_type in ("income", "einnahme", "درآمد", "revenue"):
            source = str(row.get("source", "") or "").strip() or "Import"
            c.execute(
                "INSERT INTO income(company_id, amount, source, month, date) VALUES(?,?,?,?,?)",
                (company_id, amount, source, date_str[:7], date_str))
        else:
            c.execute(
                "INSERT INTO expenses(company_id, amount, category, description, date, created_by) VALUES(?,?,?,?,?,?)",
                (company_id, amount, category, description, date_str, created_by))
        inserted += 1

    c.commit()
    c.close()
    return inserted, skipped, errors


def import_file(content: bytes, filename: str, company_id: int, created_by: int = 1):
    """Main entry: detect file type, parse, import. Returns summary dict."""
    ext = os.path.splitext(filename)[1].lower()
    if ext == ".csv":
        rows = parse_csv(content, filename)
    elif ext in (".xlsx", ".xls"):
        rows = parse_excel(content)
    else:
        return {"ok": False, "error": f"Unsupported file type: {ext}"}

    if not rows:
        return {"ok": False, "error": "No valid rows found (need 'amount' column)"}

    inserted, skipped, errors = import_rows(rows, company_id, created_by)
    return {
        "ok": True,
        "total": len(rows),
        "inserted": inserted,
        "skipped": skipped,
        "errors": errors[:10],
    }
