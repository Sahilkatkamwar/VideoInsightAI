"use client";
import { useState } from "react";
import { ingestVideos } from "@/lib/api";
import type { VideoMeta } from "@/lib/types";

type Status = "idle" | "loading" | "success" | "error";

export function useIngest() {
  const [status, setStatus] = useState<Status>("idle");
  const [error, setError] = useState<string | null>(null);
  const [videoA, setVideoA] = useState<VideoMeta | null>(null);
  const [videoB, setVideoB] = useState<VideoMeta | null>(null);

  async function ingest(urlA: string, urlB: string) {
    setStatus("loading");
    setError(null);
    try {
      const result = await ingestVideos(urlA, urlB);
      setVideoA(result.A);
      setVideoB(result.B);
      setStatus("success");
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Unknown error");
      setStatus("error");
    }
  }

  function reset() {
    setStatus("idle");
    setError(null);
    setVideoA(null);
    setVideoB(null);
  }

  return { status, error, videoA, videoB, ingest, reset };
}
