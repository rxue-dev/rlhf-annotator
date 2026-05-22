# RLHF Annotation Tool

A full-stack human annotation tool for pairwise LLM response preference comparison. This mirrors what real RLHF (Reinforcement Learning from Human Feedback) data collection systems do — given a prompt and two model responses, a human annotator chooses which response is better, producing the preference pairs that train reward models.


## DEMO
<img width="1211" height="798" alt="Screenshot 2026-05-22 at 12 44 01 PM" src="https://github.com/user-attachments/assets/7a81f0f8-b0a0-4852-9dde-5e573e4d8e81" />

<img width="747" height="491" alt="Screenshot 2026-05-22 at 12 43 22 PM" src="https://github.com/user-attachments/assets/635227f4-910a-40d1-98b8-336dabf9012d" />

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                     Browser (React)                      │
│                                                          │
│  ┌──────────┐  ┌────────────────────┐  ┌──────────────┐ │
│  │  Login    │→ │  Annotation View   │→ │  Stats Page  │ │
│  │  Screen   │  │                    │  │              │ │
│  └──────────┘  │  ┌──────┐┌──────┐  │  │  Per-user    │ │
│                │  │Resp A││Resp B│  │  │  counts      │ │
│    localStorage│  └──────┘└──────┘  │  │              │ │
│    (annotator  │  [A] [Tie] [B]     │  │  Export JSONL │ │
│     ID)        │  [Rationale]       │  └──────────────┘ │
│                └────────────────────┘                    │
└───────────────────────┬─────────────────────────────────┘
                        │ HTTP (JSON)
                        ▼
┌─────────────────────────────────────────────────────────┐
│                   FastAPI Backend                         │
│                                                          │
│  GET  /pairs/next?annotator_id=...                       │
│  POST /annotations                                       │
│  GET  /stats                                             │
│  GET  /export                                            │
└───────────────────────┬─────────────────────────────────┘
                        │ sqlite3
                        ▼
┌─────────────────────────────────────────────────────────┐
│                   SQLite Database                         │
│                                                          │
│  prompt_pairs: id, prompt, response_a, response_b,       │
│                model_a, model_b, created_at               │
│                                                          │
│  annotations:  id, pair_id, annotator_id, preferred,     │
│                rationale, response_a_shown_as, created_at │
└─────────────────────────────────────────────────────────┘
```

## Run Locally

### Backend

```bash
cd backend
pip install -r requirements.txt
python -m uvicorn main:app --reload
```

The backend runs on `http://localhost:8000`. The SQLite database is created automatically and seeded with 10 sample prompt/response pairs on first run.

### Frontend

```bash
cd frontend
npm install
npm run dev
```

The frontend runs on `http://localhost:5173`. Open it in your browser, enter an annotator name, and start labeling.

## Key Design Decisions

### Why pairwise comparison over rating scales?

Pairwise comparison ("which is better, A or B?") produces more reliable data than absolute rating scales ("rate this 1-5"). Humans are inconsistent at mapping quality to numbers but good at relative judgments. This is why Anthropic, OpenAI, and most RLHF pipelines use pairwise preferences — they map directly to the Bradley-Terry model used to train reward models.

### Why position randomization?

Annotators exhibit position bias — they tend to prefer the first response they read. By randomly assigning which underlying model response appears as "A" vs "B" for each pair (and recording this in `response_a_shown_as`), we can detect and correct for this bias in downstream analysis. Without this, training data would systematically favor whichever model happened to be listed first.

### Why JSONL export format?

JSONL (one JSON object per line) is the standard format for preference datasets in the RLHF ecosystem. Each line contains `prompt`, `chosen`, `rejected`, and metadata fields — the same schema used by Anthropic's HH-RLHF dataset. This means exported data can feed directly into training pipelines (e.g., DPO or reward model training) without format conversion.

### Why least-annotated-first queue?

A naive random or sequential queue leads to uneven coverage — some pairs get many annotations while others get none. Least-annotated-first ensures every pair gets at least one annotation before any pair gets a second, maximizing dataset coverage with limited annotator time. The queue also excludes pairs the current annotator has already labeled, preventing duplicate work.
