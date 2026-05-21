"""
SQLite database manager for Research Logger.
Handles all persistence: entries, tags, attachments, settings.
"""
import sqlite3
import os
import json
from datetime import date, datetime, timedelta
from typing import Optional, List, Dict, Any

from utils.richtext import content_to_plain_text


DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "research_logger.db")


class DatabaseManager:
    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        self._conn: Optional[sqlite3.Connection] = None
        self._init_db()

    # ─── Connection ────────────────────────────────────────────────────────────

    def _get_conn(self) -> sqlite3.Connection:
        if self._conn is None:
            self._conn = sqlite3.connect(self.db_path, check_same_thread=False)
            self._conn.row_factory = sqlite3.Row
            self._conn.execute("PRAGMA journal_mode=WAL")
            self._conn.execute("PRAGMA foreign_keys=ON")
        return self._conn

    def _init_db(self):
        conn = self._get_conn()
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS entries (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                entry_date  TEXT    NOT NULL UNIQUE,
                content     TEXT    NOT NULL DEFAULT '',
                created_at  TEXT    NOT NULL DEFAULT (datetime('now')),
                updated_at  TEXT    NOT NULL DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS tags (
                id      INTEGER PRIMARY KEY AUTOINCREMENT,
                name    TEXT NOT NULL UNIQUE
            );

            CREATE TABLE IF NOT EXISTS entry_tags (
                entry_id INTEGER NOT NULL REFERENCES entries(id) ON DELETE CASCADE,
                tag_id   INTEGER NOT NULL REFERENCES tags(id)   ON DELETE CASCADE,
                PRIMARY KEY (entry_id, tag_id)
            );

            CREATE TABLE IF NOT EXISTS attachments (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                entry_id    INTEGER NOT NULL REFERENCES entries(id) ON DELETE CASCADE,
                filename    TEXT NOT NULL,
                filepath    TEXT NOT NULL,
                file_type   TEXT NOT NULL DEFAULT 'file',
                added_at    TEXT NOT NULL DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS settings (
                key   TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_entries_date   ON entries(entry_date);
            CREATE INDEX IF NOT EXISTS idx_entry_tags_eid ON entry_tags(entry_id);
            CREATE VIRTUAL TABLE IF NOT EXISTS entries_fts
                USING fts5(entry_date UNINDEXED, content);
        """)
        # Populate FTS from existing data (safe rebuild)
        try:
            existing_fts = conn.execute("SELECT COUNT(*) FROM entries_fts").fetchone()[0]
            if existing_fts == 0:
                conn.execute("INSERT INTO entries_fts(entry_date, content) SELECT entry_date, content FROM entries")
        except Exception:
            pass
        conn.commit()
        self._ensure_default_settings()

    # ─── Entries ───────────────────────────────────────────────────────────────

    def get_entry(self, entry_date: str) -> Optional[Dict[str, Any]]:
        """Return the entry for a given date string YYYY-MM-DD."""
        conn = self._get_conn()
        row = conn.execute(
            "SELECT * FROM entries WHERE entry_date = ?", (entry_date,)
        ).fetchone()
        if row is None:
            return None
        result = dict(row)
        result["tags"] = self.get_entry_tags(result["id"])
        result["attachments"] = self.get_entry_attachments(result["id"])
        return result

    def get_or_create_entry(self, entry_date: str, default_content: str = "") -> Dict[str, Any]:
        existing = self.get_entry(entry_date)
        if existing:
            return existing
        conn = self._get_conn()
        conn.execute(
            "INSERT INTO entries (entry_date, content) VALUES (?, ?)",
            (entry_date, default_content)
        )
        conn.commit()
        return self.get_entry(entry_date)

    def save_entry(self, entry_date: str, content: str) -> Dict[str, Any]:
        conn = self._get_conn()
        conn.execute("""
            INSERT INTO entries (entry_date, content, updated_at)
            VALUES (?, ?, datetime('now'))
            ON CONFLICT(entry_date) DO UPDATE SET
                content    = excluded.content,
                updated_at = excluded.updated_at
        """, (entry_date, content))
        row = conn.execute(
            "SELECT id FROM entries WHERE entry_date = ?", (entry_date,)
        ).fetchone()
        entry_id = row["id"]
        # Sync FTS (delete by entry_date then re-insert)
        try:
            conn.execute("DELETE FROM entries_fts WHERE entry_date = ?", (entry_date,))
            conn.execute(
                "INSERT INTO entries_fts(entry_date, content) VALUES (?, ?)",
                (entry_date, content)
            )
        except Exception as e:
            print(f"FTS sync warning: {e}")
        conn.commit()
        return self.get_entry(entry_date)

    def get_entries_in_range(self, start_date: str, end_date: str) -> List[Dict[str, Any]]:
        conn = self._get_conn()
        rows = conn.execute(
            "SELECT * FROM entries WHERE entry_date BETWEEN ? AND ? ORDER BY entry_date",
            (start_date, end_date)
        ).fetchall()
        results = []
        for row in rows:
            d = dict(row)
            d["tags"] = self.get_entry_tags(d["id"])
            results.append(d)
        return results

    def get_all_entry_dates(self) -> List[str]:
        conn = self._get_conn()
        rows = conn.execute("SELECT entry_date FROM entries ORDER BY entry_date DESC").fetchall()
        return [r["entry_date"] for r in rows]

    # ─── Tags ──────────────────────────────────────────────────────────────────

    def get_entry_tags(self, entry_id: int) -> List[str]:
        conn = self._get_conn()
        rows = conn.execute("""
            SELECT t.name FROM tags t
            JOIN entry_tags et ON et.tag_id = t.id
            WHERE et.entry_id = ?
        """, (entry_id,)).fetchall()
        return [r["name"] for r in rows]

    def set_entry_tags(self, entry_date: str, tags: List[str]):
        entry = self.get_entry(entry_date)
        if not entry:
            return
        entry_id = entry["id"]
        conn = self._get_conn()
        # Remove old
        conn.execute("DELETE FROM entry_tags WHERE entry_id = ?", (entry_id,))
        for tag_name in tags:
            tag_name = tag_name.strip().lower()
            if not tag_name:
                continue
            conn.execute("INSERT OR IGNORE INTO tags (name) VALUES (?)", (tag_name,))
            tag_row = conn.execute("SELECT id FROM tags WHERE name = ?", (tag_name,)).fetchone()
            conn.execute(
                "INSERT OR IGNORE INTO entry_tags (entry_id, tag_id) VALUES (?, ?)",
                (entry_id, tag_row["id"])
            )
        conn.commit()

    def get_all_tags(self) -> List[str]:
        conn = self._get_conn()
        rows = conn.execute("SELECT name FROM tags ORDER BY name").fetchall()
        return [r["name"] for r in rows]

    def get_entries_by_tag(self, tag_name: str) -> List[str]:
        conn = self._get_conn()
        rows = conn.execute("""
            SELECT e.entry_date FROM entries e
            JOIN entry_tags et ON et.entry_id = e.id
            JOIN tags t ON t.id = et.tag_id
            WHERE t.name = ?
            ORDER BY e.entry_date DESC
        """, (tag_name,)).fetchall()
        return [r["entry_date"] for r in rows]

    # ─── Attachments ───────────────────────────────────────────────────────────

    def add_attachment(self, entry_date: str, filename: str, filepath: str, file_type: str = "file") -> int:
        entry = self.get_or_create_entry(entry_date)
        conn = self._get_conn()
        cursor = conn.execute(
            "INSERT INTO attachments (entry_id, filename, filepath, file_type) VALUES (?, ?, ?, ?)",
            (entry["id"], filename, filepath, file_type)
        )
        conn.commit()
        return cursor.lastrowid

    def get_entry_attachments(self, entry_id: int) -> List[Dict[str, Any]]:
        conn = self._get_conn()
        rows = conn.execute(
            "SELECT * FROM attachments WHERE entry_id = ? ORDER BY added_at",
            (entry_id,)
        ).fetchall()
        return [dict(r) for r in rows]

    def remove_attachment(self, attachment_id: int):
        conn = self._get_conn()
        conn.execute("DELETE FROM attachments WHERE id = ?", (attachment_id,))
        conn.commit()

    # ─── Search ────────────────────────────────────────────────────────────────

    def search(self, query: str, tag: Optional[str] = None) -> List[Dict[str, Any]]:
        conn = self._get_conn()
        results = []

        if query:
            search_query = query
            if " " in query and "\"" not in query:
                search_query = f'"{query}"'
            rows = conn.execute("""
                SELECT f.entry_date, e.content,
                       snippet(entries_fts, 1, '<b>', '</b>', '…', 20) AS snippet
                FROM entries_fts f
                JOIN entries e ON e.entry_date = f.entry_date
                WHERE entries_fts MATCH ?
                ORDER BY rank
            """, (search_query,)).fetchall()
            results = [dict(r) for r in rows]

        if tag:
            tagged_dates = set(self.get_entries_by_tag(tag))
            if query:
                results = [r for r in results if r["entry_date"] in tagged_dates]
            else:
                for d in self.get_entries_by_tag(tag):
                    entry = self.get_entry(d)
                    if entry:
                        plain = content_to_plain_text(entry["content"])
                        results.append({
                            "entry_date": d,
                            "content": entry["content"],
                            "snippet": plain[:200] + "…"
                        })

        for row in results:
            row["snippet"] = content_to_plain_text(row.get("snippet") or row.get("content", ""))

        return results

    # ─── Settings ──────────────────────────────────────────────────────────────

    def _ensure_default_settings(self):
        defaults = {
            "reminder_enabled": "true",
            "reminder_time": "20:00",
            "theme": "light",
            "auto_save_interval": "10",
            "morning_summary": "true",
        }
        conn = self._get_conn()
        for key, value in defaults.items():
            conn.execute(
                "INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)", (key, value)
            )
        conn.commit()

    def get_setting(self, key: str, default: str = "") -> str:
        conn = self._get_conn()
        row = conn.execute("SELECT value FROM settings WHERE key = ?", (key,)).fetchone()
        return row["value"] if row else default

    def set_setting(self, key: str, value: str):
        conn = self._get_conn()
        conn.execute(
            "INSERT INTO settings (key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value = excluded.value",
            (key, value)
        )
        conn.commit()

    def get_all_settings(self) -> Dict[str, str]:
        conn = self._get_conn()
        rows = conn.execute("SELECT key, value FROM settings").fetchall()
        return {r["key"]: r["value"] for r in rows}

    def close(self):
        if self._conn:
            self._conn.close()
            self._conn = None
