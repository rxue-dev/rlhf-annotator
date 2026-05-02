import sqlite3
import os
from datetime import datetime, timezone

DB_PATH = os.path.join(os.path.dirname(__file__), "annotations.db")


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db() -> None:
    conn = get_connection()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS prompt_pairs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            prompt TEXT NOT NULL,
            response_a TEXT NOT NULL,
            response_b TEXT NOT NULL,
            model_a TEXT NOT NULL,
            model_b TEXT NOT NULL,
            created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS annotations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            pair_id INTEGER NOT NULL REFERENCES prompt_pairs(id),
            annotator_id TEXT NOT NULL,
            preferred TEXT NOT NULL CHECK (preferred IN ('response_a', 'response_b', 'tie')),
            rationale TEXT,
            response_a_shown_as TEXT NOT NULL CHECK (response_a_shown_as IN ('A', 'B')),
            created_at TEXT NOT NULL
        );

        CREATE INDEX IF NOT EXISTS idx_annotations_pair_id ON annotations(pair_id);
        CREATE INDEX IF NOT EXISTS idx_annotations_annotator_id ON annotations(annotator_id);
    """)
    conn.commit()

    # Why: Only seed when DB is empty so restarts don't duplicate data
    count = conn.execute("SELECT COUNT(*) FROM prompt_pairs").fetchone()[0]
    if count == 0:
        _seed_data(conn)
    conn.close()


def _seed_data(conn: sqlite3.Connection) -> None:
    """Insert 10 sample prompt/response pairs for development and demo use."""
    now = datetime.now(timezone.utc).isoformat()
    pairs = [
        (
            "Explain quantum computing to a 10-year-old.",
            "Imagine you have a magical coin that can be both heads and tails at the same time. That's kind of like a qubit in a quantum computer! Regular computers use bits that are either 0 or 1, but quantum computers use qubits that can be both at once. This lets them solve certain puzzles much faster than regular computers.",
            "Quantum computing is a type of computation that harnesses quantum mechanical phenomena like superposition and entanglement. Unlike classical bits, qubits can exist in multiple states simultaneously, enabling parallel processing of information. This allows quantum computers to solve certain classes of problems exponentially faster than classical computers.",
            "claude-3-haiku", "gpt-4o-mini",
        ),
        (
            "Write a haiku about debugging code.",
            "Semicolon lost\nThree hours searching the void\nFound it on line two",
            "Bug hides in the code\nPrintf reveals the truth now\nFixed with one changed line",
            "claude-3-sonnet", "gpt-4o",
        ),
        (
            "What are the ethical implications of AI-generated art?",
            "AI art raises questions about authorship, consent, and economic impact. Artists whose work trained these models didn't consent to that use. It could devalue human creativity while democratizing art creation. We need frameworks that protect artists while allowing innovation.",
            "The ethical implications are multifaceted. First, there's the question of training data consent — most models used copyrighted works without permission. Second, there's economic displacement of artists. Third, there's the philosophical question of whether AI can truly create art or merely recombine patterns. However, AI tools also lower barriers to creative expression for people who lack traditional artistic training.",
            "claude-3-opus", "gpt-4",
        ),
        (
            "Explain the difference between TCP and UDP.",
            "TCP is like sending a registered letter — you get confirmation it arrived, and if it didn't, it gets resent. UDP is like shouting into a crowd — fast, but no guarantee anyone heard you. TCP is reliable but slower; UDP is fast but unreliable. Use TCP for web pages and email, UDP for video streaming and games where speed matters more than perfection.",
            "TCP (Transmission Control Protocol) establishes a connection, ensures ordered delivery, and retransmits lost packets. UDP (User Datagram Protocol) is connectionless and does not guarantee delivery or ordering. TCP has higher overhead due to its reliability mechanisms, while UDP has lower latency. TCP is used for HTTP, FTP, and SMTP; UDP is used for DNS, VoIP, and streaming.",
            "claude-3-haiku", "gpt-4o-mini",
        ),
        (
            "What would happen if the Moon disappeared?",
            "Earth's tides would shrink to about one-third their current size (only solar tides would remain). Earth's axial tilt would become unstable over millions of years, causing extreme climate swings. Nights would be much darker. Many nocturnal animals that rely on moonlight would be affected. The length of our day would also change over time since the Moon's tidal forces are gradually slowing Earth's rotation.",
            "If the Moon vanished, tides would be much smaller since they'd only come from the Sun. Nights would be darker. Over long periods, Earth's tilt could wobble wildly without the Moon's stabilizing gravity, leading to extreme seasons. Many animals that navigate or hunt by moonlight would struggle. Culturally, we'd lose a major source of human inspiration in art, religion, and timekeeping.",
            "gpt-4", "claude-3-sonnet",
        ),
        (
            "Write a Python function to check if a string is a palindrome.",
            "```python\ndef is_palindrome(s: str) -> bool:\n    cleaned = ''.join(c.lower() for c in s if c.isalnum())\n    return cleaned == cleaned[::-1]\n```\nThis handles mixed case and ignores non-alphanumeric characters.",
            "```python\ndef is_palindrome(text):\n    # Remove spaces and convert to lowercase\n    text = text.replace(' ', '').lower()\n    # Compare with reversed version\n    left = 0\n    right = len(text) - 1\n    while left < right:\n        if text[left] != text[right]:\n            return False\n        left += 1\n        right -= 1\n    return True\n```\nUses two pointers for O(1) extra space.",
            "claude-3-opus", "gpt-4o",
        ),
        (
            "Should we colonize Mars? Give arguments for and against.",
            "For: It provides a backup for humanity against extinction-level events on Earth. It drives technological innovation. It could unlock scientific discoveries about planetary formation. Against: The cost is enormous and could fund solutions to Earth's problems. Mars is hostile — thin atmosphere, radiation, no magnetic field. The ethical question of potentially contaminating Mars if microbial life exists there. Psychologically, long isolation could be devastating for colonists.",
            "For colonization: Ensures long-term species survival, inspires scientific progress, offers resource opportunities. Against: Trillions in costs with uncertain returns, extreme health risks from radiation and low gravity, potential ecological destruction of Mars, ethical issues around who gets to go. On balance, I believe robotic exploration should precede any human settlement to better understand the risks.",
            "gpt-4", "claude-3-sonnet",
        ),
        (
            "Explain the CAP theorem in distributed systems.",
            "CAP theorem states that a distributed system can only guarantee two of three properties: Consistency (all nodes see the same data), Availability (every request gets a response), and Partition tolerance (the system works despite network splits). Since network partitions are unavoidable in practice, you're really choosing between CP (consistent but may reject requests during partitions) and AP (always responds but may return stale data).",
            "The CAP theorem, proposed by Eric Brewer, says distributed systems must trade off between Consistency, Availability, and Partition tolerance — you can have at most two. In reality, since partitions happen, the choice is between consistency and availability during failures. Databases like MongoDB choose CP, while Cassandra chooses AP. Modern systems often use tunable consistency to pick different tradeoffs per operation.",
            "claude-3-opus", "gpt-4o",
        ),
        (
            "What makes a good code review?",
            "A good code review focuses on correctness, readability, and maintainability — not style preferences. Review the design and logic, not just syntax. Be specific: instead of 'this is confusing,' say 'this function does X and Y — consider splitting them.' Ask questions rather than making demands. Respond promptly. Remember that the goal is to ship better code, not to prove who's smarter.",
            "Good code reviews should check for: bugs and edge cases, security vulnerabilities, performance issues, test coverage, documentation needs, and adherence to team conventions. Provide constructive feedback with suggestions, not just criticism. Keep reviews small (under 400 lines if possible). Use automation for style enforcement so humans can focus on logic. Acknowledge good work too — positive feedback matters.",
            "gpt-4o", "claude-3-haiku",
        ),
        (
            "Explain gradient descent like I'm a hiker.",
            "You're on a mountain in thick fog — you can't see the valley below, only the ground right around your feet. To get down, you feel which direction slopes downward most steeply and take a step that way. That's gradient descent. The step size is your 'learning rate.' Too big and you might overshoot the valley and end up on another peak. Too small and you'll take forever. Sometimes you land in a small dip that isn't the lowest valley — that's a local minimum.",
            "Imagine you're blindfolded on a hilly landscape trying to reach the lowest point. You can feel the slope under your feet. Each step, you move downhill in the steepest direction. Your step size matters: too large and you jump over valleys, too small and you barely move. Sometimes you get stuck in a small valley that's not the deepest one (local minimum). Techniques like momentum help — imagine rolling a ball that carries speed from previous steps to push through small bumps.",
            "claude-3-sonnet", "gpt-4",
        ),
    ]
    conn.executemany(
        """INSERT INTO prompt_pairs (prompt, response_a, response_b, model_a, model_b, created_at)
           VALUES (?, ?, ?, ?, ?, ?)""",
        [(p, ra, rb, ma, mb, now) for p, ra, rb, ma, mb in pairs],
    )
    conn.commit()
