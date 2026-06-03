"use client";
import { useState, useRef, useCallback } from "react";
import { readSSEStream } from "@/lib/sse";
import type { Message, VideoMeta, Source } from "@/lib/types";

export function useChat(videoA: VideoMeta | null, videoB: VideoMeta | null) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [isStreaming, setIsStreaming] = useState(false);
  const sessionId = useRef<string>(crypto.randomUUID());
  const abortRef = useRef<AbortController | null>(null);

  const sendMessage = useCallback(
    async (text: string) => {
      if (!videoA || !videoB || isStreaming) return;

      // Cancel any in-flight request
      abortRef.current?.abort();
      abortRef.current = new AbortController();

      const userMsg: Message = {
        id: crypto.randomUUID(),
        role: "user",
        content: text,
      };
      const botId = crypto.randomUUID();
      const botMsg: Message = {
        id: botId,
        role: "assistant",
        content: "",
        streaming: true,
      };

      setMessages((prev) => [...prev, userMsg, botMsg]);
      setIsStreaming(true);

      try {
        const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

        const res = await fetch(`${API_URL}/chat`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          signal: abortRef.current.signal,
          body: JSON.stringify({
            message: text,
            session_id: sessionId.current,
            metadata_a: {
              title: videoA.title,
              creator: videoA.creator,
              follower_count: videoA.follower_count,
              views: videoA.views,
              likes: videoA.likes,
              comments: videoA.comments,
              engagement_rate: videoA.engagement_rate,
              duration: videoA.duration,
              upload_date: videoA.upload_date,
              hashtags: videoA.hashtags,
              platform: videoA.platform,
            },
            metadata_b: {
              title: videoB.title,
              creator: videoB.creator,
              follower_count: videoB.follower_count,
              views: videoB.views,
              likes: videoB.likes,
              comments: videoB.comments,
              engagement_rate: videoB.engagement_rate,
              duration: videoB.duration,
              upload_date: videoB.upload_date,
              hashtags: videoB.hashtags,
              platform: videoB.platform,
            },
          }),
        });

        if (!res.ok) throw new Error(`HTTP ${res.status}`);

        let collectedSources: Source[] = [];

        for await (const event of readSSEStream(res)) {
          if (event.type === "token" && event.content) {
            setMessages((prev) =>
              prev.map((m) =>
                m.id === botId
                  ? { ...m, content: m.content + event.content }
                  : m
              )
            );
          } else if (event.type === "sources" && event.sources) {
            collectedSources = event.sources;
          } else if (event.type === "done") {
            setMessages((prev) =>
              prev.map((m) =>
                m.id === botId
                  ? { ...m, streaming: false, sources: collectedSources }
                  : m
              )
            );
          } else if (event.type === "error") {
            setMessages((prev) =>
              prev.map((m) =>
                m.id === botId
                  ? {
                    ...m,
                    content: `Error: ${event.message}`,
                    streaming: false,
                  }
                  : m
              )
            );
          }
        }
      } catch (e: unknown) {
        if (e instanceof Error && e.name === "AbortError") return;
        setMessages((prev) =>
          prev.map((m) =>
            m.id === botId
              ? { ...m, content: "Request failed. Try again.", streaming: false }
              : m
          )
        );
      } finally {
        setIsStreaming(false);
      }
    },
    [videoA, videoB, isStreaming]
  );

  function clearChat() {
    setMessages([]);
    sessionId.current = crypto.randomUUID(); // new session = fresh memory
  }

  return { messages, isStreaming, sendMessage, clearChat };
}
