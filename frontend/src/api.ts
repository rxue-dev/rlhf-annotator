const BASE = "http://localhost:8000";

export interface PromptPair {
  id: number;
  prompt: string;
  response_a: string;
  response_b: string;
  model_a: string;
  model_b: string;
}

export interface Stats {
  total_pairs: number;
  annotated_pairs: number;
  per_annotator: { annotator_id: string; count: number }[];
}

export async function fetchAllPairs(): Promise<PromptPair[]> {
  const res = await fetch(`${BASE}/pairs/all`);
  const data = await res.json();
  return data.pairs;
}

export async function fetchNextPair(annotatorId: string): Promise<PromptPair | null> {
  const res = await fetch(`${BASE}/pairs/next?annotator_id=${encodeURIComponent(annotatorId)}`);
  const data = await res.json();
  return data.pair;
}

export async function fetchPairById(pairId: number): Promise<PromptPair | null> {
  const res = await fetch(`${BASE}/pairs/${pairId}`);
  const data = await res.json();
  return data.pair;
}

export async function submitAnnotation(body: {
  pair_id: number;
  annotator_id: string;
  preferred: string;
  rationale: string | null;
  response_a_shown_as: string;
}): Promise<{ status: string; id: number }> {
  const res = await fetch(`${BASE}/annotations`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  return res.json();
}

export interface Annotation {
  preferred: string;
  rationale: string | null;
  response_a_shown_as: string;
}

export async function fetchAnnotationForPair(
  pairId: number,
  annotatorId: string,
): Promise<Annotation | null> {
  const res = await fetch(
    `${BASE}/annotations/for-pair?pair_id=${pairId}&annotator_id=${encodeURIComponent(annotatorId)}`,
  );
  const data = await res.json();
  return data.annotation;
}

export async function updateAnnotation(body: {
  pair_id: number;
  annotator_id: string;
  preferred: string;
  rationale: string | null;
  response_a_shown_as: string;
}): Promise<{ status: string }> {
  const res = await fetch(`${BASE}/annotations`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  return res.json();
}

export async function fetchStats(): Promise<Stats> {
  const res = await fetch(`${BASE}/stats`);
  return res.json();
}
