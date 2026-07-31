"""
ExFlow Enterprise — REST API
==============================
FastAPI-based REST API for external integrations.
Run: python3 api.py
"""
import os, sys
sys.path = [p for p in sys.path if 'hermes' not in p.lower()]

import sqlite3, hashlib, secrets, json
from datetime import datetime, date
from typing import Optional
from fastapi import FastAPI, HTTPException, Header, Query, Depends
from pydantic import BaseModel

app = FastAPI(title="ExFlow Enterprise API", version="1.0.0")

DB_PATH = os.path.join(os.path.dirname(__file__), "data", "exflow.db")

# Single shared connection for API (SQLite concurrent write workaround)
_conn = None
def get_db():
    global _conn
    if _conn is None:
        _conn = sqlite3.connect(DB_PATH, timeout=60, check_same_thread=False)
        _conn.row_factory = sqlite3.Row
        _conn.execute("PRAGMA journal_mode=WAL")
        _conn.execute("PRAGMA busy_timeout=60000")
        _conn.execute("PRAGMA foreign_keys=ON")
    return _conn

# ─── Auth ───
def verify_api_key(api_key: str):
    """Verify an API key and return company_id."""
    c = get_db()
    row = c.execute("SELECT company_id, name FROM api_keys k JOIN companies c ON k.company_id=c.id WHERE k.key=?", (api_key,)).fetchone()
    if not row:
        return None
    return {"company_id": row["company_id"], "company_name": row["name"]}

# ─── Models ───
class ExpenseCreate(BaseModel):
    amount: float
    category: str
    description: str = ""
    date: str  # YYYY-MM-DD

class IncomeCreate(BaseModel):
    amount: float
    source: str
    date: str  # YYYY-MM-DD

class BudgetCreate(BaseModel):
    month: str  # YYYY-MM
    category: str
    amount: float

# ─── API Key auth dependency ───
async def check_auth(x_api_key: str = Header(...)):
    company = verify_api_key(x_api_key)
    if not company:
        raise HTTPException(status_code=401, detail="Invalid API key")
    return company

# ─── Endpoints ───

@app.get("/")
async def root():
    return {"name": "ExFlow Enterprise API", "version": "1.0.0", "status": "running"}

@app.post("/expenses")
async def add_expense(expense: ExpenseCreate, company: dict = Depends(check_auth)):
    """Add a new expense for the authenticated company."""
    if expense.amount <= 0:
        raise HTTPException(status_code=400, detail="Amount must be positive")
    try:
        dt = datetime.strptime(expense.date, "%Y-%m-%d")
    except ValueError:
        raise HTTPException(status_code=400, detail="Date must be YYYY-MM-DD")
    
    c = get_db()
    c_cursor = c.execute("INSERT INTO expenses(company_id,amount,category,description,date,created_by) VALUES(?,?,?,?,?,?)",
              (company["company_id"], expense.amount, expense.category, expense.description, expense.date, 1))
    c.commit()
    expense_id = c_cursor.lastrowid
    return {"status": "ok", "id": expense_id, "amount": expense.amount, "category": expense.category}

@app.get("/expenses")
async def list_expenses(month: Optional[str] = Query(None), company: dict = Depends(check_auth)):
    """List expenses. Optionally filter by month (YYYY-MM)."""
    c = get_db()
    if month:
        rows = c.execute("SELECT * FROM expenses WHERE company_id=? AND substr(date,1,7)=? ORDER BY date DESC",
                        (company["company_id"], month)).fetchall()
    else:
        rows = c.execute("SELECT * FROM expenses WHERE company_id=? ORDER BY date DESC",
                        (company["company_id"],)).fetchall()
    return [dict(r) for r in rows]

@app.delete("/expenses/{expense_id}")
async def delete_expense(expense_id: int, company: dict = Depends(check_auth)):
    """Delete an expense by ID."""
    c = get_db()
    existing = c.execute("SELECT id FROM expenses WHERE id=? AND company_id=?", (expense_id, company["company_id"])).fetchone()
    if not existing:
        raise HTTPException(status_code=404, detail="Expense not found")
    c.execute("DELETE FROM expenses WHERE id=?", (expense_id,))
    c.commit()
    return {"status": "deleted", "id": expense_id}

@app.post("/income")
async def add_income(income: IncomeCreate, company: dict = Depends(check_auth)):
    """Add income entry."""
    try:
        dt = datetime.strptime(income.date, "%Y-%m-%d")
    except ValueError:
        raise HTTPException(status_code=400, detail="Date must be YYYY-MM-DD")
    
    c = get_db()
    c_cursor = c.execute("INSERT INTO income(company_id,amount,source,month,date) VALUES(?,?,?,?,?)",
              (company["company_id"], income.amount, income.source, dt.strftime("%Y-%m"), income.date))
    c.commit()
    income_id = c_cursor.lastrowid
    return {"status": "ok", "id": income_id}

@app.get("/income")
async def list_income(month: Optional[str] = Query(None), company: dict = Depends(check_auth)):
    """List income entries."""
    c = get_db()
    if month:
        rows = c.execute("SELECT * FROM income WHERE company_id=? AND month=? ORDER BY date DESC",
                        (company["company_id"], month)).fetchall()
    else:
        rows = c.execute("SELECT * FROM income WHERE company_id=? ORDER BY date DESC",
                        (company["company_id"],)).fetchall()
    return [dict(r) for r in rows]

@app.get("/stats")
async def get_stats(month: Optional[str] = Query(None), company: dict = Depends(check_auth)):
    """Get monthly statistics."""
    c = get_db()
    m = month or datetime.now().strftime("%Y-%m")
    
    expenses = c.execute("SELECT SUM(amount) as total, COUNT(*) as count FROM expenses WHERE company_id=? AND substr(date,1,7)=?",
                        (company["company_id"], m)).fetchone()
    income = c.execute("SELECT SUM(amount) as total FROM income WHERE company_id=? AND month=?",
                      (company["company_id"], m)).fetchone()
    categories = c.execute("SELECT category, SUM(amount) as total FROM expenses WHERE company_id=? AND substr(date,1,7)=? GROUP BY category ORDER BY total DESC",
                          (company["company_id"], m)).fetchall()
    
    return {
        "month": m,
        "company": company["company_name"],
        "total_expenses": expenses["total"] or 0,
        "total_income": income["total"] or 0,
        "balance": (income["total"] or 0) - (expenses["total"] or 0),
        "transaction_count": expenses["count"] or 0,
        "category_breakdown": {r["category"]: r["total"] for r in categories},
    }

@app.post("/api-keys")
async def create_api_key(company: dict = Depends(check_auth)):
    """Generate a new API key for the company."""
    if company["company_id"] != company.get("company_id"):
        raise HTTPException(status_code=403, detail="Not authorized")
    
    api_key = secrets.token_hex(32)
    c = get_db()
    c.execute("INSERT INTO api_keys(company_id, key) VALUES(?,?)", (company["company_id"], api_key))
    c.commit()
    return {"api_key": api_key, "company": company["company_name"]}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
