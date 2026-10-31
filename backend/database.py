import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from cryptography.fernet import Fernet

from config import DATABASE_PATH, TOKEN_KEY_PATH


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def _connect():
    con = sqlite3.connect(DATABASE_PATH, timeout=20)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA journal_mode=WAL")
    con.execute("PRAGMA foreign_keys=ON")
    return con


def init_db() -> None:
    with _connect() as con:
        con.executescript("""
        CREATE TABLE IF NOT EXISTS history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            action TEXT NOT NULL,
            details TEXT NOT NULL DEFAULT '',
            status TEXT NOT NULL DEFAULT 'success',
            created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS drafts (
            id TEXT PRIMARY KEY,
            filename TEXT NOT NULL,
            stored_path TEXT NOT NULL,
            public_token TEXT NOT NULL,
            caption TEXT NOT NULL DEFAULT '',
            hashtags TEXT NOT NULL DEFAULT '',
            video_summary TEXT NOT NULL DEFAULT '',
            cover_filename TEXT NOT NULL DEFAULT '',
            status TEXT NOT NULL DEFAULT 'draft',
            instagram_media_id TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS instagram_connection (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            token_encrypted BLOB NOT NULL,
            user_id TEXT NOT NULL,
            username TEXT NOT NULL DEFAULT '',
            expires_at TEXT NOT NULL DEFAULT '',
            updated_at TEXT NOT NULL
        );
        """)
        # Backward-compatible migrations for existing personal workspaces.
        existing = {row[1] for row in con.execute("PRAGMA table_info(drafts)").fetchall()}
        for column, definition in {
            "content_prompt": "TEXT NOT NULL DEFAULT ''",
            "gemini_file_uri": "TEXT NOT NULL DEFAULT ''",
            "gemini_file_mime_type": "TEXT NOT NULL DEFAULT ''",
        }.items():
            if column not in existing:
                con.execute(f"ALTER TABLE drafts ADD COLUMN {column} {definition}")
    _fernet()


def _fernet() -> Fernet:
    if not TOKEN_KEY_PATH.exists():
        TOKEN_KEY_PATH.write_bytes(Fernet.generate_key())
        try:
            TOKEN_KEY_PATH.chmod(0o600)
        except OSError:
            pass
    return Fernet(TOKEN_KEY_PATH.read_bytes())


def save_token(token: str, user_id: str, username: str, expires_in: int = 0) -> None:
    expires_at = ""
    if expires_in:
        from datetime import timedelta
        expires_at = (datetime.now(timezone.utc) + timedelta(seconds=int(expires_in))).astimezone().isoformat(timespec="seconds")
    encrypted = _fernet().encrypt(token.encode("utf-8"))
    with _connect() as con:
        con.execute("""INSERT INTO instagram_connection(id, token_encrypted, user_id, username, expires_at, updated_at)
            VALUES(1, ?, ?, ?, ?, ?) ON CONFLICT(id) DO UPDATE SET
            token_encrypted=excluded.token_encrypted, user_id=excluded.user_id,
            username=excluded.username, expires_at=excluded.expires_at, updated_at=excluded.updated_at""",
            (encrypted, str(user_id), username, expires_at, now_iso()))


def get_connection() -> dict[str, Any] | None:
    with _connect() as con:
        row = con.execute("SELECT * FROM instagram_connection WHERE id=1").fetchone()
    if not row:
        return None
    return {
        "token": _fernet().decrypt(row["token_encrypted"]).decode("utf-8"),
        "user_id": row["user_id"], "username": row["username"],
        "expires_at": row["expires_at"], "updated_at": row["updated_at"]
    }


def remove_connection() -> None:
    with _connect() as con:
        con.execute("DELETE FROM instagram_connection WHERE id=1")


def add_history(action: str, details: str = "", status: str = "success") -> None:
    with _connect() as con:
        con.execute("INSERT INTO history(action, details, status, created_at) VALUES(?,?,?,?)",
                    (action, details[:1000], status, now_iso()))


def get_history(limit: int = 200) -> list[dict[str, Any]]:
    with _connect() as con:
        rows = con.execute("SELECT * FROM history ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
    return [dict(r) for r in rows]


def create_draft(data: dict[str, Any]) -> None:
    with _connect() as con:
        con.execute("""INSERT INTO drafts(id, filename, stored_path, public_token, caption, hashtags,
            video_summary, cover_filename, status, created_at, content_prompt, gemini_file_uri,
            gemini_file_mime_type) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (data["id"], data["filename"], data["stored_path"], data["public_token"],
             data.get("caption", ""), data.get("hashtags", ""), data.get("video_summary", ""),
             data.get("cover_filename", ""), data.get("status", "draft"), now_iso(),
             data.get("content_prompt", ""), data.get("gemini_file_uri", ""),
             data.get("gemini_file_mime_type", "")))


def update_draft(draft_id: str, **fields: str) -> None:
    allowed = {"caption", "hashtags", "video_summary", "content_prompt", "cover_filename",
               "gemini_file_uri", "gemini_file_mime_type", "status", "instagram_media_id"}
    pairs = [(k, v) for k, v in fields.items() if k in allowed]
    if not pairs:
        return
    assignments = ",".join(f"{k}=?" for k, _ in pairs)
    with _connect() as con:
        con.execute(f"UPDATE drafts SET {assignments} WHERE id=?", [v for _, v in pairs] + [draft_id])


def get_draft(draft_id: str) -> dict[str, Any] | None:
    with _connect() as con:
        row = con.execute("SELECT * FROM drafts WHERE id=?", (draft_id,)).fetchone()
    return dict(row) if row else None


def get_drafts(limit: int = 100) -> list[dict[str, Any]]:
    with _connect() as con:
        rows = con.execute("SELECT * FROM drafts ORDER BY created_at DESC LIMIT ?", (limit,)).fetchall()
    return [dict(r) for r in rows]
