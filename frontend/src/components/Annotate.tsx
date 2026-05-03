import { useState, useEffect, useCallback } from "react";
import type { PromptPair } from "../api";
import { fetchAllPairs, submitAnnotation, updateAnnotation, fetchStats } from "../api";
import styles from "./Annotate.module.css";

interface Props {
  annotatorId: string;
  onShowStats: () => void;
  onLogout: () => void;
}

interface Result {
  preferred: string;     // "response_a" | "response_b" | "tie"
  rationale: string;
  showAAsA: boolean;
}

export default function Annotate({ annotatorId, onShowStats, onLogout }: Props) {
  const [pairs, setPairs] = useState<PromptPair[]>([]);
  const [results, setResults] = useState<(Result | null)[]>([]);
  const [index, setIndex] = useState(0);
  const [loading, setLoading] = useState(true);

  // Why: Position randomization is decided once per pair and stored in the result,
  // so it stays consistent across back/forward navigation.
  const [showAAsA, setShowAAsA] = useState(true);
  const [choice, setChoice] = useState<string | null>(null);
  const [rationale, setRationale] = useState("");

  useEffect(() => {
    (async () => {
      const allPairs = await fetchAllPairs();
      const stats = await fetchStats();
      const mine = stats.per_annotator.find((a) => a.annotator_id === annotatorId);
      const completedCount = mine?.count ?? 0;

      setPairs(allPairs);
      setResults(new Array(allPairs.length).fill(null));
      setIndex(completedCount);
      setShowAAsA(true);
      setLoading(false);
    })();
  }, [annotatorId]);

  const displayChoice = useCallback((preferred: string, flipA: boolean): string | null => {
    if (preferred === "tie") return "tie";
    if (preferred === "response_a") return flipA ? "A" : "B";
    return flipA ? "B" : "A";
  }, []);

  const toPreferred = useCallback((ch: string, flipA: boolean): string => {
    if (ch === "tie") return "tie";
    if (ch === "A") return flipA ? "response_a" : "response_b";
    return flipA ? "response_b" : "response_a";
  }, []);

  function saveToResults(preferred: string, rat: string, flip: boolean) {
    setResults((prev) => {
      const copy = [...prev];
      copy[index] = { preferred, rationale: rat, showAAsA: flip };
      return copy;
    });
  }

  async function handleNext() {
    if (!choice) return;

    const pair = pairs[index];
    const preferred = toPreferred(choice, showAAsA);
    const existing = results[index];

    saveToResults(preferred, rationale, showAAsA);

    if (existing) {
      await updateAnnotation({
        pair_id: pair.id,
        annotator_id: annotatorId,
        preferred,
        rationale: rationale.trim() || null,
        response_a_shown_as: showAAsA ? "A" : "B",
      });
    } else {
      await submitAnnotation({
        pair_id: pair.id,
        annotator_id: annotatorId,
        preferred,
        rationale: rationale.trim() || null,
        response_a_shown_as: showAAsA ? "A" : "B",
      });
    }

    const nextIdx = index + 1;
    setIndex(nextIdx);

    if (nextIdx < pairs.length) {
      const nextResult = results[nextIdx];
      if (nextResult) {
        setShowAAsA(nextResult.showAAsA);
        setChoice(displayChoice(nextResult.preferred, nextResult.showAAsA));
        setRationale(nextResult.rationale);
      } else {
        setShowAAsA(true);
        setChoice(null);
        setRationale("");
      }
    }
  }

  async function handleBack() {
    if (index <= 0) return;

    if (choice) {
      const pair = pairs[index];
      const preferred = toPreferred(choice, showAAsA);
      const existing = results[index];
      saveToResults(preferred, rationale, showAAsA);

      if (existing) {
        await updateAnnotation({
          pair_id: pair.id,
          annotator_id: annotatorId,
          preferred,
          rationale: rationale.trim() || null,
          response_a_shown_as: showAAsA ? "A" : "B",
        });
      }
    }

    const prevIdx = index - 1;
    const prevResult = results[prevIdx];
    setIndex(prevIdx);

    if (prevResult) {
      setShowAAsA(prevResult.showAAsA);
      setChoice(displayChoice(prevResult.preferred, prevResult.showAAsA));
      setRationale(prevResult.rationale);
    } else {
      setShowAAsA(true);
      setChoice(null);
      setRationale("");
    }
  }

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

  if (loading) return <div className={styles.loading}>Loading...</div>;

  const total = pairs.length;
  const completed = results.filter((r) => r !== null).length;
  const progress = total > 0 ? (completed / total) * 100 : 0;

  if (index >= total) {
    return (
      <div className={styles.done}>
        <h2 className={styles.doneTitle}>All pairs annotated</h2>
        <p>You've completed all {total} pairs. Thank you!</p>
        <div className={styles.doneActions}>
          {total > 0 && (
            <button className={styles.navButton} onClick={handleBack}>
              &#8592; Review Answers
            </button>
          )}
          <button className={styles.navButton} onClick={onShowStats}>
            View Stats
          </button>
        </div>
      </div>
    );
  }

  const pair = pairs[index];
  const leftText = showAAsA ? pair.response_a : pair.response_b;
  const rightText = showAAsA ? pair.response_b : pair.response_a;

  return (
    <div>
      <div className={styles.header}>
        <span className={styles.annotator}>Annotator: {annotatorId}</span>
        <div className={styles.nav}>
          <button className={styles.navButton} onClick={onShowStats}>Stats</button>
          <button className={styles.navButton} onClick={onLogout}>Logout</button>
        </div>
      </div>

      <div className={styles.progressLabel}>
        Question {index + 1} of {total}
      </div>
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
        <button
          className={styles.navButton}
          disabled={index <= 0}
          onClick={handleBack}
        >
          &#8592; Back
        </button>
        <button
          className={styles.submitBtn}
          disabled={!choice}
          onClick={handleNext}
        >
          {index < total - 1 ? "Next" : "Finish"}
        </button>
      </div>
    </div>
  );
}
