"""
ExFlow Enterprise — Smart Assistant (rule-based AI insights)
=============================================================
Gives the app an "AI" feel without needing an external LLM API:
  - auto-categorize a transaction description
  - monthly insights (spending trends, budget status, anomalies)
  - smart budget suggestions based on history
All rules are deterministic, explainable, and offline.
"""
import os
import re
from datetime import datetime

# ── Auto-categorization: keyword -> category ──
CATEGORY_KEYWORDS = {
    "Food": ["lebensmittel", "food", "restaurant", "cafe", "café", "supermarkt", "market", "essen",
             "mittagessen", "bäckerei", "pizza", "grocer", "خوراک", "غذا", "رستوران", "سوپرمارکت"],
    "Transport": ["transport", "ticket", "bahn", "bus", "taxi", "uber", "fuel", "benzin", "gas",
                  "parking", "حمل", "بنزین", "تاکسی", "اتوبوس", "قطار"],
    "Bills": ["bill", "strom", "electric", "wasser", "miete", "internet", "phone", "rechnung",
              "قبوض", "برق", "گاز", "اجاره", "اینترنت"],
    "Health": ["apotheke", "pharmacy", "health", "arzt", "doctor", "kranken", "medizin",
               "سلامت", "دارو", "پزشک", "بیمارستان"],
    "Entertainment": ["kino", "cinema", "entertainment", "netflix", "spotify", "spiel", "game",
                      "سرگرمی", "سینما"],
    "Shopping": ["shopping", "kleidung", "clothes", "amazon", "schuhe", "خرید", "لباس"],
    "Education": ["schule", "school", "kurs", "university", "buch", "book", "آموزش", "کتاب", "دانشگاه"],
    "Housing": ["wohnung", "housing", "miete", "apartment", "خانه", "مسکن"],
}


def suggest_category(description: str, fallback="Other"):
    """Guess the category from free-text description (en/de/fa keywords)."""
    if not description:
        return fallback
    d = description.lower()
    best = fallback
    best_score = 0
    for cat, kws in CATEGORY_KEYWORDS.items():
        score = sum(1 for k in kws if k in d)
        if score > best_score:
            best, best_score = cat, score
    return best


