const API_BASE =
  (import.meta as any).env?.VITE_API_BASE ?? "http://localhost:8000/api";

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