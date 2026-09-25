"""Session-scoped SQLite persistence. Original binary files are never stored."""
from __future__ import annotations
from pathlib import Path
from array import array
from contextlib import contextmanager
import json
import sqlite3
import time
from uuid import uuid4

from .ingest import Section


class Store:
    def __init__(self, path: Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as db:
            db.executescript("""
                PRAGMA foreign_keys = ON;
                CREATE TABLE IF NOT EXISTS documents (
                    id TEXT PRIMARY KEY, session_id TEXT NOT NULL, name TEXT NOT NULL,
                    file_type TEXT NOT NULL, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );
                CREATE INDEX IF NOT EXISTS idx_documents_session ON documents(session_id);
                CREATE TABLE IF NOT EXISTS chunks (
                    id TEXT PRIMARY KEY, document_id TEXT NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
                    ordinal INTEGER NOT NULL, heading TEXT NOT NULL, body TEXT NOT NULL, page INTEGER NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_chunks_document ON chunks(document_id, ordinal);
                CREATE TABLE IF NOT EXISTS embeddings (
                    chunk_id TEXT NOT NULL REFERENCES chunks(id) ON DELETE CASCADE,
                    model TEXT NOT NULL, vector BLOB NOT NULL,
                    PRIMARY KEY(chunk_id, model)
                );
                CREATE TABLE IF NOT EXISTS messages (
                    id TEXT PRIMARY KEY,
                    document_id TEXT NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
                    question TEXT NOT NULL, result TEXT NOT NULL,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );
                CREATE INDEX IF NOT EXISTS idx_messages_document ON messages(document_id, created_at);
                CREATE TABLE IF NOT EXISTS summaries (
                    document_id TEXT NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
                    offset INTEGER NOT NULL, result TEXT NOT NULL,
                    PRIMARY KEY(document_id, offset)
                );
                CREATE TABLE IF NOT EXISTS audit_events (
                    id TEXT PRIMARY KEY,
                    document_id TEXT NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
                    operation TEXT NOT NULL, chunk_ids TEXT NOT NULL,
                    status TEXT NOT NULL, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );
                CREATE TABLE IF NOT EXISTS request_limits (
                    session_id TEXT NOT NULL, kind TEXT NOT NULL,
                    bucket INTEGER NOT NULL, count INTEGER NOT NULL,
                    PRIMARY KEY(session_id, kind, bucket)
                );
            """)

    @contextmanager
    def connect(self):
        db = sqlite3.connect(self.path, timeout=15)
        db.row_factory = sqlite3.Row
        try:
            db.execute("PRAGMA foreign_keys = ON")
            db.execute("PRAGMA secure_delete = ON")
            with db:
                yield db
        finally:
            db.close()

    def add(self, session: str, name: str, kind: str, sections: list[Section]) -> str:
        document_id = str(uuid4())
        with self.connect() as db:
            db.execute("INSERT INTO documents(id,session_id,name,file_type) VALUES(?,?,?,?)", (document_id, session, name, kind))
            db.executemany("INSERT INTO chunks(id,document_id,ordinal,heading,body,page) VALUES(?,?,?,?,?,?)",
                           [(str(uuid4()), document_id, i, s.heading, s.text, s.page) for i, s in enumerate(sections)])
        return document_id

    def list(self, session: str) -> list[dict]:
        with self.connect() as db:
            rows = db.execute("SELECT d.id,d.name,d.file_type,d.created_at,COUNT(c.id) AS section_count FROM documents d LEFT JOIN chunks c ON c.document_id=d.id WHERE d.session_id=? GROUP BY d.id ORDER BY d.created_at DESC,d.rowid DESC", (session,)).fetchall()
        return [dict(row) for row in rows]

    def get(self, session: str, document_id: str) -> dict | None:
        with self.connect() as db:
            row = db.execute("SELECT id,name,file_type,created_at FROM documents WHERE id=? AND session_id=?", (document_id, session)).fetchone()
            if not row:
                return None
            chunks = db.execute("SELECT id,heading,body AS text,page,ordinal FROM chunks WHERE document_id=? ORDER BY ordinal", (document_id,)).fetchall()
        return {**dict(row), "chunks": [dict(chunk) for chunk in chunks]}

    def delete(self, session: str, document_id: str) -> bool:
        with self.connect() as db:
            result = db.execute("DELETE FROM documents WHERE id=? AND session_id=?", (document_id, session))
        return result.rowcount > 0

    def delete_all(self, session: str) -> int:
        with self.connect() as db:
            result = db.execute("DELETE FROM documents WHERE session_id=?", (session,))
            db.execute("DELETE FROM request_limits WHERE session_id=?", (session,))
        return result.rowcount

    def allow_request(self, session: str, kind: str, limit: int, window_seconds: int = 60) -> bool:
        bucket = int(time.time() // window_seconds)
        with self.connect() as db:
            db.execute("DELETE FROM request_limits WHERE session_id=? AND bucket<?", (session, bucket - 1))
            db.execute("""INSERT INTO request_limits(session_id,kind,bucket,count) VALUES(?,?,?,1)
                ON CONFLICT(session_id,kind,bucket) DO UPDATE SET count=count+1""", (session, kind, bucket))
            count = db.execute("SELECT count FROM request_limits WHERE session_id=? AND kind=? AND bucket=?", (session, kind, bucket)).fetchone()[0]
        return count <= limit

    def index_batch(self, session: str, document_id: str, model: str, offset: int, limit: int = 16) -> tuple[int, list[dict]]:
        """Return the requested batch with indexed state for idempotent progress updates."""
        with self.connect() as db:
            rows = db.execute("""SELECT c.id,c.heading,c.body AS text,c.page,e.vector
                FROM chunks c JOIN documents d ON d.id=c.document_id
                LEFT JOIN embeddings e ON e.chunk_id=c.id AND e.model=?
                WHERE d.id=? AND d.session_id=? ORDER BY c.ordinal LIMIT ? OFFSET ?""",
                (model, document_id, session, limit, offset)).fetchall()
            total = db.execute("SELECT COUNT(*) FROM chunks WHERE document_id=?", (document_id,)).fetchone()[0]
        return total, [dict(row) for row in rows]

    def save_embeddings(self, session: str, document_id: str, model: str, items: list[tuple[str, list[float]]]) -> None:
        with self.connect() as db:
            db.executemany("""INSERT OR REPLACE INTO embeddings(chunk_id,model,vector)
                SELECT c.id,?,? FROM chunks c JOIN documents d ON d.id=c.document_id
                WHERE c.id=? AND d.id=? AND d.session_id=?""",
                [(model, array('f', vector).tobytes(), chunk_id, document_id, session) for chunk_id, vector in items])

    def vectors(self, session: str, document_id: str, model: str) -> dict[str, list[float]]:
        with self.connect() as db:
            rows = db.execute("""SELECT e.chunk_id,e.vector FROM embeddings e JOIN chunks c ON c.id=e.chunk_id
                JOIN documents d ON d.id=c.document_id WHERE d.id=? AND d.session_id=? AND e.model=?""",
                (document_id, session, model)).fetchall()
        vectors = {}
        for row in rows:
            value = array('f')
            value.frombytes(row['vector'])
            vectors[row['chunk_id']] = list(value)
        return vectors

    def add_message(self, session: str, document_id: str, question: str, result: dict) -> None:
        with self.connect() as db:
            db.execute("""INSERT INTO messages(id,document_id,question,result)
                SELECT ?,d.id,?,? FROM documents d WHERE d.id=? AND d.session_id=?""",
                (str(uuid4()), question, json.dumps(result), document_id, session))

    def history(self, session: str, document_id: str) -> list[dict]:
        with self.connect() as db:
            rows = db.execute("""SELECT m.id,m.question,m.result,m.created_at FROM messages m
                JOIN documents d ON d.id=m.document_id WHERE d.id=? AND d.session_id=?
                ORDER BY m.rowid DESC LIMIT 100""", (document_id, session)).fetchall()
        return [{"id": row['id'], "question": row['question'], "answer": json.loads(row['result']),
                 "created_at": row['created_at']} for row in reversed(rows)]

    def cached_answer(self, session: str, document_id: str, question: str) -> dict | None:
        with self.connect() as db:
            row = db.execute("""SELECT m.result FROM messages m JOIN documents d ON d.id=m.document_id
                WHERE d.id=? AND d.session_id=? AND m.question=? ORDER BY m.rowid DESC LIMIT 1""",
                (document_id, session, question)).fetchone()
        result = json.loads(row['result']) if row else None
        return result if result and result.get('status') == 'answered' else None

    def save_summary(self, session: str, document_id: str, offset: int, result: dict) -> None:
        with self.connect() as db:
            db.execute("""INSERT OR REPLACE INTO summaries(document_id,offset,result)
                SELECT d.id,?,? FROM documents d WHERE d.id=? AND d.session_id=?""",
                (offset, json.dumps(result), document_id, session))

    def summaries(self, session: str, document_id: str, level: str = "simple") -> list[dict]:
        with self.connect() as db:
            rows = db.execute("""SELECT s.result FROM summaries s JOIN documents d ON d.id=s.document_id
                WHERE d.id=? AND d.session_id=? ORDER BY s.offset""", (document_id, session)).fetchall()
        parts = []
        expected_offset = 0
        for row in rows:
            result = json.loads(row['result'])
            if result.get('level', 'simple') != level:
                continue
            if result.get('start_offset') != expected_offset:
                break
            parts.append(result)
            expected_offset += result.get('coverage_count', 0)
        return parts

    def clear_summaries(self, session: str, document_id: str) -> None:
        with self.connect() as db:
            db.execute("""DELETE FROM summaries WHERE document_id IN
                (SELECT id FROM documents WHERE id=? AND session_id=?)""", (document_id, session))

    def log_event(self, session: str, document_id: str, operation: str, chunk_ids: list[str], status: str) -> None:
        """Keep only template type and source IDs for local audit, never user or document text."""
        with self.connect() as db:
            db.execute("""INSERT INTO audit_events(id,document_id,operation,chunk_ids,status)
                SELECT ?,d.id,?,?,? FROM documents d WHERE d.id=? AND d.session_id=?""",
                (str(uuid4()), operation, json.dumps(chunk_ids), status, document_id, session))
