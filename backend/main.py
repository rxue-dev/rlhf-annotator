from typing import Optional
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from datetime import datetime, timezone
import json
import io

from database import get_connection, init_db

app = FastAPI(title="RLHF Annotation Tool")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class AnnotationRequest(BaseModel):
    pair_id: int
    annotator_id: str
    preferred: str  # "response_a", "response_b", or "tie"
    rationale: Optional[str] = None
    response_a_shown_as: str  # "A" or "B"


@app.on_event("startup")
def startup():
    init_db()


@app.get("/pairs/next")
def get_next_pair(annotator_id: str = Query(...)):
    """Return the next unannotated pair for this annotator.

    # Why: Least-annotated-first queue ensures balanced coverage across all pairs,
    # preventing popular/easy pairs from being over-annotated while others are skipped.
    """
    conn = get_connection()
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
    conn.close()

    if row is None:
        return {"pair": None}

    return {
        "pair": {
            "id": row["id"],
            "prompt": row["prompt"],
            "response_a": row["response_a"],
            "response_b": row["response_b"],
            "model_a": row["model_a"],
            "model_b": row["model_b"],
        }
    }


@app.get("/pairs/all")
def get_all_pairs():
    conn = get_connection()
    rows = conn.execute("SELECT * FROM prompt_pairs ORDER BY id ASC").fetchall()
    conn.close()
    return {
        "pairs": [
            {
                "id": r["id"],
                "prompt": r["prompt"],
                "response_a": r["response_a"],
                "response_b": r["response_b"],
                "model_a": r["model_a"],
                "model_b": r["model_b"],
            }
            for r in rows
        ]
    }


@app.get("/pairs/{pair_id}")
def get_pair(pair_id: int):
    conn = get_connection()
    row = conn.execute("SELECT * FROM prompt_pairs WHERE id = ?", (pair_id,)).fetchone()
    conn.close()
    if row is None:
        return {"pair": None}
    return {
        "pair": {
            "id": row["id"],
            "prompt": row["prompt"],
            "response_a": row["response_a"],
            "response_b": row["response_b"],
            "model_a": row["model_a"],
            "model_b": row["model_b"],
        }
    }


@app.post("/annotations")
def create_annotation(req: AnnotationRequest):
    conn = get_connection()

    # Why: Prevent duplicate annotations from the same annotator on the same pair
    existing = conn.execute(
        "SELECT id FROM annotations WHERE pair_id = ? AND annotator_id = ?",
        (req.pair_id, req.annotator_id),
    ).fetchone()
    if existing:
        conn.close()
        return {"status": "already_annotated", "id": existing["id"]}

    now = datetime.now(timezone.utc).isoformat()
    cursor = conn.execute(
        """INSERT INTO annotations (pair_id, annotator_id, preferred, rationale, response_a_shown_as, created_at)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (req.pair_id, req.annotator_id, req.preferred, req.rationale, req.response_a_shown_as, now),
    )
    conn.commit()
    annotation_id = cursor.lastrowid
    conn.close()

    return {"status": "created", "id": annotation_id}


@app.put("/annotations")
def update_annotation(req: AnnotationRequest):
    conn = get_connection()
    now = datetime.now(timezone.utc).isoformat()
    conn.execute(
        """UPDATE annotations SET preferred = ?, rationale = ?, response_a_shown_as = ?, created_at = ?
           WHERE pair_id = ? AND annotator_id = ?""",
        (req.preferred, req.rationale, req.response_a_shown_as, now, req.pair_id, req.annotator_id),
    )
    conn.commit()
    conn.close()
    return {"status": "updated"}


@app.get("/annotations/for-pair")
def get_annotation_for_pair(pair_id: int = Query(...), annotator_id: str = Query(...)):
    conn = get_connection()
    row = conn.execute(
        "SELECT preferred, rationale, response_a_shown_as FROM annotations WHERE pair_id = ? AND annotator_id = ?",
        (pair_id, annotator_id),
    ).fetchone()
    conn.close()
    if row is None:
        return {"annotation": None}
    return {
        "annotation": {
            "preferred": row["preferred"],
            "rationale": row["rationale"],
            "response_a_shown_as": row["response_a_shown_as"],
        }
    }


@app.get("/stats")
def get_stats():
    conn = get_connection()
    total = conn.execute("SELECT COUNT(*) FROM prompt_pairs").fetchone()[0]
    annotated = conn.execute(
        "SELECT COUNT(DISTINCT pair_id) FROM annotations"
    ).fetchone()[0]
    per_annotator = conn.execute(
        "SELECT annotator_id, COUNT(*) as count FROM annotations GROUP BY annotator_id ORDER BY count DESC"
    ).fetchall()
    conn.close()

    return {
        "total_pairs": total,
        "annotated_pairs": annotated,
        "per_annotator": [{"annotator_id": r["annotator_id"], "count": r["count"]} for r in per_annotator],
    }


@app.get("/export")
def export_annotations():
    """Export all annotations as JSONL compatible with Anthropic's HH-RLHF schema.

    # Why: JSONL (one JSON object per line) is the standard format for HH-RLHF datasets.
    # Each record contains the prompt, chosen/rejected responses, and metadata,
    # so it can feed directly into a preference-learning training pipeline.
    """
    conn = get_connection()
    rows = conn.execute(
        """
        SELECT a.*, p.prompt, p.response_a, p.response_b, p.model_a, p.model_b
        FROM annotations a
        JOIN prompt_pairs p ON p.id = a.pair_id
        ORDER BY a.created_at ASC
        """
    ).fetchall()
    conn.close()

    buffer = io.StringIO()
    for row in rows:
        if row["preferred"] == "response_a":
            chosen, rejected = row["response_a"], row["response_b"]
            chosen_model, rejected_model = row["model_a"], row["model_b"]
        elif row["preferred"] == "response_b":
            chosen, rejected = row["response_b"], row["response_a"]
            chosen_model, rejected_model = row["model_b"], row["model_a"]
        else:
            chosen, rejected = row["response_a"], row["response_b"]
            chosen_model, rejected_model = row["model_a"], row["model_b"]

        shown_as = row["response_a_shown_as"]
        if row["preferred"] == "tie":
            annotator_choice = "tie"
        elif row["preferred"] == "response_a":
            annotator_choice = shown_as
        else:
            annotator_choice = "B" if shown_as == "A" else "A"

        record = {
            "prompt": row["prompt"],
            "chosen": chosen,
            "rejected": rejected,
            "annotator_choice": annotator_choice,
            "chosen_model": chosen_model,
            "rejected_model": rejected_model,
            "is_tie": row["preferred"] == "tie",
            "annotator_id": row["annotator_id"],
            "rationale": row["rationale"],
            "created_at": row["created_at"],
        }
        buffer.write(json.dumps(record) + "\n")

    buffer.seek(0)
    return StreamingResponse(
        buffer,
        media_type="application/jsonl",
        headers={"Content-Disposition": "attachment; filename=annotations.jsonl"},
    )
