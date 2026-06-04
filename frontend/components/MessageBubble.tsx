import { memo } from "react";
import type { Message } from "@/lib/types";

interface Props {
  message: Message;
}

export const MessageBubble = memo(function MessageBubble({ message }: Props) {
  const isUser = message.role === "user";

  return (
    <div style={{
      display: "flex",
      flexDirection: "column",
      alignItems: isUser ? "flex-end" : "flex-start",
      gap: 6,
    }}>
      {/* Bubble */}
      <div style={{
        background: isUser ? "#6c63ff" : "#1a1a1a",
        border: isUser ? "none" : "1px solid #2a2a2a",
        borderRadius: isUser ? "16px 16px 4px 16px" : "16px 16px 16px 4px",
        color: "#f0f0f0",
        fontSize: 14,
        lineHeight: 1.6,
        maxWidth: "85%",
        padding: "10px 14px",
        whiteSpace: "pre-wrap",
        wordBreak: "break-word",
      }}>
        {message.content}
        {message.streaming && <BlinkCursor />}
      </div>

      {/* Citation sources */}
      {message.sources && message.sources.length > 0 && (
        <div style={{
          display: "flex",
          flexWrap: "wrap",
          gap: 4,
          maxWidth: "85%",
        }}>
          {message.sources.map((src, i) => (
            <div
              key={i}
              title={src.text_preview}
              style={{
                background: src.video_id === "A" ? "#1e1a3a" : "#2a1a2e",
                border: `1px solid ${src.video_id === "A" ? "#4a3fa0" : "#7a3f6a"}`,
                borderRadius: 6,
                color: src.video_id === "A" ? "#a89aff" : "#ff9ad5",
                cursor: "help",
                fontSize: 11,
                padding: "3px 8px",
              }}
            >
              Video {src.video_id} · chunk {src.chunk_index}
              {src.start_time >= 0 && ` · ${src.start_time.toFixed(1)}s`}
              · {Math.round(src.score * 100)}% match
            </div>
          ))}
        </div>
      )}
    </div>
  );
});

function BlinkCursor() {
  return (
    <span style={{
      display: "inline-block",
      width: 2,
      height: 14,
      background: "#f0f0f0",
      marginLeft: 2,
      verticalAlign: "middle",
      animation: "blink 1s step-end infinite",
    }} />
  );
}
