import { useState } from "react";
import Login from "./components/Login";
import Annotate from "./components/Annotate";
import Stats from "./components/Stats";

type Page = "annotate" | "stats";

const STORAGE_KEY = "rlhf_annotator_id";

export default function App() {
  const [annotatorId, setAnnotatorId] = useState<string | null>(
    () => localStorage.getItem(STORAGE_KEY)
  );
  const [page, setPage] = useState<Page>("annotate");

  function handleLogin(name: string) {
    localStorage.setItem(STORAGE_KEY, name);
    setAnnotatorId(name);
  }

  function handleLogout() {
    localStorage.removeItem(STORAGE_KEY);
    setAnnotatorId(null);
    setPage("annotate");
  }

  if (!annotatorId) {
    return <Login onLogin={handleLogin} />;
  }

  if (page === "stats") {
    return <Stats onBack={() => setPage("annotate")} />;
  }

  return (
    <Annotate
      annotatorId={annotatorId}
      onShowStats={() => setPage("stats")}
      onLogout={handleLogout}
    />
  );
}
