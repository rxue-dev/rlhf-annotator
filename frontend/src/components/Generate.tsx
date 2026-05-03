import { useState } from "react";
import { generatePairs, resetSession } from "../api";
import styles from "./Generate.module.css";

const API_KEY_STORAGE = "rlhf_anthropic_key";

interface Props {
  annotatorId: string;
  onDone: () => void;
  onBack: () => void;
}

export default function Generate({ annotatorId, onDone, onBack }: Props) {
  const [apiKey, setApiKey] = useState(() => localStorage.getItem(API_KEY_STORAGE) || "");
  const [topic, setTopic] = useState("");
  const [count, setCount] = useState(5);
  const [generating, setGenerating] = useState(false);
  const [result, setResult] = useState<{ ok: boolean; message: string } | null>(null);

  async function handleGenerate() {
    if (!apiKey.trim() || !topic.trim()) return;
    setGenerating(true);
    setResult(null);

    // Why: Persist API key in localStorage so the user doesn't re-enter it each time.
    // The key is only stored client-side and sent per-request — never saved on the server.
    localStorage.setItem(API_KEY_STORAGE, apiKey);

    const res = await generatePairs({ api_key: apiKey, topic, count });

    if (res.status === "ok") {
      setResult({ ok: true, message: `Generated ${res.created} new pairs.` });
    } else {
      setResult({ ok: false, message: res.message || "Generation failed." });
    }
    setGenerating(false);
  }

  async function handleStartAnnotating() {
    await resetSession(annotatorId);
    onDone();
  }

  return (
    <div className={styles.container}>
      <div className={styles.header}>
        <h2 className={styles.title}>Generate New Pairs</h2>
        <button className={styles.backBtn} onClick={onBack}>Back</button>
      </div>

      <div className={styles.form}>
        <div>
          <div className={styles.label}>Anthropic API Key</div>
          <input
            className={styles.input}
            type="password"
            placeholder="sk-ant-..."
            value={apiKey}
            onChange={(e) => setApiKey(e.target.value)}
          />
          <div className={styles.hint}>Stored locally in your browser only</div>
        </div>

        <div>
          <div className={styles.label}>Topic</div>
          <input
            className={styles.input}
            type="text"
            placeholder="e.g. machine learning, cooking, philosophy..."
            value={topic}
            onChange={(e) => setTopic(e.target.value)}
          />
        </div>

        <div>
          <div className={styles.label}>Number of Pairs</div>
          <input
            className={`${styles.input} ${styles.small}`}
            type="number"
            min={1}
            max={20}
            value={count}
            onChange={(e) => setCount(Math.max(1, Math.min(20, Number(e.target.value))))}
          />
        </div>

        <button
          className={styles.generateBtn}
          disabled={generating || !apiKey.trim() || !topic.trim()}
          onClick={handleGenerate}
        >
          {generating ? "Generating..." : "Generate Pairs"}
        </button>
      </div>

      {generating && (
        <div className={styles.status}>
          <span className={styles.spinner}>Calling Anthropic API... this may take a minute.</span>
        </div>
      )}

      {result && (
        <div className={styles.status}>
          <span className={result.ok ? styles.success : styles.error}>{result.message}</span>
          {result.ok && (
            <div>
              <button className={styles.startBtn} onClick={handleStartAnnotating}>
                Start Annotating
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
