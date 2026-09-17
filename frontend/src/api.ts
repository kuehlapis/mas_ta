const API_BASE =
  (import.meta as any).env?.VITE_API_BASE ?? "http://localhost:8000/api";

export type Mode = "keyword" | "semantic" | "hybrid";

export type SearchResult = {
  doc_id: string;
  chunk_id: string;
  filename: string;
  page: number;
  section: string;
  score: number;
  snippet: string;
  mode: Mode;
  keyword_rank: number | null;
  semantic_rank: number | null;
  rerank_rank: number | null;
};

export type Citation = {
  n: number;
  doc_id: string;
  chunk_id: string;
  filename: string;
  page: number;
  section: string;
  snippet: string;
  quotes: string[];
  text: string;
};

export type AskResponse = {
  question: string;
  mode: Mode;
  answer: string;
  citations: Citation[];
  blocked_sentences: number;
};

async function postJson<T>(path: string, body: unknown): Promise<T> {
  const r = await fetch(`${API_BASE}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!r.ok) throw new Error(await r.text());
  return r.json() as Promise<T>;
}

export async function listDocuments() {
  const r = await fetch(`${API_BASE}/documents`);
  if (!r.ok) throw new Error(await r.text());
  return r.json();
}

export async function uploadDocument(file: File) {
  const fd = new FormData();
  fd.append("file", file);

  const r = await fetch(`${API_BASE}/documents`, {
    method: "POST",
    body: fd,
  });
  if (!r.ok) throw new Error(await r.text());
  return r.json() as Promise<{ doc_id: string }>;
}

export async function ingestDocument(docId: string) {
  const r = await fetch(`${API_BASE}/documents/${docId}/ingest`, {
    method: "POST",
  });
  if (!r.ok) throw new Error(await r.text());
  return r.json() as Promise<{ doc_id: string; chunks_indexed: number }>;
}

export function search(query: string, mode: Mode, top_k: number) {
  return postJson<{ query: string; mode: Mode; results: SearchResult[] }>("/search", { query, mode, top_k });
}

export function ask(question: string, mode: Mode, top_k: number) {
  return postJson<AskResponse>("/ask", { question, mode, top_k });
}
