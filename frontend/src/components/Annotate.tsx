import { useState, useEffect, useCallback } from "react";
import type { PromptPair } from "../api";
import { fetchNextPair, fetchPairById, submitAnnotation, fetchStats } from "../api";
import styles from "./Annotate.module.css";

interface Props {
  annotatorId: string;
  onShowStats: () => void;
  onLogout: () => void;
}

export default function Annotate({ annotatorId, onShowStats, onLogout }: Props) {
  const [pair, setPair] = useState<PromptPair | null>(null);
  const [loading, setLoading] = useState(true);
  const [choice, setChoice] = useState<string | null>(null);
  const [rationale, setRationale] = useState("");
  const [total, setTotal] = useState(0);
  const [completed, setCompleted] = useState(0);
  const [submitting, setSubmitting] = useState(false);

  // Why: Randomize which underlying response maps to label "A" vs "B" per pair.
  // This counters position bias — annotators tend to prefer whichever response appears first.
  const [showAAsA, setShowAAsA] = useState(true);

  // Why: Track history so annotators can revisit previous pairs to review their decisions
  const [history, setHistory] = useState<number[]>([]);
  const [viewingHistory, setViewingHistory] = useState(false);

  const loadStats = useCallback(async () => {
    const stats = await fetchStats();
    setTotal(stats.total_pairs);
    const mine = stats.per_annotator.find((a) => a.annotator_id === annotatorId);
    setCompleted(mine?.count ?? 0);
  }, [annotatorId]);

  const loadNext = useCallback(async () => {
    setLoading(true);
    setChoice(null);
    setRationale("");
    setShowAAsA(Math.random() >= 0.5);
    setViewingHistory(false);

    const [nextPair] = await Promise.all([
      fetchNextPair(annotatorId),
      loadStats(),
    ]);

    setPair(nextPair);
    setLoading(false);
  }, [annotatorId, loadStats]);

  const goBack = useCallback(async () => {
    if (history.length === 0) return;
    setLoading(true);
    setChoice(null);
    setRationale("");
    setShowAAsA(Math.random() >= 0.5);
    setViewingHistory(true);

    const prevId = history[history.length - 1];
    const prevPair = await fetchPairById(prevId);
    setPair(prevPair);
    setHistory((h) => h.slice(0, -1));
    setLoading(false);
  }, [history]);

  useEffect(() => {
    loadNext();
  }, [loadNext]);

  useEffect(() => {
    function handleKey(e: KeyboardEvent) {
      if (e.target instanceof HTMLTextAreaElement) return;
      if (e.key === "a" || e.key === "A") setChoice("A");
      else if (e.key === "b" || e.key === "B") setChoice("B");
      else if (e.key === "t" || e.key === "T") setChoice("tie");
    }
    window.addEventListener("keydown", handleKey);
    return () => window.removeEventListener("keydown", handleKey);
  }, []);

  async function handleSubmit() {
    if (!pair || !choice || submitting) return;
    setSubmitting(true);

    // Why: Map the displayed label back to the actual response field.
    // If response_a was shown as "B" and the user picked "B", they preferred response_a.
    let preferred: string;
    if (choice === "tie") {
      preferred = "tie";
    } else if (choice === "A") {
      preferred = showAAsA ? "response_a" : "response_b";
    } else {
      preferred = showAAsA ? "response_b" : "response_a";
    }

    await submitAnnotation({
      pair_id: pair.id,
      annotator_id: annotatorId,
      preferred,
      rationale: rationale.trim() || null,
      response_a_shown_as: showAAsA ? "A" : "B",
    });

    setHistory((h) => [...h, pair.id]);
    setSubmitting(false);
    loadNext();
  }

  if (loading) return <div className={styles.loading}>Loading...</div>;

  const progress = total > 0 ? (completed / total) * 100 : 0;
  const leftText = showAAsA ? pair?.response_a : pair?.response_b;
  const rightText = showAAsA ? pair?.response_b : pair?.response_a;

  if (!pair) {
    return (
      <div className={styles.done}>
        <h2 className={styles.doneTitle}>All pairs annotated</h2>
        <p>You've completed all {total} pairs. Thank you!</p>
        <button className={styles.navButton} onClick={onShowStats} style={{ marginTop: "1rem" }}>
          View Stats
        </button>
      </div>
    );
  }

  return (
    <div>
      <div className={styles.header}>
        <span className={styles.annotator}>Annotator: {annotatorId}</span>
        <div className={styles.nav}>
          <button className={styles.navButton} onClick={goBack} disabled={history.length === 0} title="Go back to previous pair">
            &#8592; Back
          </button>
          <button className={styles.navButton} onClick={onShowStats}>Stats</button>
          <button className={styles.navButton} onClick={onLogout}>Logout</button>
        </div>
      </div>

      <div className={styles.progressLabel}>{completed} of {total} completed</div>
      <div className={styles.progressBar}>
        <div className={styles.progressFill} style={{ width: `${progress}%` }} />
      </div>

      <div className={styles.prompt}>
        <div className={styles.promptLabel}>Prompt</div>
        <div className={styles.promptText}>{pair.prompt}</div>
      </div>

      <div className={styles.responses}>
        <div className={styles.response}>
          <div className={styles.responseLabel}>
            <span className={styles.badge}>A</span> Response A
          </div>
          <div className={styles.responseText}>{leftText}</div>
        </div>
        <div className={styles.response}>
          <div className={styles.responseLabel}>
            <span className={styles.badge}>B</span> Response B
          </div>
          <div className={styles.responseText}>{rightText}</div>
        </div>
      </div>

      <div className={styles.actions}>
        <button
          className={`${styles.choiceBtn} ${choice === "A" ? styles.selected : ""}`}
          onClick={() => setChoice("A")}
        >
          Prefer A<span className={styles.kbd}>A</span>
        </button>
        <button
          className={`${styles.choiceBtn} ${choice === "tie" ? styles.selected : ""}`}
          onClick={() => setChoice("tie")}
        >
          Tie<span className={styles.kbd}>T</span>
        </button>
        <button
          className={`${styles.choiceBtn} ${choice === "B" ? styles.selected : ""}`}
          onClick={() => setChoice("B")}
        >
          Prefer B<span className={styles.kbd}>B</span>
        </button>
      </div>

      <textarea
        className={styles.rationale}
        placeholder="Optional: explain your reasoning..."
        value={rationale}
        onChange={(e) => setRationale(e.target.value)}
      />

      <div className={styles.submitRow}>
        {viewingHistory ? (
          <button className={styles.submitBtn} onClick={loadNext}>
            Next &#8594;
          </button>
        ) : (
          <button
            className={styles.submitBtn}
            disabled={!choice || submitting}
            onClick={handleSubmit}
          >
            {submitting ? "Submitting..." : "Submit"}
          </button>
        )}
      </div>
    </div>
  );
}
