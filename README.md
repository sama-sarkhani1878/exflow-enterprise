# 🏢 ExFlow Enterprise

**Multi-company expense management system** built with Python + Streamlit.

Manage expenses, income, budgets, invoices (OCR), and users for multiple companies — in 3 languages (🇮🇷 فارسی / 🇩🇪 Deutsch / 🇬🇧 English).

---

## ✨ Features

| Feature | Description |
|---|---|
| 🔐 **Multi-role auth** | Super Admin / Company Admin / Employee + master login + change password |
| 🏢 **Multi-company** | Independent companies, users, budgets, data + per-company brand color |
| 📊 **Dashboard** | Metrics + charts (pie, daily trend) |
| 📋 **Transactions** | Add/edit/delete expenses & income with categories |
| 📂 **File import** | Bulk upload from CSV / Excel (German & US amount formats) |
| 🎯 **Budgets** | Monthly budget vs actual + warning when nearing/exceeding |
| 📄 **Invoice OCR** | Upload invoice photo → auto-extract vendor/amount/date |
| 📈 **Advanced reports** | Monthly comparison + Excel export |
| 📜 **Activity log** | Audit trail of who added/edited/deleted what |
| 💾 **Backup** | One-click + scheduled daily DB backups |
| 🔗 **REST API** | FastAPI endpoints with per-company API keys |
| 🧪 **Automated tests** | 52 pytest tests (DB, auth, API) |
| 🐳 **Docker** | Dockerfile + docker-compose for easy deploy |
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
git clone https://github.com/sama-sarkhani1878/exflow-enterprise.git
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

### Run with Docker

```bash
# Build & start both app (8503) and API (8000)
docker compose up -d

# Just the app
docker build -t exflow . && docker run -p 8503:8503 exflow
```

Data persists in the `./data` volume.

### Run tests

```bash
python3 -m pytest tests/ -v
```

### Manual backup

```bash
python3 backup.py                 # one backup now
python3 backup.py --keep 14       # prune to the last 14 backups
```

---

## 🌐 Deploy (make it public 24/7)

### Option A — Streamlit Community Cloud (easiest, free)

1. Push this repo to GitHub.
2. Go to **https://share.streamlit.io** and Sign in with GitHub.
3. Select `exflow-enterprise`, main file `app.py`, click **Deploy**.
4. Your app is live at `https://<name>.streamlit.app`.

> ⚠️ Free tier stores the SQLite DB in ephemeral storage — data resets on each redeploy. For persistent storage, use Option B or connect a Supabase/Postgres database.

### Option B — Railway / Render (persistent)

1. Create a repo + push.
2. On **Railway** or **Render**: New project → link the GitHub repo.
3. Set the start command: `streamlit run app.py --server.port 8503`.
4. Attach a **Postgres** database and set `DATABASE_URL`.
5. Deploy. Data persists in the managed DB.

### Option C — Your own server (Docker)

```bash
git clone <your-repo> && cd exflow-enterprise
docker compose up -d
```

Then point a domain/reverse-proxy (Caddy/Nginx) at port 8503.

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
├── db.py             # Shared DB & auth helpers (app + API + tests)
├── importer.py       # CSV / Excel file importer
├── pdf_report.py     # HTML report generator
├── ocr_scanner.py    # Invoice OCR (Tesseract)
├── backup.py         # DB backup script
├── tests/            # pytest suite (52 tests)
├── Dockerfile        # Container image
├── docker-compose.yml# App + API services
├── requirements.txt  # Python dependencies
└── data/             # SQLite database + backups (gitignored)
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
