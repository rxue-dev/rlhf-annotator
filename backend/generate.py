"""Generate prompt/response pairs using the Anthropic API.

# Why: Using real LLM-generated responses makes the annotation tool produce
# realistic training data, rather than relying on hardcoded examples.
# We generate two responses with different system prompts (personas) to create
# natural variation — the same approach used in real RLHF data collection.
"""

import json
import urllib.request
import urllib.error
from datetime import datetime, timezone
from database import get_connection

ANTHROPIC_API_URL = "https://api.anthropic.com/v1/messages"

# Why: Two distinct personas produce meaningfully different responses to compare,
# simulating what happens when you collect outputs from different models or configs.
PERSONA_A = "You are a helpful, concise assistant. Give clear and direct answers."
PERSONA_B = "You are a thorough, detailed assistant. Give comprehensive answers with examples."

PROMPT_GENERATION_SYSTEM = """You are a prompt designer for an RLHF annotation dataset.
Generate diverse, interesting prompts that would produce meaningfully different responses
from different AI assistants. Each prompt should be a clear question or task.

Return ONLY a JSON array of strings, no other text. Example:
["What is the trolley problem?", "Write a function to reverse a linked list"]"""


def _call_anthropic(api_key, system, user_message, max_tokens=1024):
    """Make a direct HTTP request to the Anthropic Messages API."""
    body = json.dumps({
        "model": "claude-sonnet-4-20250514",
        "max_tokens": max_tokens,
        "system": system,
        "messages": [{"role": "user", "content": user_message}],
    }).encode("utf-8")

    req = urllib.request.Request(
        ANTHROPIC_API_URL,
        data=body,
        headers={
            "Content-Type": "application/json",
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
        },
    )

    try:
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return data["content"][0]["text"]
    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8")
        raise RuntimeError(f"Anthropic API error ({e.code}): {error_body}")


def generate_prompts(api_key, topic, count):
    """Generate a list of prompts on a given topic."""
    user_msg = f"Generate {count} diverse prompts about: {topic}"
    raw = _call_anthropic(api_key, PROMPT_GENERATION_SYSTEM, user_msg)

    # Why: The model may wrap JSON in markdown code fences
    cleaned = raw.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.split("\n", 1)[1]
        cleaned = cleaned.rsplit("```", 1)[0]

    return json.loads(cleaned)


def generate_response_pair(api_key, prompt):
    """Generate two responses to a prompt using different personas."""
    resp_a = _call_anthropic(api_key, PERSONA_A, prompt)
    resp_b = _call_anthropic(api_key, PERSONA_B, prompt)
    return resp_a, resp_b


def generate_and_store(api_key, topic, count):
    """Generate prompt/response pairs and insert them into the database.

    Returns the number of pairs successfully created.
    """
    prompts = generate_prompts(api_key, topic, count)
    now = datetime.now(timezone.utc).isoformat()
    conn = get_connection()
    created = 0

    for prompt in prompts:
        try:
            resp_a, resp_b = generate_response_pair(api_key, prompt)
            conn.execute(
                """INSERT INTO prompt_pairs
                   (prompt, response_a, response_b, model_a, model_b, created_at)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (prompt, resp_a, resp_b, "claude-concise", "claude-detailed", now),
            )
            conn.commit()
            created += 1
        except Exception:
            continue

    conn.close()
    return created
