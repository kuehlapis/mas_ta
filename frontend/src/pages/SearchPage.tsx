import React, { useState } from "react";
import { Mode, SearchResult, search } from "../api";

export const MODES: Mode[] = ["hybrid", "keyword", "semantic"];

export default function SearchPage() {
  const [query, setQuery] = useState("");
  const [mode, setMode] = useState<Mode>("hybrid");
  const [topK, setTopK] = useState(10);
  const [results, setResults] = useState<SearchResult[] | null>(null);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  async function onSearch(e: React.FormEvent) {
    e.preventDefault();
    if (!query.trim()) return;
    setBusy(true);
    setErr(null);
    try {
      const data = await search(query.trim(), mode, topK);
      setResults(data.results);
    } catch (e: any) {
      setErr(String(e?.message ?? e));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div style={{ maxWidth: 900, margin: "24px auto", padding: "0 16px" }}>
      <h2>Search</h2>

      <form onSubmit={onSearch} style={{ display: "flex", gap: 8, alignItems: "center", flexWrap: "wrap" }}>
        <input
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="e.g. civil penalties imposed"
          style={{ flex: 1, minWidth: 240, padding: 6 }}
        />
        <select value={mode} onChange={(e) => setMode(e.target.value as Mode)}>
          {MODES.map((m) => (
            <option key={m} value={m}>
              {m}
            </option>
          ))}
        </select>
        <label style={{ fontSize: 14 }}>
          top_k{" "}
          <input
            type="number"
            min={1}
            max={50}
            value={topK}
            onChange={(e) => setTopK(Math.max(1, Math.min(50, Number(e.target.value) || 1)))}
            style={{ width: 56 }}
          />
        </label>
        <button type="submit" disabled={busy || !query.trim()}>
          {busy ? "Searching…" : "Search"}
        </button>
      </form>

      {err && <pre style={{ background: "#fee", padding: 10, whiteSpace: "pre-wrap", marginTop: 12 }}>{err}</pre>}

      {results && (
        <>
          <h3 style={{ marginTop: 18 }}>
            {results.length} result{results.length === 1 ? "" : "s"}
          </h3>
          {results.length === 0 && <p style={{ opacity: 0.7 }}>No matches. Have documents been ingested?</p>}
          <ol style={{ paddingLeft: 20 }}>
            {results.map((r) => (
              <li key={r.chunk_id} style={{ borderTop: "1px solid #ddd", padding: "10px 0" }}>
                <div style={{ fontSize: 13, opacity: 0.8 }}>
                  <strong>{r.filename}</strong> · page {r.page}
                  {r.section && <> · {r.section}</>}
                </div>
                <div style={{ margin: "6px 0", whiteSpace: "pre-wrap" }}>{r.snippet}</div>
                <div style={{ fontSize: 12, opacity: 0.65 }}>
                  score {r.score.toFixed(4)}
                  {" · "}keyword rank {r.keyword_rank ?? "–"}
                  {" · "}semantic rank {r.semantic_rank ?? "–"}
                  {r.rerank_rank != null && <> · rerank rank {r.rerank_rank}</>}
                </div>
              </li>
            ))}
          </ol>
        </>
      )}
    </div>
  );
}
