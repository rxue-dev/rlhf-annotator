import { useState, FormEvent } from "react";
import styles from "./Login.module.css";

interface Props {
  onLogin: (name: string) => void;
}

export default function Login({ onLogin }: Props) {
  const [name, setName] = useState("");

  function handleSubmit(e: FormEvent) {
    e.preventDefault();
    const trimmed = name.trim();
    if (trimmed) onLogin(trimmed);
  }

  return (
    <div className={styles.container}>
      <h1 className={styles.title}>RLHF Annotation Tool</h1>
      <p className={styles.subtitle}>Enter your name to start annotating</p>
      <form className={styles.form} onSubmit={handleSubmit}>
        <input
          className={styles.input}
          type="text"
          placeholder="Your name"
          value={name}
          onChange={(e) => setName(e.target.value)}
          autoFocus
        />
        <button className={styles.button} type="submit">
          Start
        </button>
      </form>
    </div>
  );
}
