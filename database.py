import json
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent / "data" / "retailops.db"
STATUSES = ("Open", "In Progress", "Resolved")


def _connect() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    conn = _connect()
    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS tickets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                description TEXT NOT NULL,
                category TEXT NOT NULL,
                issue_type TEXT NOT NULL,
                assigned_to TEXT NOT NULL,
                actions_json TEXT NOT NULL,
                sources_json TEXT NOT NULL,
                matched_rules_json TEXT NOT NULL,
                requires_review INTEGER NOT NULL DEFAULT 0,
                status TEXT NOT NULL DEFAULT 'Open'
                    CHECK (status IN ('Open', 'In Progress', 'Resolved')),
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()
    finally:
        conn.close()


def create_ticket(description: str, result: dict) -> int:
    if not description.strip():
        raise ValueError("Issue description cannot be empty.")

    required = (
        "category",
        "issue_type",
        "assigned_to",
        "actions",
        "sources",
        "matched_rules",
        "requires_review",
    )
    if not all(key in result for key in required):
        raise ValueError("Incomplete classification result.")

    conn = _connect()
    try:
        cursor = conn.execute(
            """
            INSERT INTO tickets (
                description, category, issue_type,
                assigned_to, actions_json, sources_json,
                matched_rules_json, requires_review
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                description.strip(),
                result["category"],
                result["issue_type"],
                result["assigned_to"],
                json.dumps(result["actions"]),
                json.dumps(result["sources"]),
                json.dumps(result["matched_rules"]),
                int(result["requires_review"]),
            ),
        )
        conn.commit()
        return cursor.lastrowid
    finally:
        conn.close()


def list_tickets() -> list[dict]:
    conn = _connect()
    try:
        rows = conn.execute("""
            SELECT
                id, description, category, issue_type,
                assigned_to, status, requires_review,
                created_at, updated_at
            FROM tickets
            ORDER BY id DESC
        """).fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


def get_ticket(ticket_id: int) -> dict | None:
    conn = _connect()
    try:
        row = conn.execute(
            "SELECT * FROM tickets WHERE id = ?",
            (ticket_id,),
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def update_ticket_status(ticket_id: int, new_status: str) -> bool:
    if new_status not in STATUSES:
        raise ValueError(f"Invalid status: {new_status}")

    conn = _connect()
    try:
        cursor = conn.execute(
            """
            UPDATE tickets
            SET status = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (new_status, ticket_id),
        )
        conn.commit()
        return cursor.rowcount == 1
    finally:
        conn.close()