"use client";
import { useState } from "react";

interface Props {
  onIngest: (urlA: string, urlB: string) => void;
  status: "idle" | "loading" | "success" | "error";
  error: string | null;
}

export function IngestForm({ onIngest, status, error }: Props) {
  const [urlA, setUrlA] = useState("");
  const [urlB, setUrlB] = useState("");

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (urlA.trim() && urlB.trim()) {
      onIngest(urlA.trim(), urlB.trim());
    }
  }

  const isLoading = status === "loading";

  return (
    <div style={{
      background: "#0f0f0f",
      border: "1px solid #222",
      borderRadius: 12,
      padding: "20px 24px",
    }}>
      <p style={{ color: "#888", fontSize: 12, margin: "0 0 14px", textTransform: "uppercase", letterSpacing: 1 }}>
        Ingest Videos
      </p>
      <form onSubmit={handleSubmit}>
        <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
          <input
            value={urlA}
            onChange={(e) => setUrlA(e.target.value)}
            placeholder="Video A — YouTube URL"
            disabled={isLoading}
            style={inputStyle}
          />
          <input
            value={urlB}
            onChange={(e) => setUrlB(e.target.value)}
            placeholder="Video B — Instagram Reel URL"
            disabled={isLoading}
            style={inputStyle}
          />
          <button
            type="submit"
            disabled={isLoading || !urlA.trim() || !urlB.trim()}
            style={{
              ...btnStyle,
              opacity: isLoading || !urlA.trim() || !urlB.trim() ? 0.5 : 1,
            }}
          >
            {isLoading ? (
              <span style={{ display: "flex", alignItems: "center", gap: 8 }}>
                <Spinner /> Ingesting... (30–90s)
              </span>
            ) : (
              "Ingest Both Videos"
            )}
          </button>
        </div>
      </form>
      {error && (
        <p style={{ color: "#ff5555", fontSize: 13, marginTop: 10 }}>
          ⚠ {error}
        </p>
      )}
      {status === "success" && (
        <p style={{ color: "#50fa7b", fontSize: 13, marginTop: 10 }}>
          ✓ Both videos ingested — start chatting
        </p>
      )}
    </div>
  );
}

const inputStyle: React.CSSProperties = {
  background: "#1a1a1a",
  border: "1px solid #2a2a2a",
  borderRadius: 8,
  color: "#f0f0f0",
  fontSize: 14,
  padding: "10px 14px",
  outline: "none",
  width: "100%",
  boxSizing: "border-box",
};

const btnStyle: React.CSSProperties = {
  background: "#6c63ff",
  border: "none",
  borderRadius: 8,
  color: "#fff",
  cursor: "pointer",
  fontSize: 14,
  fontWeight: 600,
  padding: "11px 0",
  width: "100%",
};

function Spinner() {
  return (
    <span style={{
      display: "inline-block",
      width: 14,
      height: 14,
      border: "2px solid rgba(255,255,255,0.3)",
      borderTopColor: "#fff",
      borderRadius: "50%",
      animation: "spin 0.7s linear infinite",
    }} />
  );
}
