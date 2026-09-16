import React, { useEffect, useState } from "react";
import { ingestDocument, listDocuments, uploadDocument } from "../api";

type DocInfo = {
  doc_id: string;
  filename: string;
  created_at: string;
  ingested: boolean;
  chunk_count: number;
};

export default function UploadPage() {
  const [file, setFile] = useState<File | null>(null);
  const [docs, setDocs] = useState<DocInfo[]>([]);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  async function refresh() {
    const data = await listDocuments();
    setDocs(data.documents ?? []);
  }

  useEffect(() => {
    refresh().catch((e) => setErr(String(e)));
  }, []);

  async function onUpload() {
    if (!file) return;
    setBusy(true);
    setErr(null);
    try {
      const { doc_id } = await uploadDocument(file);
      await refresh();
      alert(`Uploaded doc_id: ${doc_id}`);
    } catch (e: any) {
      setErr(String(e?.message ?? e));
    } finally {
      setBusy(false);
    }
  }

  async function onIngest(docId: string) {
    setBusy(true);
    setErr(null);
    try {
      await ingestDocument(docId);
      await refresh();
    } catch (e: any) {
      setErr(String(e?.message ?? e));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div style={{ maxWidth: 900, margin: "24px auto", fontFamily: "system-ui, sans-serif" }}>
      <h2>Upload & Ingest</h2>

      <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
        <input type="file" onChange={(e) => setFile(e.target.files?.[0] ?? null)} />
        <button onClick={onUpload} disabled={!file || busy}>
          Upload
        </button>
        <button onClick={refresh} disabled={busy}>
          Refresh
        </button>
      </div>

      {err && (
        <pre style={{ background: "#fee", padding: 10, whiteSpace: "pre-wrap", marginTop: 12 }}>
          {err}
        </pre>
      )}

      <h3 style={{ marginTop: 18 }}>Documents</h3>
      <table style={{ width: "100%", borderCollapse: "collapse" }}>
        <thead>
          <tr>
            <th align="left">Doc</th>
            <th align="left">Created</th>
            <th align="left">Ingested</th>
            <th align="left">Chunks</th>
            <th />
          </tr>
        </thead>
        <tbody>
          {docs.map((d) => (
            <tr key={d.doc_id} style={{ borderTop: "1px solid #ddd" }}>
              <td>
                <code>{d.doc_id}</code>
                <div style={{ fontSize: 12, opacity: 0.75 }}>{d.filename}</div>
              </td>
              <td style={{ fontSize: 12 }}>{d.created_at}</td>
              <td>{d.ingested ? "yes" : "no"}</td>
              <td>{d.chunk_count}</td>
              <td>
                <button onClick={() => onIngest(d.doc_id)} disabled={busy}>
                  Ingest
                </button>
              </td>
            </tr>
          ))}
          {docs.length === 0 && (
            <tr>
              <td colSpan={5} style={{ padding: 10, opacity: 0.7 }}>
                No documents yet.
              </td>
            </tr>
          )}
        </tbody>
      </table>
    </div>
  );
}