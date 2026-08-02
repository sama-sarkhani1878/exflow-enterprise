"""Importer tests — CSV parsing, German amount formats, validation."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from db import init_db, get_db
from importer import parse_amount, parse_date, import_file


def setup_module():
    init_db()


def test_parse_decimal_comma():
    assert parse_amount("5,00") == 5.0


def test_parse_german_thousands():
    assert parse_amount("1.234,56") == 1234.56


def test_parse_us_thousands():
    assert parse_amount("1,234.56") == 1234.56


def test_parse_negative():
    assert parse_amount("-5") == -5.0


def test_parse_bad():
    assert parse_amount("abc") is None


def test_parse_date_german():
    assert parse_date("21.07.2026") == "2026-07-21"


def test_parse_date_iso():
    assert parse_date("2026-07-20") == "2026-07-20"


def test_import_csv_inserts():
    csv_bytes = b"amount,category,description,date\n25.50,Food,Mittagessen,2026-08-01\n12,00,Transport,Bahn,21.07.2026\n-5,Food,bad,2026-07-20\n"
    res = import_file(csv_bytes, "t.csv", 1, 1)
    assert res["ok"] is True
    assert res["inserted"] == 2
    assert res["skipped"] == 1  # negative amount rejected


def test_import_unsupported_type():
    res = import_file(b"x", "t.txt", 1, 1)
    assert res["ok"] is False