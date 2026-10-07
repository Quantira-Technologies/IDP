"""Persistence: per-user scans + a Windows-like folder tree, on SQLite.

Kept intentionally small. Production would use PostgreSQL with migrations, but the
shape here (ownership, folders, soft metadata columns for fast listing) mirrors it.
"""
from __future__ import annotations

import json
import os
import sqlite3
import uuid
from datetime import datetime, timezone
from threading import Lock

from .config import settings
from .models import DocumentResult


def _sqlite_path() -> str:
    url = settings.database_url
    if url.startswith("sqlite:///"):
        return url.replace("sqlite:///", "", 1)
    return "./storage/intel2doc.sqlite3"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class Store:
    def __init__(self) -> None:
        self._lock = Lock()
        self._cache: dict[str, DocumentResult] = {}
        path = _sqlite_path()
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        self._conn = sqlite3.connect(path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._images_dir = os.path.join(os.path.dirname(path) or ".", "uploads")
        os.makedirs(self._images_dir, exist_ok=True)
        self._conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS results (
                id TEXT PRIMARY KEY, owner TEXT, source_name TEXT, doc_type TEXT,
                route TEXT, engine TEXT, approved INTEGER DEFAULT 0,
                folder_id TEXT, created_at TEXT, payload TEXT
            );
            CREATE TABLE IF NOT EXISTS folders (
                id TEXT PRIMARY KEY, owner TEXT, name TEXT, parent_id TEXT, created_at TEXT
            );
            """
        )
        cols = {r["name"] for r in self._conn.execute("PRAGMA table_info(results)")}
        for col, ddl in [
            ("owner", "owner TEXT"), ("source_name", "source_name TEXT"),
            ("doc_type", "doc_type TEXT"), ("route", "route TEXT"),
            ("engine", "engine TEXT"), ("approved", "approved INTEGER DEFAULT 0"),
            ("folder_id", "folder_id TEXT"), ("created_at", "created_at TEXT"),
            ("confidence", "confidence REAL DEFAULT 0"),
        ]:
            if col not in cols:
                self._conn.execute(f"ALTER TABLE results ADD COLUMN {ddl}")
        self._conn.commit()

    # ------------------------------------------------------------------ scans
    def save(self, result: DocumentResult) -> None:
        sub = result.sub_documents[0] if result.sub_documents else None
        conf = round(sub.min_confidence, 4) if sub else 0.0
        with self._lock:
            self._cache[result.id] = result
            self._conn.execute(
                """INSERT OR REPLACE INTO results
                   (id, owner, source_name, doc_type, route, engine, approved, folder_id, created_at, confidence, payload)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    result.id, result.owner, result.source_name,
                    sub.doc_type.value if sub else "unknown",
                    sub.route.value if sub else "needs_review",
                    sub.engine if sub else "",
                    1 if result.approved else 0,
                    result.folder_id, result.created_at or _now(), conf,
                    result.model_dump_json(),
                ),
            )
            self._conn.commit()

    # ------------------------------------------------------------ preview image
    def save_image(self, doc_id: str, data: bytes | None) -> None:
        if not data:
            return
        with open(os.path.join(self._images_dir, doc_id), "wb") as fh:
            fh.write(data)

    def image_bytes(self, doc_id: str) -> bytes | None:
        path = os.path.join(self._images_dir, doc_id)
        if not os.path.exists(path):
            return None
        with open(path, "rb") as fh:
            return fh.read()

    def get(self, doc_id: str) -> DocumentResult | None:
        with self._lock:
            if doc_id in self._cache:
                return self._cache[doc_id]
            row = self._conn.execute("SELECT payload FROM results WHERE id=?", (doc_id,)).fetchone()
            if not row:
                return None
            result = DocumentResult.model_validate(json.loads(row["payload"]))
            self._cache[doc_id] = result
            return result

    def list_for_owner(self, owner: str, folder_id: str | None = "__any__") -> list[dict]:
        q = "SELECT id, source_name, doc_type, route, engine, approved, folder_id, created_at, confidence FROM results WHERE owner=?"
        args: list = [owner]
        if folder_id != "__any__":
            if folder_id is None:
                q += " AND (folder_id IS NULL OR folder_id='')"
            else:
                q += " AND folder_id=?"
                args.append(folder_id)
        q += " ORDER BY created_at DESC"
        with self._lock:
            rows = self._conn.execute(q, args).fetchall()
        return [
            {
                "id": r["id"], "source_name": r["source_name"], "doc_type": r["doc_type"],
                "route": r["route"], "engine": r["engine"], "approved": bool(r["approved"]),
                "folder_id": r["folder_id"], "created_at": r["created_at"],
                "confidence": r["confidence"] or 0.0,
            }
            for r in rows
        ]

    def owns(self, doc_id: str, owner: str) -> bool:
        with self._lock:
            row = self._conn.execute("SELECT owner FROM results WHERE id=?", (doc_id,)).fetchone()
        return bool(row) and row["owner"] == owner

    def delete(self, doc_id: str, owner: str) -> bool:
        with self._lock:
            cur = self._conn.execute("DELETE FROM results WHERE id=? AND owner=?", (doc_id, owner))
            self._conn.commit()
            self._cache.pop(doc_id, None)
            return cur.rowcount > 0

    def set_folder(self, doc_id: str, owner: str, folder_id: str | None) -> bool:
        with self._lock:
            cur = self._conn.execute(
                "UPDATE results SET folder_id=? WHERE id=? AND owner=?", (folder_id, doc_id, owner)
            )
            self._conn.commit()
            self._cache.pop(doc_id, None)
            return cur.rowcount > 0

    # -------------------------------------------------------------- analytics
    def analytics_rows(self, owner: str | None = None) -> list[dict]:
        """Lightweight rows for dashboard aggregation (optionally scoped to a user)."""
        q = "SELECT doc_type, route, approved, created_at, confidence, owner FROM results"
        args: list = []
        if owner:
            q += " WHERE owner=?"
            args.append(owner)
        with self._lock:
            rows = self._conn.execute(q, args).fetchall()
        return [
            {
                "doc_type": r["doc_type"] or "unknown",
                "route": r["route"] or "needs_review",
                "approved": bool(r["approved"]),
                "created_at": r["created_at"] or "",
                "confidence": r["confidence"] or 0.0,
                "owner": r["owner"] or "",
            }
            for r in rows
        ]

    def detail_payloads(self, owner: str | None = None) -> list[dict]:
        """Full result payloads (for country/rule-level analytics)."""
        q = "SELECT payload FROM results"
        args: list = []
        if owner:
            q += " WHERE owner=?"
            args.append(owner)
        with self._lock:
            rows = self._conn.execute(q, args).fetchall()
        out: list[dict] = []
        for r in rows:
            try:
                out.append(json.loads(r["payload"]))
            except (json.JSONDecodeError, TypeError):
                continue
        return out

    # ---------------------------------------------------------------- folders
    def list_folders(self, owner: str) -> list[dict]:
        with self._lock:
            rows = self._conn.execute(
                "SELECT id, name, parent_id, created_at FROM folders WHERE owner=? ORDER BY name", (owner,)
            ).fetchall()
            counts = {
                r["folder_id"]: r["n"]
                for r in self._conn.execute(
                    "SELECT folder_id, COUNT(*) n FROM results WHERE owner=? GROUP BY folder_id", (owner,)
                ).fetchall()
            }
        return [
            {"id": r["id"], "name": r["name"], "parent_id": r["parent_id"],
             "created_at": r["created_at"], "count": counts.get(r["id"], 0)}
            for r in rows
        ]

    def create_folder(self, owner: str, name: str, parent_id: str | None) -> dict:
        fid = f"f-{uuid.uuid4().hex[:10]}"
        clean = (name or "").strip() or "New folder"
        with self._lock:
            self._conn.execute(
                "INSERT INTO folders (id, owner, name, parent_id, created_at) VALUES (?,?,?,?,?)",
                (fid, owner, clean, parent_id, _now()),
            )
            self._conn.commit()
        return {"id": fid, "name": clean, "parent_id": parent_id, "count": 0}

    def rename_folder(self, owner: str, folder_id: str, name: str) -> bool:
        with self._lock:
            cur = self._conn.execute(
                "UPDATE folders SET name=? WHERE id=? AND owner=?", ((name or "").strip(), folder_id, owner)
            )
            self._conn.commit()
            return cur.rowcount > 0

    def delete_folder(self, owner: str, folder_id: str) -> bool:
        """Delete a folder; its scans and child folders move up to its parent."""
        with self._lock:
            row = self._conn.execute(
                "SELECT parent_id FROM folders WHERE id=? AND owner=?", (folder_id, owner)
            ).fetchone()
            if not row:
                return False
            parent = row["parent_id"]
            self._conn.execute("UPDATE results SET folder_id=? WHERE owner=? AND folder_id=?", (parent, owner, folder_id))
            self._conn.execute("UPDATE folders SET parent_id=? WHERE owner=? AND parent_id=?", (parent, owner, folder_id))
            self._conn.execute("DELETE FROM folders WHERE id=? AND owner=?", (folder_id, owner))
            self._conn.commit()
            return True


store = Store()