def monthly_insights(company_id, lang="fa", month=None):
    """
    Compute a few human-readable insights for the current month.
    Returns list of dicts: {icon, text} in the requested language.
    """
    from db import get_db

    c = get_db()
    if month is None:
        month = datetime.now().strftime("%Y-%m")

    # totals
    ex_row = c.execute("SELECT COALESCE(SUM(amount),0) FROM expenses WHERE company_id=? AND date LIKE ?",
                       (company_id, month + "%")).fetchone()[0]
    in_row = c.execute("SELECT COALESCE(SUM(amount),0) FROM income WHERE company_id=? AND date LIKE ?",
                       (company_id, month + "%")).fetchone()[0]

    # previous month
    ym = datetime.strptime(month, "%Y-%m")
    if ym.month == 1:
        prev = f"{ym.year-1}-12"
    else:
        prev = f"{ym.year}-{ym.month-1:02d}"
    prev_ex = c.execute("SELECT COALESCE(SUM(amount),0) FROM expenses WHERE company_id=? AND date LIKE ?",
                        (company_id, prev + "%")).fetchone()[0]

    # top category
    top = c.execute(
        "SELECT category, SUM(amount) as s FROM expenses WHERE company_id=? AND date LIKE ? GROUP BY category ORDER BY s DESC LIMIT 1",
        (company_id, month + "%")).fetchone()

    top_cat_text = f"{top['category']} ({top['s']:,.0f}€)" if top else None

    # budget status
    over_budget = []
    for b in c.execute("SELECT category, amount FROM budget WHERE company_id=? AND month=?", (company_id, month)).fetchall():
        used = c.execute("SELECT COALESCE(SUM(amount),0) FROM expenses WHERE company_id=? AND date LIKE ? AND category=?",
                         (company_id, month + "%", b["category"])).fetchone()[0]
        if b["amount"] and used > b["amount"]:
            over_budget.append(b["category"])

    c.close()

    texts = {
        "fa": {
            "spend": f"این ماه تا حالا {ex_row:,.0f}€ خرج شده",
            "income": f"درآمد این ماه: {in_row:,.0f}€",
            "balance": f"مانده: {in_row-ex_row:+,.0f}€",
            "vs_prev_up": f"هزینه‌ها نسبت به ماه قبل {((ex_row-prev_ex)/prev_ex*100 if prev_ex else 0):.0f}٪ بیشتر شده — مراقب باش!",
            "vs_prev_down": f"هزینه‌ها نسبت به ماه قبل {((prev_ex-ex_row)/prev_ex*100 if prev_ex else 0):.0f}٪ کمتر شده — آفرین!",
            "top_cat": f"بیشترین هزینه: {top_cat_text}",
            "no_spend": "هنوز هزینه‌ای این ماه ثبت نشده",
            "over": "⚠️ از بودجه این دسته‌ها رد شدی: {}",
        },
        "de": {
            "spend": f"Diesen Monat bisher {ex_row:,.0f}€ ausgegeben",
            "income": f"Einkommen diesen Monat: {in_row:,.0f}€",
            "balance": f"Guthaben: {in_row-ex_row:+,.0f}€",
            "vs_prev_up": f"Ausgaben {((ex_row-prev_ex)/prev_ex*100 if prev_ex else 0):.0f}% höher als letzten Monat — Achtung!",
            "vs_prev_down": f"Ausgaben {((prev_ex-ex_row)/prev_ex*100 if prev_ex else 0):.0f}% niedriger als letzten Monat — gut!",
            "top_cat": f"Höchste Ausgabe: {top_cat_text}",
            "no_spend": "Noch keine Ausgaben diesen Monat",
            "over": "⚠️ Budget überschritten in: {}",
        },
        "en": {
            "spend": f"Spent {ex_row:,.0f}€ so far this month",
            "income": f"Income this month: {in_row:,.0f}€",
            "balance": f"Balance: {in_row-ex_row:+,.0f}€",
            "vs_prev_up": f"Spending is {((ex_row-prev_ex)/prev_ex*100 if prev_ex else 0):.0f}% higher than last month — watch out!",
            "vs_prev_down": f"Spending is {((prev_ex-ex_row)/prev_ex*100 if prev_ex else 0):.0f}% lower than last month — nice!",
            "top_cat": f"Top category: {top_cat_text}",
            "no_spend": "No expenses recorded this month yet",
            "over": "⚠️ You exceeded the budget for: {}",
        },
    }
    t = texts.get(lang, texts["en"])
    insights = []
    if ex_row == 0:
        insights.append({"icon": "📭", "text": t["no_spend"]})
        return insights
    insights.append({"icon": "💸", "text": t["spend"]})
    if in_row:
        insights.append({"icon": "💰", "text": t["income"]})
        insights.append({"icon": "⚖️", "text": t["balance"]})
    if prev_ex and prev_ex != 0:
        if ex_row > prev_ex:
            insights.append({"icon": "📈", "text": t["vs_prev_up"]})
        else:
            insights.append({"icon": "📉", "text": t["vs_prev_down"]})
    if top:
        insights.append({"icon": "🏆", "text": t["top_cat"]})
    if over_budget:
        insights.append({"icon": "🚨", "text": t["over"].format(", ".join(over_budget))})
    return insights


def suggest_budget(company_id, category, month=None):
    """Suggest a budget = 110% of last month's spend in that category."""
    from db import get_db
    c = get_db()
    if month is None:
        month = datetime.now().strftime("%Y-%m")
    ym = datetime.strptime(month, "%Y-%m")
    if ym.month == 1:
        prev = f"{ym.year-1}-12"
    else:
        prev = f"{ym.year}-{ym.month-1:02d}"
    spent = c.execute("SELECT COALESCE(SUM(amount),0) FROM expenses WHERE company_id=? AND date LIKE ? AND category=?",
                      (company_id, prev + "%", category)).fetchone()[0]
    c.close()
    if spent > 0:
        return round(spent * 1.1, 2), spent
    return None, spent


