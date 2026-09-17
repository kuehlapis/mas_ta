import React, { useState } from "react";
import UploadPage from "./pages/UploadPage";
import SearchPage from "./pages/SearchPage";
import AskPage from "./pages/AskPage";

const TABS = [
  { id: "upload", label: "Upload & Ingest" },
  { id: "search", label: "Search" },
  { id: "ask", label: "Ask" },
] as const;

type TabId = (typeof TABS)[number]["id"];

export default function App() {
  const [tab, setTab] = useState<TabId>("upload");

  return (
    <div style={{ fontFamily: "system-ui, sans-serif" }}>
      <nav style={{ display: "flex", gap: 4, justifyContent: "center", borderBottom: "1px solid #ddd", padding: "12px 0 0" }}>
        {TABS.map((t) => (
          <button
            key={t.id}
            onClick={() => setTab(t.id)}
            style={{
              padding: "8px 16px",
              border: "none",
              borderBottom: tab === t.id ? "2px solid #2563eb" : "2px solid transparent",
              background: "none",
              fontWeight: tab === t.id ? 600 : 400,
              cursor: "pointer",
            }}
          >
            {t.label}
          </button>
        ))}
      </nav>
      {/* keep pages mounted so switching tabs doesn't lose their state */}
      <div style={{ display: tab === "upload" ? "block" : "none" }}>
        <UploadPage />
      </div>
      <div style={{ display: tab === "search" ? "block" : "none" }}>
        <SearchPage />
      </div>
      <div style={{ display: tab === "ask" ? "block" : "none" }}>
        <AskPage />
      </div>
    </div>
  );
}
