"use client";
import { useIngest } from "@/hooks/useIngest";
import { useChat } from "@/hooks/useChat";
import { IngestForm } from "@/components/IngestForm";
import { VideoCard } from "@/components/VideoCard";
import { ChatPanel } from "@/components/ChatPanel";

export default function Home() {
  const { status, error, videoA, videoB, ingest, reset } = useIngest();
  const { messages, isStreaming, sendMessage, clearChat } = useChat(videoA, videoB);

  const hasVideos = !!videoA && !!videoB;

  return (
    <div style={{
      display: "flex",
      flexDirection: "column",
      height: "100vh",
      overflow: "hidden",
    }}>
      {/* Top bar */}
      <header style={{
        borderBottom: "1px solid #1a1a1a",
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        padding: "12px 20px",
        flexShrink: 0,
      }}>
        <span style={{ color: "#f0f0f0", fontSize: 15, fontWeight: 700 }}>
          ◈ RAG Video Chatbot
        </span>
        {hasVideos && (
          <button onClick={() => { reset(); clearChat(); }} style={{
            background: "none",
            border: "1px solid #2a2a2a",
            borderRadius: 6,
            color: "#666",
            cursor: "pointer",
            fontSize: 12,
            padding: "4px 10px",
          }}>
            Reset
          </button>
        )}
      </header>

      {/* Main content */}
      <main style={{
        display: "flex",
        flex: 1,
        gap: 16,
        overflow: "hidden",
        padding: 16,
      }}>
        {/* Left column: Ingest form + Video cards */}
        <div style={{
          display: "flex",
          flexDirection: "column",
          gap: 14,
          width: 460,
          flexShrink: 0,
          overflowY: "auto",
        }}>
          <IngestForm
            onIngest={ingest}
            status={status}
            error={error}
            videoA={videoA}
            videoB={videoB}
          />

          {hasVideos && (
            <div style={{ display: "flex", gap: 10 }}>
              <VideoCard video={videoA} label="A" />
              <VideoCard video={videoB} label="B" />
            </div>
          )}

          {!hasVideos && status === "idle" && (
            <div style={{
              background: "#0f0f0f",
              border: "1px dashed #1e1e1e",
              borderRadius: 12,
              color: "#333",
              fontSize: 13,
              padding: 24,
              textAlign: "center",
            }}>
              Video cards will appear here after ingestion
            </div>
          )}
        </div>

        {/* Right column: Chat */}
        <div style={{ flex: 1, minWidth: 0 }}>
          <ChatPanel
            messages={messages}
            isStreaming={isStreaming}
            onSend={sendMessage}
            onClear={clearChat}
            videoA={videoA}
            videoB={videoB}
          />
        </div>
      </main>
    </div>
  );
}
