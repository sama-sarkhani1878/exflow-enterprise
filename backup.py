#!/usr/bin/env python3
"""
ExFlow Enterprise — Database Backup script
===========================================
Copies the SQLite DB to a timestamped backup under data/backups/.

Usage:
    python3 backup.py                 # make one backup now
    python3 backup.py --keep 14       # keep only last 14 backups (prune older)
"""
import os
import sys
import shutil
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "exflow.db")
BACKUP_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "backups")


def make_backup() -> str:
    os.makedirs(BACKUP_DIR, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    dest = os.path.join(BACKUP_DIR, f"exflow_{ts}.db")
    # Ensure WAL is checkpointed so the backup is consistent
    try:
        import sqlite3
        conn = sqlite3.connect(DB_PATH, timeout=10)
        conn.execute("PRAGMA wal_checkpoint(FULL)")
        conn.close()
    except Exception:
        pass
    if os.path.exists(DB_PATH):
        shutil.copy2(DB_PATH, dest)
    else:
        raise FileNotFoundError(f"DB not found: {DB_PATH}")
    return dest


def prune(keep: int = 14):
    backups = sorted([f for f in os.listdir(BACKUP_DIR) if f.startswith("exflow_")])
    while len(backups) > keep:
        rm = os.path.join(BACKUP_DIR, backups.pop(0))
        os.remove(rm)
        print(f"  pruned: {rm}")


if __name__ == "__main__":
    dest = make_backup()
    print(f"✅ Backup created: {dest}")
    keep = 14
    if len(sys.argv) > 2 and sys.argv[1] == "--keep":
        keep = int(sys.argv[2])
    if keep:
        prune(keep)