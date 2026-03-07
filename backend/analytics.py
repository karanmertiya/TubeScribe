"""
Analytics — lightweight SQLite counter.
Tracks: PDFs generated, videos processed, distinct sessions, daily counts.
No PII. No external service. File lives at DATA_DIR/analytics.db

On Railway/Render with ephemeral filesystems, set DATA_DIR to a mounted volume.
If the file can't be written, analytics silently no-ops (never breaks the app).
"""
from __future__ import annotations
import datetime
import logging
import os
import sqlite3

log      = logging.getLogger("tubescribe.analytics")
DATA_DIR = os.getenv("DATA_DIR", ".")
DB_PATH  = os.path.join(DATA_DIR, "analytics.db")


def _conn() -> sqlite3.Connection | None:
    try:
        con = sqlite3.connect(DB_PATH)
        con.execute("""
            CREATE TABLE IF NOT EXISTS events (
                id        INTEGER PRIMARY KEY AUTOINCREMENT,
                ts        TEXT    NOT NULL,
                event     TEXT    NOT NULL,   -- 'pdf_generated' | 'video_processed' | 'session'
                mode      TEXT,               -- 'dev' | 'user'
                session   TEXT,               -- hashed session ID (no PII)
                provider  TEXT                -- 'gemini' | 'groq'
            )
        """)
        con.commit()
        return con
    except Exception as exc:
        log.debug("Analytics DB unavailable: %s", exc)
        return None


def record(event: str, mode: str = "", session: str = "", provider: str = "") -> None:
    con = _conn()
    if not con:
        return
    try:
        con.execute(
            "INSERT INTO events (ts, event, mode, session, provider) VALUES (?,?,?,?,?)",
            (datetime.datetime.utcnow().isoformat(), event, mode, session, provider),
        )
        con.commit()
    except Exception as exc:
        log.debug("Analytics write failed: %s", exc)
    finally:
        con.close()


def summary() -> dict:
    """Return aggregate counts for the public stats endpoint."""
    con = _conn()
    if not con:
        return {}
    try:
        def q(sql: str) -> int:
            return con.execute(sql).fetchone()[0] or 0

        today = datetime.date.today().isoformat()
        return {
            "pdfs_generated":    q("SELECT COUNT(*) FROM events WHERE event='pdf_generated'"),
            "videos_processed":  q("SELECT COUNT(*) FROM events WHERE event='video_processed'"),
            "distinct_users":    q("SELECT COUNT(DISTINCT session) FROM events WHERE mode='user' AND session != ''"),
            "daily_active_users": q(f"SELECT COUNT(DISTINCT session) FROM events WHERE ts LIKE '{today}%' AND session != ''"),
        }
    except Exception:
        return {}
    finally:
        con.close()
