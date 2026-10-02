"""SQLite: action log (who/what/when/why), status log, approved file library."""
from __future__ import annotations

import json
import sqlite3
import threading
import time
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS actions (
  id INTEGER PRIMARY KEY, ts REAL NOT NULL, user TEXT NOT NULL, tool TEXT NOT NULL,
  params TEXT NOT NULL, outcome TEXT NOT NULL, detail TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS status_log (
  id INTEGER PRIMARY KEY, ts REAL NOT NULL, printer TEXT NOT NULL, state TEXT NOT NULL,
  data TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS library (
  file_id TEXT PRIMARY KEY, printer TEXT NOT NULL, name TEXT NOT NULL, sha256 TEXT NOT NULL,
  path TEXT NOT NULL, plates TEXT NOT NULL, added_ts REAL NOT NULL
);
"""


class Store:
    def __init__(self, path: Path):
        path.parent.mkdir(parents=True, exist_ok=True)
        self._db = sqlite3.connect(path, check_same_thread=False, isolation_level=None)
        self._db.execute("PRAGMA journal_mode=WAL")
        self._db.executescript(SCHEMA)
        self._lock = threading.Lock()

    def _exec(self, sql: str, args: tuple = ()) -> list[sqlite3.Row]:
        with self._lock:
            cur = self._db.execute(sql, args)
            return cur.fetchall()

    def log_action(self, user: str, tool: str, params: dict, outcome: str, detail: str = "") -> None:
        self._exec("INSERT INTO actions (ts,user,tool,params,outcome,detail) VALUES (?,?,?,?,?,?)",
                   (time.time(), user, tool, json.dumps(params, default=str), outcome, detail[:500]))

    def recent_actions(self, limit: int = 20) -> list[tuple]:
        return self._exec("SELECT ts,user,tool,params,outcome,detail FROM actions "
                          "ORDER BY id DESC LIMIT ?", (limit,))

    def log_status(self, printer: str, state: str, data: dict) -> None:
        self._exec("INSERT INTO status_log (ts,printer,state,data) VALUES (?,?,?,?)",
                   (time.time(), printer, state, json.dumps(data, default=str)))

    def add_file(self, file_id: str, printer: str, name: str, sha256: str, path: str,
                 plates: dict) -> None:
        self._exec("INSERT OR REPLACE INTO library VALUES (?,?,?,?,?,?,?)",
                   (file_id, printer, name, sha256, path, json.dumps(plates), time.time()))

    def get_file(self, file_id: str) -> dict | None:
        rows = self._exec("SELECT file_id,printer,name,sha256,path,plates FROM library "
                          "WHERE file_id=?", (file_id,))
        if not rows:
            return None
        f = rows[0]
        return {"file_id": f[0], "printer": f[1], "name": f[2], "sha256": f[3],
                "path": f[4], "plates": json.loads(f[5])}

    def list_files(self, printer: str | None = None) -> list[dict]:
        rows = self._exec("SELECT file_id FROM library " +
                          ("WHERE printer=? " if printer else "") + "ORDER BY name",
                          (printer,) if printer else ())
        return [self.get_file(r[0]) for r in rows]
