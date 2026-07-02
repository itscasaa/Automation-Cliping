import sqlite3
from pathlib import Path
from datetime import datetime

DB_PATH = Path(__file__).parent / "clipper_queue.db"


def get_db_connection():
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Membuat tabel jobs jika belum ada."""
    conn = get_db_connection()
    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS jobs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                url TEXT,
                file_path TEXT,
                content_type TEXT NOT NULL,
                max_clips INTEGER NOT NULL,
                lang TEXT,
                no_face_track INTEGER DEFAULT 0, -- 0 = False, 1 = True
                status TEXT NOT NULL CHECK(status IN ('pending', 'processing', 'completed', 'failed')),
                discord_channel_id INTEGER,
                error_message TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                started_at TEXT,
                completed_at TEXT
            )
        """)
        conn.commit()
    finally:
        conn.close()


def add_job(
    url=None,
    file_path=None,
    content_type="general",
    max_clips=5,
    lang=None,
    no_face_track=False,
    discord_channel_id=None,
):
    """Menambahkan job baru ke antrean."""
    if not url and not file_path:
        raise ValueError("Job harus memiliki url atau file_path!")

    init_db()  # Pastikan DB terinisialisasi

    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO jobs (url, file_path, content_type, max_clips, lang, no_face_track, status, discord_channel_id)
            VALUES (?, ?, ?, ?, ?, ?, 'pending', ?)
        """, (
            url,
            file_path,
            content_type,
            max_clips,
            lang,
            1 if no_face_track else 0,
            discord_channel_id,
        ))
        conn.commit()
        return cursor.lastrowid
    finally:
        conn.close()


def get_next_pending_job():
    """Mengambil job pending tertua untuk diproses."""
    init_db()
    conn = get_db_connection()
    try:
        row = conn.execute("""
            SELECT * FROM jobs 
            WHERE status = 'pending' 
            ORDER BY id ASC 
            LIMIT 1
        """).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def update_job_status(job_id: int, status: str, error_message: str = None):
    """Memperbarui status job beserta timestamp-nya."""
    init_db()
    now_str = datetime.now().isoformat()
    conn = get_db_connection()
    try:
        if status == "processing":
            conn.execute("""
                UPDATE jobs 
                SET status = ?, started_at = ? 
                WHERE id = ?
            """, (status, now_str, job_id))
        elif status in ("completed", "failed"):
            conn.execute("""
                UPDATE jobs 
                SET status = ?, completed_at = ?, error_message = ? 
                WHERE id = ?
            """, (status, now_str, error_message, job_id))
        else:
            conn.execute("""
                UPDATE jobs 
                SET status = ? 
                WHERE id = ?
            """, (status, job_id))
        conn.commit()
    finally:
        conn.close()


def get_queue_status():
    """Mendapatkan statistik antrean."""
    init_db()
    conn = get_db_connection()
    try:
        pending = conn.execute("SELECT COUNT(*) FROM jobs WHERE status = 'pending'").fetchone()[0]
        processing = conn.execute("SELECT COUNT(*) FROM jobs WHERE status = 'processing'").fetchone()[0]
        completed = conn.execute("SELECT COUNT(*) FROM jobs WHERE status = 'completed'").fetchone()[0]
        failed = conn.execute("SELECT COUNT(*) FROM jobs WHERE status = 'failed'").fetchone()[0]
        return {
            "pending": pending,
            "processing": processing,
            "completed": completed,
            "failed": failed,
        }
    finally:
        conn.close()
