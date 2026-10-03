"""SQLite catalog with immutable content-addressed source snapshots."""
import hashlib
import json
import re
import sqlite3
from contextlib import contextmanager
from pathlib import Path

from .sources import normalize_act, now


class Store:
    def __init__(self, directory):
        self.directory = Path(directory)
        self.directory.mkdir(parents=True, exist_ok=True)
        self.path = self.directory / "catalog.sqlite3"
        with self.connect() as db:
            db.executescript("""
                PRAGMA journal_mode=WAL;
                CREATE TABLE IF NOT EXISTS acts (
                    eli TEXT PRIMARY KEY, title TEXT NOT NULL, publisher TEXT, year INTEGER,
                    metadata TEXT NOT NULL, fetched_at TEXT NOT NULL, body TEXT NOT NULL DEFAULT '',
                    text_fetched_at TEXT, text_stale INTEGER NOT NULL DEFAULT 0);
                CREATE VIRTUAL TABLE IF NOT EXISTS acts_fts USING fts5(eli UNINDEXED, title, body);
                CREATE TABLE IF NOT EXISTS snapshots (
                    eli TEXT, kind TEXT, sha256 TEXT, source_url TEXT, fetched_at TEXT,
                    PRIMARY KEY (eli,kind,sha256));
                CREATE TABLE IF NOT EXISTS sync_runs (
                    scope TEXT PRIMARY KEY, next_offset INTEGER, reported_total INTEGER,
                    completed INTEGER, updated_at TEXT);
            """)

    @contextmanager
    def connect(self):
        db = sqlite3.connect(self.path, timeout=15)
        db.row_factory = sqlite3.Row
        try:
            with db:
                yield db
        finally:
            db.close()

    def _snapshot(self, db, eli, kind, raw, source_url, stamp):
        digest = hashlib.sha256(raw).hexdigest()
        folder = self.directory / "snapshots" / digest[:2]
        folder.mkdir(parents=True, exist_ok=True)
        target = folder / digest
        # O_EXCL-equivalent: snapshots are append-only, never overwritten.
        try:
            with target.open("xb") as handle:
                handle.write(raw)
        except FileExistsError:
            if hashlib.sha256(target.read_bytes()).hexdigest() != digest:
                raise ValueError("Niezgodna suma istniejącego snapshotu.")
        db.execute("INSERT OR IGNORE INTO snapshots VALUES (?,?,?,?,?)", (eli,kind,digest,source_url,stamp))
        return digest

    def upsert(self, item, *, source_url, raw=None):
        act = normalize_act(item)
        stamp = now()
        with self.connect() as db:
            old = db.execute("SELECT metadata FROM acts WHERE eli=?", (act["eli"],)).fetchone()
            changed = old is not None and json.loads(old["metadata"]).get("changeDate") != item.get("changeDate")
            db.execute("""INSERT INTO acts (eli,title,publisher,year,metadata,fetched_at) VALUES (?,?,?,?,?,?)
                ON CONFLICT(eli) DO UPDATE SET title=excluded.title, metadata=excluded.metadata,
                fetched_at=excluded.fetched_at, text_stale=CASE WHEN ? THEN 1 ELSE acts.text_stale END""",
                (act["eli"],act["title"],act["publisher"],act["year"],json.dumps(item,ensure_ascii=False),stamp,changed))
            self._snapshot(db, act["eli"], "metadata" if raw is not None else "metadata_item", raw if raw is not None else json.dumps(item,ensure_ascii=False,sort_keys=True).encode(), source_url, stamp)
            self._reindex(db, act["eli"])
        return act

    def set_text(self, eli, text, raw, source_url):
        with self.connect() as db:
            if not db.execute("SELECT 1 FROM acts WHERE eli=?", (eli,)).fetchone():
                raise ValueError("Najpierw zaimportuj metadane aktu.")
            digest = self._snapshot(db, eli, "html", raw, source_url, now())
            db.execute("UPDATE acts SET body=?, text_fetched_at=?, text_stale=0 WHERE eli=?", (text,now(),eli))
            self._reindex(db, eli)
        return digest

    @staticmethod
    def _reindex(db, eli):
        row = db.execute("SELECT title,body,text_stale FROM acts WHERE eli=?", (eli,)).fetchone()
        db.execute("DELETE FROM acts_fts WHERE eli=?", (eli,))
        db.execute("INSERT INTO acts_fts VALUES (?,?,?)", (eli,row["title"],"" if row["text_stale"] else row["body"]))

    @staticmethod
    def _public(row):
        act = normalize_act(json.loads(row["metadata"]))
        act.update(fetched_at=row["fetched_at"], text_fetched_at=row["text_fetched_at"],
                   text_stale=bool(row["text_stale"]), indexed_text=bool(row["body"]) and not row["text_stale"])
        return act

    def get(self, eli):
        with self.connect() as db:
            row = db.execute("SELECT * FROM acts WHERE eli=?", (eli,)).fetchone()
            if not row:
                return None
            act = self._public(row)
            act["text"] = row["body"]
            act["snapshots"] = [dict(s) for s in db.execute("SELECT kind,sha256,source_url,fetched_at FROM snapshots WHERE eli=? ORDER BY fetched_at DESC", (eli,))]
            return act

    def search(self, query, limit=20):
        tokens = re.findall(r"[^\W_]+", query, re.UNICODE)[:12]
        if not tokens:
            return []
        # User input never becomes raw FTS syntax.
        expression = " AND ".join('"' + token + '"*' for token in tokens)
        with self.connect() as db:
            rows = db.execute("""SELECT a.* FROM acts_fts f JOIN acts a ON a.eli=f.eli
                WHERE acts_fts MATCH ? ORDER BY bm25(acts_fts,0,5,1) LIMIT ?""", (expression,limit)).fetchall()
            return [self._public(row) for row in rows]

    def recent(self, limit=6):
        with self.connect() as db:
            return [self._public(row) for row in db.execute("SELECT * FROM acts ORDER BY fetched_at DESC,eli LIMIT ?", (limit,))]

    def status(self):
        with self.connect() as db:
            counts = db.execute("SELECT COUNT(*) n, COALESCE(SUM(body!='' AND text_stale=0),0) t, MAX(fetched_at) d FROM acts").fetchone()
            return {"metadata_count": counts["n"], "text_count": counts["t"], "last_import": counts["d"],
                    "temporal_verified_count": 0, "complete_polish_law": False,
                    "by_publisher": {r["publisher"]:r["n"] for r in db.execute("SELECT publisher,COUNT(*) n FROM acts GROUP BY publisher")},
                    "imports": [dict(r) for r in db.execute("SELECT * FROM sync_runs ORDER BY scope")]}

    def checkpoint(self, scope, offset, total, complete):
        with self.connect() as db:
            db.execute("INSERT OR REPLACE INTO sync_runs VALUES (?,?,?,?,?)", (scope,offset,total,int(complete),now()))

    def offset(self, scope):
        with self.connect() as db:
            row = db.execute("SELECT next_offset FROM sync_runs WHERE scope=?", (scope,)).fetchone()
            return row[0] if row else 0
