"use client";
import { useState } from "react";
import type { VideoMeta } from "@/lib/types";

interface Props {
  onIngest: (urlA: string, urlB: string) => void;
  status: "idle" | "loading" | "success" | "error";
  error: string | null;
  videoA: VideoMeta | null;
  videoB: VideoMeta | null;
}

export function IngestForm({ onIngest, status, error, videoA, videoB }: Props) {
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
            id="video-a-url"
            name="video-a-url"
            autoComplete="url"
            value={urlA}
            onChange={(e) => setUrlA(e.target.value)}
            placeholder="Video A — YouTube URL"
            disabled={isLoading}
            style={inputStyle}
          />
          <input
            id="video-b-url"
            name="video-b-url"
            autoComplete="url"
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
      {status === "success" && (videoA || videoB) && (
        <IngestDiagnostics videoA={videoA} videoB={videoB} />
      )}
    </div>
  );
}

function IngestDiagnostics({
  videoA,
  videoB,
}: {
  videoA: VideoMeta | null;
  videoB: VideoMeta | null;
}) {
  const videos = [
    ["A", videoA],
    ["B", videoB],
  ] as const;

  return (
    <div style={diagnosticsStyle}>
      <p style={{ color: "#888", fontSize: 11, margin: "0 0 8px", textTransform: "uppercase", letterSpacing: 0.8 }}>
        Ingest Diagnostics
      </p>
      {videos.map(([label, video]) => {
        if (!video) return null;

        const warnings = video.diagnostics ?? [];
        const isYoutube = video.platform === "youtube";
        const hasZeroStats = isYoutube && (video.views === 0 || video.duration === 0);

        return (
          <div key={label} style={{ marginTop: 8 }}>
            <p style={{ color: "#ddd", fontSize: 12, margin: 0 }}>
              Video {label} · {video.platform} · views {formatNum(video.views)} · duration {video.duration}s
            </p>
            {video.resolved_url && (
              <p style={{ color: "#777", fontSize: 11, margin: "3px 0 0", wordBreak: "break-all" }}>
                resolved: {video.resolved_url}
              </p>
            )}
            {(video.source_video_id || video.resolved_video_id || video.metadata_source) && (
              <p style={{ color: "#777", fontSize: 11, margin: "3px 0 0", wordBreak: "break-word" }}>
                id: {video.source_video_id || "n/a"} → {video.resolved_video_id || "n/a"}
                {video.metadata_source ? ` · source: ${video.metadata_source}` : ""}
              </p>
            )}
            {(hasZeroStats || warnings.length > 0) && (
              <div style={{ marginTop: 4 }}>
                {warnings.length === 0 ? (
                  <p style={warningStyle}>YouTube returned zero metadata for this URL.</p>
                ) : (
                  warnings.map((item) => (
                    <p key={item} style={warningStyle}>
                      {item}
                    </p>
                  ))
                )}
              </div>
            )}
          </div>
        );
      })}
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

const diagnosticsStyle: React.CSSProperties = {
  background: "#141414",
  border: "1px solid #252525",
  borderRadius: 8,
  marginTop: 12,
  padding: "10px 12px",
};

const warningStyle: React.CSSProperties = {
  color: "#ffb86c",
  fontSize: 11,
  margin: "3px 0 0",
};

function formatNum(n: number): string {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1_000) return `${(n / 1_000).toFixed(1)}K`;
  return n.toString();
}

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
