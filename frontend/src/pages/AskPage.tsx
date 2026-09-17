import React, { useState } from "react";
import { AskResponse, Citation, Mode, ask } from "../api";
import { MODES } from "./SearchPage";

export default function AskPage() {
  const [question, setQuestion] = useState("");
  const [mode, setMode] = useState<Mode>("hybrid");
  const [result, setResult] = useState<AskResponse | null>(null);
  const [open, setOpen] = useState<number | null>(null);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  async function onAsk(e: React.FormEvent) {
    e.preventDefault();
    if (!question.trim()) return;
    setBusy(true);
    setErr(null);
    setOpen(null);
    try {
      setResult(await ask(question.trim(), mode, 6));
    } catch (e: any) {
      setErr(String(e?.message ?? e));
    } finally {
      setBusy(false);
    }
  }

  function showCitation(n: number) {
    setOpen(n);
    // wait for the card to expand before scrolling to it
    requestAnimationFrame(() =>
      document.getElementById(`citation-${n}`)?.scrollIntoView({ behavior: "smooth", block: "center" })
    );
  }

  return (
    <div style={{ maxWidth: 900, margin: "24px auto", padding: "0 16px" }}>
      <h2>Ask</h2>

      <form onSubmit={onAsk} style={{ display: "flex", gap: 8, alignItems: "center", flexWrap: "wrap" }}>
        <input
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          placeholder="e.g. How many criminal convictions were recorded?"
          style={{ flex: 1, minWidth: 240, padding: 6 }}
        />
        <select value={mode} onChange={(e) => setMode(e.target.value as Mode)}>
          {MODES.map((m) => (
            <option key={m} value={m}>
              {m}
            </option>
          ))}
        </select>
        <button type="submit" disabled={busy || !question.trim()}>
          {busy ? "Asking…" : "Ask"}
        </button>
      </form>

      {err && <pre style={{ background: "#fee", padding: 10, whiteSpace: "pre-wrap", marginTop: 12 }}>{err}</pre>}

      {result && (
        <>
          <h3 style={{ marginTop: 18 }}>Answer</h3>
          <p style={{ background: "#f6f8fa", padding: 12, borderRadius: 6, lineHeight: 1.6 }}>
            <AnswerText answer={result.answer} citations={result.citations} onCite={showCitation} />
          </p>
          <p style={{ fontSize: 12, opacity: 0.65 }}>
            The answer is quoted verbatim from the cited passage.
            {result.blocked_sentences > 0 &&
              ` ${result.blocked_sentences} retrieved sentence(s) were ignored because they looked like instructions (prompt injection).`}
          </p>

          {result.citations.length > 0 && <h3>Citations</h3>}
          {result.citations.map((c) => (
            <CitationCard
              key={c.n}
              citation={c}
              open={open === c.n}
              onToggle={() => setOpen(open === c.n ? null : c.n)}
            />
          ))}
        </>
      )}
    </div>
  );
}

/** Renders the answer with each [n] marker as a link to its citation. */
function AnswerText({
  answer,
  citations,
  onCite,
}: {
  answer: string;
  citations: Citation[];
  onCite: (n: number) => void;
}) {
  const known = new Set(citations.map((c) => c.n));
  const parts = answer.split(/(\[\d+\])/g);
  return (
    <>
      {parts.map((part, i) => {
        const m = part.match(/^\[(\d+)\]$/);
        if (m && known.has(Number(m[1]))) {
          const n = Number(m[1]);
          return (
            <a
              key={i}
              href={`#citation-${n}`}
              onClick={(e) => {
                e.preventDefault();
                onCite(n);
              }}
              style={{ color: "#2563eb", fontWeight: 600, textDecoration: "none" }}
              title="Show source"
            >
              [{n}]
            </a>
          );
        }
        return <React.Fragment key={i}>{part}</React.Fragment>;
      })}
    </>
  );
}

function CitationCard({ citation: c, open, onToggle }: { citation: Citation; open: boolean; onToggle: () => void }) {
  return (
    <div
      id={`citation-${c.n}`}
      style={{
        border: `1px solid ${open ? "#2563eb" : "#ddd"}`,
        borderRadius: 6,
        padding: 12,
        marginBottom: 10,
        scrollMarginTop: 16,
      }}
    >
      <div style={{ display: "flex", justifyContent: "space-between", gap: 8 }}>
        <div style={{ fontSize: 13 }}>
          <strong>[{c.n}]</strong> {c.filename} · page {c.page}
          {c.section && <span style={{ opacity: 0.75 }}> · {c.section}</span>}
        </div>
        <button onClick={onToggle} style={{ fontSize: 12 }}>
          {open ? "Hide passage" : "Show full passage"}
        </button>
      </div>
      <div style={{ marginTop: 8, whiteSpace: "pre-wrap", lineHeight: 1.5 }}>
        <Highlighted text={open ? c.text : c.snippet} quotes={c.quotes} />
      </div>
      <div style={{ fontSize: 11, opacity: 0.5, marginTop: 6 }}>
        doc {c.doc_id} · chunk {c.chunk_id}
      </div>
    </div>
  );
}

/** Highlights the quoted sentences inside the passage text. */
function Highlighted({ text, quotes }: { text: string; quotes: string[] }) {
  const escaped = quotes.filter(Boolean).map((q) => q.replace(/[.*+?^${}()|[\]\\]/g, "\\$&"));
  if (escaped.length === 0) return <>{text}</>;
  const parts = text.split(new RegExp(`(${escaped.join("|")})`, "g"));
  return (
    <>
      {parts.map((part, i) =>
        quotes.includes(part) ? (
          <mark key={i} style={{ background: "#fef08a" }}>
            {part}
          </mark>
        ) : (
          <React.Fragment key={i}>{part}</React.Fragment>
        )
      )}
    </>
  );
}
