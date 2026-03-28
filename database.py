import sqlite3
from datetime import datetime, timedelta

DB_PATH = "jobs.db"


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with get_conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS jobs (
                id           TEXT PRIMARY KEY,
                title        TEXT,
                organization TEXT,
                location     TEXT,
                deadline     TEXT,
                job_type     TEXT,
                url          TEXT,
                first_seen   DATETIME,
                last_seen    DATETIME
            )
        """)
        # Add job_type column if upgrading from old schema
        try:
            conn.execute("ALTER TABLE jobs ADD COLUMN job_type TEXT DEFAULT ''")
            conn.commit()
        except Exception:
            pass  # Column already exists
        conn.commit()


def upsert_jobs(jobs: list[dict]):
    now = datetime.utcnow().isoformat()
    with get_conn() as conn:
        for job in jobs:
            existing = conn.execute(
                "SELECT id FROM jobs WHERE id = ?", (job["id"],)
            ).fetchone()
            job_type = job.get("job_type", "")
            deadline = job.get("deadline", "")
            if existing:
                conn.execute(
                    "UPDATE jobs SET title=?, organization=?, location=?, deadline=?, job_type=?, url=?, last_seen=? WHERE id=?",
                    (job["title"], job["organization"], job["location"],
                     deadline, job_type, job["url"], now, job["id"])
                )
            else:
                conn.execute(
                    "INSERT INTO jobs (id, title, organization, location, deadline, job_type, url, first_seen, last_seen) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (job["id"], job["title"], job["organization"], job["location"],
                     deadline, job_type, job["url"], now, now)
                )
        conn.commit()


def get_recent_jobs(hours: int = 48) -> list[dict]:
    cutoff = (datetime.utcnow() - timedelta(hours=hours)).isoformat()
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM jobs WHERE first_seen >= ? ORDER BY first_seen DESC",
            (cutoff,)
        ).fetchall()
    return [dict(row) for row in rows]
