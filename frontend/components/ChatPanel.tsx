"use client";
import { useState, useRef, useEffect } from "react";
import { MessageBubble } from "./MessageBubble";
import type { Message, VideoMeta } from "@/lib/types";

const SUGGESTED = [
  "Why did Video A get more engagement than Video B?",
  "What's the engagement rate of each video?",
  "Compare the hooks in the first 5 seconds",
  "Who's the creator of Video B and what's their follower count?",
  "Suggest improvements for B based on what worked in A",
];

interface Props {
  messages: Message[];
  isStreaming: boolean;
  onSend: (text: string) => void;
  onClear: () => void;
  videoA: VideoMeta | null;
  videoB: VideoMeta | null;
}

export function ChatPanel({ messages, isStreaming, onSend, onClear, videoA, videoB }: Props) {
  const [input, setInput] = useState("");
  const bottomRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const ready = !!videoA && !!videoB;

  // Auto-scroll to bottom on new tokens
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  function handleSend() {
    const text = input.trim();
    if (!text || isStreaming || !ready) return;
    setInput("");
    onSend(text);
  }

  function handleKey(e: React.KeyboardEvent) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  }

  return (
    <div style={{
      display: "flex",
      flexDirection: "column",
      height: "100%",
      background: "#0a0a0a",
      border: "1px solid #1a1a1a",
      borderRadius: 12,
      overflow: "hidden",
    }}>
      {/* Header */}
      <div style={{
        borderBottom: "1px solid #1a1a1a",
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        padding: "12px 16px",
      }}>
        <span style={{ color: "#888", fontSize: 12, textTransform: "uppercase", letterSpacing: 1 }}>
          Chat
          {isStreaming && (
            <span style={{ color: "#6c63ff", marginLeft: 8 }}>● streaming</span>
          )}
        </span>
        {messages.length > 0 && (
          <button onClick={onClear} style={{
            background: "none",
            border: "1px solid #2a2a2a",
            borderRadius: 6,
            color: "#666",
            cursor: "pointer",
            fontSize: 11,
            padding: "3px 8px",
          }}>
            Clear
          </button>
        )}
      </div>

      {/* Messages */}
      <div style={{
        flex: 1,
        overflowY: "auto",
        padding: 16,
        display: "flex",
        flexDirection: "column",
        gap: 12,
      }}>
        {!ready && (
          <div style={{ color: "#444", fontSize: 13, textAlign: "center", marginTop: 40 }}>
            Ingest both videos to start chatting
          </div>
        )}

        {ready && messages.length === 0 && (
          <div style={{ display: "flex", flexDirection: "column", gap: 8, marginTop: 20 }}>
            <p style={{ color: "#555", fontSize: 12, textAlign: "center", marginBottom: 8 }}>
              Suggested questions
            </p>
            {SUGGESTED.map((q) => (
              <button
                key={q}
                onClick={() => onSend(q)}
                style={{
                  background: "#111",
                  border: "1px solid #2a2a2a",
                  borderRadius: 8,
                  color: "#aaa",
                  cursor: "pointer",
                  fontSize: 13,
                  padding: "10px 14px",
                  textAlign: "left",
                  transition: "border-color 0.15s",
                }}
              >
                {q}
              </button>
            ))}
          </div>
        )}

        {messages.map((msg) => (
          <MessageBubble key={msg.id} message={msg} />
        ))}
        <div ref={bottomRef} />
      </div>

      {/* Input */}
      <div style={{
        borderTop: "1px solid #1a1a1a",
        display: "flex",
        gap: 8,
        padding: 12,
      }}>
        <textarea
          id="chat-message"
          name="chat-message"
          autoComplete="off"
          ref={textareaRef}
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKey}
          placeholder={ready ? "Ask anything about these videos…" : "Ingest videos first"}
          disabled={!ready || isStreaming}
          rows={1}
          style={{
            background: "#141414",
            border: "1px solid #2a2a2a",
            borderRadius: 8,
            color: "#f0f0f0",
            flex: 1,
            fontSize: 14,
            outline: "none",
            padding: "10px 12px",
            resize: "none",
            lineHeight: 1.5,
          }}
        />
        <button
          onClick={handleSend}
          disabled={!ready || isStreaming || !input.trim()}
          style={{
            background: "#6c63ff",
            border: "none",
            borderRadius: 8,
            color: "#fff",
            cursor: "pointer",
            fontSize: 18,
            opacity: !ready || isStreaming || !input.trim() ? 0.4 : 1,
            padding: "0 16px",
          }}
        >
          ↑
        </button>
      </div>
    </div>
  );
}
