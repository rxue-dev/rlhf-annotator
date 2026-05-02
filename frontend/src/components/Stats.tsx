import { useState, useEffect } from "react";
import type { Stats as StatsData } from "../api";
import { fetchStats } from "../api";
import styles from "./Stats.module.css";

interface Props {
  onBack: () => void;
}

export default function Stats({ onBack }: Props) {
  const [stats, setStats] = useState<StatsData | null>(null);

  useEffect(() => {
    fetchStats().then(setStats);
  }, []);

  if (!stats) return <div className={styles.loading}>Loading stats...</div>;

  return (
    <div className={styles.container}>
      <div className={styles.header}>
        <h2 className={styles.title}>Annotation Stats</h2>
        <button className={styles.backBtn} onClick={onBack}>Back to Annotating</button>
      </div>

      <div className={styles.summary}>
        <div className={styles.card}>
          <div className={styles.cardValue}>{stats.total_pairs}</div>
          <div className={styles.cardLabel}>Total Pairs</div>
        </div>
        <div className={styles.card}>
          <div className={styles.cardValue}>{stats.annotated_pairs}</div>
          <div className={styles.cardLabel}>Pairs with Annotations</div>
        </div>
      </div>

      <h3 className={styles.tableTitle}>Per Annotator</h3>
      <table className={styles.table}>
        <thead>
          <tr>
            <th>Annotator</th>
            <th>Annotations</th>
          </tr>
        </thead>
        <tbody>
          {stats.per_annotator.map((row) => (
            <tr key={row.annotator_id}>
              <td>{row.annotator_id}</td>
              <td>{row.count}</td>
            </tr>
          ))}
          {stats.per_annotator.length === 0 && (
            <tr>
              <td colSpan={2} style={{ color: "var(--text-muted)", textAlign: "center" }}>
                No annotations yet
              </td>
            </tr>
          )}
        </tbody>
      </table>

      <a className={styles.exportBtn} href="http://localhost:8000/export" download>
        Export JSONL
      </a>
    </div>
  );
}