def forecast_next_month(company_id, lang="en"):
    """
    Estimate next month's expenses as the average of the last 3 months
    (fallback to this month if fewer). Returns a human-readable string.
    """
    from db import get_db
    c = get_db()
    now = datetime.now()
    totals = []
    ym = now
    for _ in range(3):
        m = f"{ym.year}-{ym.month:02d}"
        tot = c.execute("SELECT COALESCE(SUM(amount),0) FROM expenses WHERE company_id=? AND date LIKE ?",
                        (company_id, m + "%")).fetchone()[0]
        totals.append(tot)
        # previous month
        if ym.month == 1:
            ym = ym.replace(year=ym.year - 1, month=12)
        else:
            ym = ym.replace(month=ym.month - 1)
    c.close()
    recent = [t for t in totals if t > 0]
    avg = sum(recent) / len(recent) if recent else 0.0
    nxt_ym = (datetime(now.year, now.month, 1).replace(month=now.month + 1)
              if now.month < 12 else datetime(now.year + 1, 1, 1))
    texts = {
        "en": f"Based on the last {len(recent)} months, next month's spending is estimated around {avg:,.0f}€.",
        "de": f"Basierend auf den letzten {len(recent)} Monaten werden die Ausgaben nächsten Monat auf etwa {avg:,.0f}€ geschätzt.",
        "fa": f"بر اساس {len(recent)} ماه گذشته، هزینه ماه آینده حدود {avg:,.0f}€ تخمین زده می‌شود.",
    }
    return texts.get(lang, texts["en"])


def chat(company_id, question, lang="en"):
    """
    Lightweight rule-based 'talk to your data' assistant.
    Understands a few intents dynamically; returns a helpful answer.
    """
    q = (question or "").lower()
    from db import get_db
    c = get_db()
    now = datetime.now()
    m = f"{now.year}-{now.month:02d}"
    ex = c.execute("SELECT COALESCE(SUM(amount),0) FROM expenses WHERE company_id=? AND date LIKE ?", (company_id, m + "%")).fetchone()[0]
    inc = c.execute("SELECT COALESCE(SUM(amount),0) FROM income WHERE company_id=? AND date LIKE ?", (company_id, m + "%")).fetchone()[0]
    c.close()

    t = {
        "en": {
            "spent": f"This month you've spent {ex:,.0f}€.",
            "income": f"This month's income is {inc:,.0f}€.",
            "balance": f"Current balance: {inc-ex:+,.0f}€.",
            "hello": "Hi! I can tell you about this month's spending, income, or balance. Try asking: 'how much did I spend?'",
            "unknown": "I can help with questions about this month's spending, income, and balance.",
        },
        "de": {
            "spent": f"Diesen Monat haben Sie {ex:,.0f}€ ausgegeben.",
            "income": f"Das Einkommen diesen Monat beträgt {inc:,.0f}€.",
            "balance": f"Aktuelles Guthaben: {inc-ex:+,.0f}€.",
            "hello": "Hallo! Ich kann über Ausgaben, Einkommen oder Guthaben Auskunft geben.",
            "unknown": "Ich kann bei Fragen zu Ausgaben, Einkommen und Guthaben helfen.",
        },
        "fa": {
            "spent": f"این ماه {ex:,.0f}€ خرج کرده‌ای.",
            "income": f"درآمد این ماه {inc:,.0f}€ است.",
            "balance": f"مانده فعلی: {inc-ex:+,.0f}€.",
            "hello": "سلام! می‌تونم درباره هزینه، درآمد یا مانده این ماه کمک کنم.",
            "unknown": "می‌تونم درباره هزینه، درآمد و مانده این ماه کمک کنم.",
        },
    }
    x = t.get(lang, t["en"])
    if any(w in q for w in ["spend", "ausgegeben", "خرج", "خرج کرد", "cost", "costs"]):
        return x["spent"]
    if any(w in q for w in ["income", "einkommen", "درآمد", "earn", "earned"]):
        return x["income"]
    if any(w in q for w in ["balance", "guthaben", "مانده", "konto"]):
        return x["balance"]
    if any(w in q for w in ["hi", "hello", "hey", "سلام", "hallo"]):
        return x["hello"]
    return x["unknown"]
