"""
ExFlow Enterprise — PDF Report Generator (HTML-based, RTL-safe)
==================================================================
"""
import os, sys

# Keep only the project venv in path (remove Hermes)
VENV_SITE = "/Users/samasarkhanzadeh/MyHub/projects/exflow-enterprise/venv/lib/python3.14/site-packages"
sys.path = [p for p in sys.path if 'hermes' not in p.lower()]
if VENV_SITE not in sys.path:
    sys.path.insert(0, VENV_SITE)

from datetime import date
from fpdf import FPDF
import arabic_reshaper

REPORT_DIR = os.path.join(os.path.dirname(__file__), "reports")
os.makedirs(REPORT_DIR, exist_ok=True)
VAZIR_PATH = os.path.expanduser("~/.fonts/Vazirmatn-Regular.ttf")

PDF_T = {
    "category": {"fa": "دسته", "de": "Kategorie", "en": "Category"},
    "amount_eur": {"fa": "مبلغ (€)", "de": "Betrag (€)", "en": "Amount (EUR)"},
    "pct": {"fa": "٪", "de": "%", "en": "%"},
    "total": {"fa": "مجموع", "de": "Gesamt", "en": "Total"},
    "source": {"fa": "منبع", "de": "Quelle", "en": "Source"},
    "date_h": {"fa": "تاریخ", "de": "Datum", "en": "Date"},
    "budget": {"fa": "بودجه", "de": "Budget", "en": "Budget"},
    "spent": {"fa": "مصرف", "de": "Ausgegeben", "en": "Spent"},
    "remaining": {"fa": "باقی مانده", "de": "Übrig", "en": "Remaining"},
    "income": {"fa": "درآمد", "de": "Einkommen", "en": "Income"},
    "expenses": {"fa": "هزینه‌ها", "de": "Ausgaben", "en": "Expenses"},
    "balance": {"fa": "مانده", "de": "Guthaben", "en": "Balance"},
    "breakdown": {"fa": "تفکیک هزینه‌ها", "de": "Ausgabenaufschlüsselung", "en": "Expense Breakdown"},
    "income_list": {"fa": "فهرست درآمدها", "de": "Einkommensliste", "en": "Income List"},
    "budget_vs": {"fa": "بودجه در برابر واقعیت", "de": "Budget vs. Ist", "en": "Budget vs Actual"},
    "no_exp": {"fa": "هزینه‌ای ثبت نشده", "de": "Keine Ausgaben", "en": "No expenses recording"},
    "no_inc": {"fa": "درآمدی ثبت نشده", "de": "Kein Einkommen", "en": "No income recording"},
}

def pt(key, lang):
    d = PDF_T.get(key, {})
    return d.get(lang, d.get("en", f"?{key}?"))

