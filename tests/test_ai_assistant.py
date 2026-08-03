"""AI Assistant tests — auto-categorization + monthly insights."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from db import init_db, get_db
from ai_assistant import suggest_category, monthly_insights


def setup_module():
    init_db()


def test_suggest_food():
    assert suggest_category("Lebensmittel Einkauf") == "Food"


def test_suggest_transport():
    assert suggest_category("Bahn Ticket nach Berlin") == "Transport"


def test_suggest_health():
    assert suggest_category("Apotheke Medikamente") == "Health"


def test_suggest_entertainment():
    assert suggest_category("Kino am Abend") == "Entertainment"


def test_suggest_bills():
    assert suggest_category("Stromrechnung Juli") == "Bills"


def test_suggest_empty_fallback():
    assert suggest_category("") == "Other"


def test_insights_return_list():
    ins = monthly_insights(1, lang="en", month="2026-07")
    assert isinstance(ins, list)
    assert len(ins) > 0
    assert all("text" in i and "icon" in i for i in ins)


def test_insights_three_langs():
    for lang in ("fa", "de", "en"):
        ins = monthly_insights(1, lang=lang, month="2026-07")
        assert isinstance(ins, list)
        assert all(i["text"] for i in ins), f"empty text in {lang}"
