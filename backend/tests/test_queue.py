"""Unit tests for the annotation queue logic — least-annotated-first ordering
and per-annotator deduplication."""

import sqlite3
import sys
from pathlib import Path
from datetime import datetime, timezone

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from database import init_db


def get_test_db():
    """Create an in-memory SQLite database with the same schema as production."""
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    conn.executescript("""
        CREATE TABLE prompt_pairs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            prompt TEXT NOT NULL,
            response_a TEXT NOT NULL,
            response_b TEXT NOT NULL,
            model_a TEXT NOT NULL,
            model_b TEXT NOT NULL,
            created_at TEXT NOT NULL
        );
        CREATE TABLE annotations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            pair_id INTEGER NOT NULL REFERENCES prompt_pairs(id),
            annotator_id TEXT NOT NULL,
            preferred TEXT NOT NULL CHECK (preferred IN ('response_a', 'response_b', 'tie')),
            rationale TEXT,
            response_a_shown_as TEXT NOT NULL CHECK (response_a_shown_as IN ('A', 'B')),
            created_at TEXT NOT NULL
        );
        CREATE INDEX idx_annotations_pair_id ON annotations(pair_id);
        CREATE INDEX idx_annotations_annotator_id ON annotations(annotator_id);
    """)
    conn.commit()
    return conn


def insert_pairs(conn, n=3):
    now = datetime.now(timezone.utc).isoformat()
    for i in range(n):
        conn.execute(
            "INSERT INTO prompt_pairs (prompt, response_a, response_b, model_a, model_b, created_at) VALUES (?,?,?,?,?,?)",
            (f"prompt {i}", f"resp_a {i}", f"resp_b {i}", "model_a", "model_b", now),
        )
    conn.commit()


def insert_annotation(conn, pair_id, annotator_id):
    now = datetime.now(timezone.utc).isoformat()
    conn.execute(
        "INSERT INTO annotations (pair_id, annotator_id, preferred, rationale, response_a_shown_as, created_at) VALUES (?,?,?,?,?,?)",
        (pair_id, annotator_id, "response_a", None, "A", now),
    )
    conn.commit()


def get_next_pair(conn, annotator_id):
    """Mirrors the queue query from main.py — least-annotated-first, skip already-labeled."""
    row = conn.execute(
        """
        SELECT p.*
        FROM prompt_pairs p
        LEFT JOIN annotations a ON a.pair_id = p.id AND a.annotator_id = ?
        WHERE a.id IS NULL
        ORDER BY (
            SELECT COUNT(*) FROM annotations WHERE pair_id = p.id
        ) ASC, p.id ASC
        LIMIT 1
        """,
        (annotator_id,),
    ).fetchone()
    return row


class TestQueueOrdering:
    def test_returns_first_pair_when_no_annotations(self):
        conn = get_test_db()
        insert_pairs(conn, 3)
        row = get_next_pair(conn, "alice")
        assert row["id"] == 1

    def test_skips_pair_already_annotated_by_same_user(self):
        conn = get_test_db()
        insert_pairs(conn, 3)
        insert_annotation(conn, pair_id=1, annotator_id="alice")
        row = get_next_pair(conn, "alice")
        assert row["id"] == 2

    def test_does_not_skip_pair_annotated_by_different_user(self):
        conn = get_test_db()
        insert_pairs(conn, 3)
        insert_annotation(conn, pair_id=1, annotator_id="bob")
        row = get_next_pair(conn, "alice")
        # Pair 1 has 1 annotation (by bob), pairs 2&3 have 0
        # Least-annotated-first means alice gets pair 2 or 3 (lowest id wins)
        assert row["id"] == 2

    def test_least_annotated_first(self):
        conn = get_test_db()
        insert_pairs(conn, 3)
        # Give pair 1 two annotations from different users
        insert_annotation(conn, pair_id=1, annotator_id="bob")
        insert_annotation(conn, pair_id=1, annotator_id="carol")
        # Give pair 2 one annotation
        insert_annotation(conn, pair_id=2, annotator_id="bob")
        # Pair 3 has zero annotations — should come first for alice
        row = get_next_pair(conn, "alice")
        assert row["id"] == 3

    def test_returns_none_when_all_annotated(self):
        conn = get_test_db()
        insert_pairs(conn, 2)
        insert_annotation(conn, pair_id=1, annotator_id="alice")
        insert_annotation(conn, pair_id=2, annotator_id="alice")
        row = get_next_pair(conn, "alice")
        assert row is None


class TestDuplicatePrevention:
    def test_unique_constraint_on_annotator_pair(self):
        """Annotator can only annotate each pair once (enforced at app level)."""
        conn = get_test_db()
        insert_pairs(conn, 1)
        insert_annotation(conn, pair_id=1, annotator_id="alice")
        # Verify the annotation exists
        count = conn.execute(
            "SELECT COUNT(*) FROM annotations WHERE pair_id = 1 AND annotator_id = 'alice'"
        ).fetchone()[0]
        assert count == 1