# ─── HTML report (RTL-safe, for Persian) ───
def generate_html(company_name, month, expenses_data, income_data, budget_data,
                   cat_translations, lang="fa"):
    """Generate HTML report (handles RTL natively via browser)."""
    total_exp = sum(e["amount"] for e in expenses_data) if expenses_data else 0
    total_inc = sum(i["amount"] for i in income_data) if income_data else 0
    balance = total_inc - total_exp
    is_rtl = lang == "fa"
    dir_attr = "rtl" if is_rtl else "ltr"
    
    # Expense breakdown rows
    exp_rows = ""
    if expenses_data:
        ct = {}
        for e in expenses_data:
            n = cat_translations.get(e["category"], {}).get(lang, e["category"])
            ct[n] = ct.get(n, 0) + e["amount"]
        for n, a in sorted(ct.items(), key=lambda x: -x[1]):
            p = (a / total_exp * 100) if total_exp else 0
            exp_rows += f"<tr><td>{n}</td><td style='text-align:right'>{a:,.2f}€</td><td style='text-align:right'>{p:.1f}%</td></tr>"
        exp_rows += f"<tr style='font-weight:bold;background:#e8f5e9'><td>{pt('total',lang)}</td><td style='text-align:right'>{total_exp:,.2f}€</td><td style='text-align:right'>100%</td></tr>"
    
    inc_rows = ""
    if income_data:
        for i in income_data:
            inc_rows += f"<tr><td>{i['source']}</td><td style='text-align:right'>{i['amount']:,.2f}€</td><td>{i['date']}</td></tr>"
        inc_rows += f"<tr style='font-weight:bold;background:#e8f5e9'><td>{pt('total',lang)}</td><td style='text-align:right'>{total_inc:,.2f}€</td><td></td></tr>"
    
    bud_rows = ""
    if budget_data:
        for b in budget_data:
            n = cat_translations.get(b["category"], {}).get(lang, b["category"])
            spent = sum(e["amount"] for e in expenses_data if e["category"] == b["category"]) or 0
            rem = b["amount"] - spent
            rc = "green" if rem >= 0 else "red"
            bud_rows += f"<tr><td>{n}</td><td style='text-align:right'>{b['amount']:,.2f}€</td><td style='text-align:right'>{spent:,.2f}€</td><td style='text-align:right;color:{rc}'>{rem:+,.2f}€</td></tr>"
    
    font_family = "'Vazirmatn', 'Segoe UI', Tahoma, sans-serif" if is_rtl else "'Segoe UI', 'Helvetica', sans-serif"
    
    html = f"""<!DOCTYPE html>
<html dir="{dir_attr}">
<head><meta charset="utf-8"><title>{company_name} - {month}</title>
<style>
    body {{ font-family: {font_family}; font-size: 11pt; color: #333; padding: 20px; max-width: 800px; margin: auto; }}
    h1 {{ font-size: 20pt; color: #1a1a2e; border-bottom: 2px solid #1a1a2e; padding-bottom: 5px; }}
    .sub {{ font-size: 10pt; color: #666; margin-bottom: 15px; }}
    .summary {{ background: #f0f4ff; padding: 12px 16px; border-radius: 8px; margin: 10px 0; line-height: 1.8; }}
    h2 {{ font-size: 14pt; color: #1a1a2e; margin: 20px 0 8px; }}
    table {{ width: 100%; border-collapse: collapse; margin-bottom: 15px; font-size: 10pt; }}
    th {{ background: #1a1a2e; color: white; padding: 7px 10px; }}
    th.g {{ background: #1b5e20; }}
    th.o {{ background: #e65100; }}
    td {{ padding: 5px 8px; border-bottom: 1px solid #ddd; }}
    tr:nth-child(even) {{ background: #f8f8f8; }}
    .footer {{ text-align: center; font-size: 7pt; color: #999; margin-top: 30px; border-top: 1px solid #eee; padding-top: 10px; }}
    .note {{ background: #fff3e0; padding: 8px 12px; border-radius: 6px; font-size: 9pt; color: #e65100; margin-bottom: 10px; }}
</style></head>
<body>
    <h1>{company_name}</h1>
    <div class="sub">{month} | ExFlow Enterprise</div>
    
    <div class="summary">
        <b>{pt('income',lang)}:</b> {total_inc:,.2f} EUR &nbsp;|&nbsp;
        <b>{pt('expenses',lang)}:</b> {total_exp:,.2f} EUR &nbsp;|&nbsp;
        <b>{pt('balance',lang)}:</b> {balance:+,.2f} EUR
    </div>
    
    <h2>{pt('breakdown',lang)}</h2>
    <table><tr><th>{pt('category',lang)}</th><th style='text-align:right'>{pt('amount_eur',lang)}</th><th style='text-align:right'>{pt('pct',lang)}</th></tr>{exp_rows}</table>
    
    <h2>{pt('income_list',lang)}</h2>
    <table><tr><th>{pt('source',lang)}</th><th style='text-align:right'>{pt('amount_eur',lang)}</th><th>{pt('date_h',lang)}</th></tr>{inc_rows}</table>
    
    <h2>{pt('budget_vs',lang)}</h2>
    <table><tr><th>{pt('category',lang)}</th><th style='text-align:right'>{pt('budget',lang)}</th><th style='text-align:right'>{pt('spent',lang)}</th><th style='text-align:right'>{pt('remaining',lang)}</th></tr>{bud_rows}</table>
    
    <div class="footer">ExFlow Enterprise &nbsp;|&nbsp; {date.today().isoformat()}</div>
</body></html>"""
    return html

# ─── PDF fallback (for DE/EN only, FA uses English in PDF) ───
def generate_report(company_name, month, expenses_data, income_data, budget_data,
                     cat_translations, lang="fa"):
    """Generate HTML report for ALL languages (consistent, RTL-safe for FA, 
    clean tables for DE/EN). Returns .html file path."""
    html = generate_html(company_name, month, expenses_data, income_data,
                         budget_data, cat_translations, lang)
    fp = os.path.join(REPORT_DIR, f"{company_name.replace(' ','_')}_{month}_report.html")
    with open(fp, "w", encoding="utf-8") as f:
        f.write(html)
    return fp


def generate_html_report(company_name, month, expenses_data, income_data, budget_data,
                          cat_translations, lang="fa"):
    """Public interface: returns HTML string for in-browser display."""
    return generate_html(company_name, month, expenses_data, income_data, budget_data,
                         cat_translations, lang)


if __name__ == "__main__":
    td = [{"category":"Food","amount":95.0},{"category":"Transport","amount":71.0}]
    ti = [{"source":"Revenue","amount":1500.0,"date":"2026-07-01"}]
    tb = [{"category":"Food","amount":400.0}]
    ct = {"Food":{"fa":"خوراک","de":"Lebensmittel","en":"Food"},"Transport":{"fa":"حمل و نقل","de":"Verkehr","en":"Transport"}}
    for lang in ["fa","de","en"]:
        fp = generate_report("Demo","2026-07",td,ti,tb,ct,lang)
        print(f"✅ {lang}: {fp}")
