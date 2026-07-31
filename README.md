# 🏢 ExFlow Enterprise

**Multi-company expense management system** built with Python + Streamlit.

Manage expenses, income, budgets, invoices (OCR), and users for multiple companies — in 3 languages (🇮🇷 فارسی / 🇩🇪 Deutsch / 🇬🇧 English).

---

## ✨ Features

| Feature | Description |
|---|---|
| 🔐 **Multi-role auth** | Super Admin / Company Admin / Employee |
| 🏢 **Multi-company** | Independent companies, users, budgets, data |
| 📊 **Dashboard** | Metrics + charts (pie, daily trend) |
| 📋 **Transactions** | Add/delete expenses & income with categories |
| 🎯 **Budgets** | Monthly budget vs actual with progress |
| 📄 **Invoice OCR** | Upload invoice photo → auto-extract vendor/amount/date |
| 📄 **Reports** | HTML monthly report in 3 languages |
| 🔗 **REST API** | FastAPI endpoints with per-company API keys |
| 📱 **PWA-ready** | Installable on mobile home screen |
| 🌐 **3 Languages** | Full UI translation (FA/DE/EN) |

---

## 🚀 Quick Start

### Requirements
- Python 3.11+
- [Tesseract OCR](https://github.com/tesseract-ocr/tesseract) (for invoice scanning)

### Install

```bash
# 1. Clone
git clone https://github.com/YOUR_USERNAME/exflow-enterprise.git
cd exflow-enterprise

# 2. Create virtual environment
python3 -m venv venv
source venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Install Tesseract (macOS)
brew install tesseract tesseract-lang
```

### Run the app

```bash
python3 -m streamlit run app.py --server.port 8503
```

Open **http://localhost:8503**

> **Default login:** `admin` / `admin123`
> ⚠️ Change this immediately after first login (Settings → Change Password)

### Run the REST API (optional)

```bash
python3 api.py
```

API docs at **http://localhost:8000/docs**

---

## 🌍 Access from your phone

```bash
cloudflared tunnel --url http://localhost:8503
```

The tunnel gives you a public URL like `https://xxx.trycloudflare.com`.

---

## 🗂️ Project Structure

```
exflow-enterprise/
├── app.py            # Main Streamlit app (auth, pages, translations)
├── api.py            # FastAPI REST API
├── pdf_report.py     # HTML report generator
├── ocr_scanner.py    # Invoice OCR (Tesseract)
├── data/             # SQLite database (gitignored)
└── requirements.txt  # Python dependencies
```

---

## 🔧 Tech Stack

- **Python** — backend logic
- **Streamlit** — web UI
- **SQLite** — database
- **FastAPI / Uvicorn** — REST API
- **Tesseract + pytesseract** — OCR
- **Pandas / Plotly** — charts
- **fpdf2** — PDF generation
- **Cloudflare Tunnel** — remote access

---

## 📄 License

MIT
