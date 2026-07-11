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

      for (const video of [result.A, result.B]) {
        if (video.platform !== "youtube") continue;

        const diagnostics = video.diagnostics ?? [];

        if (video.views === 0 || video.duration === 0 || diagnostics.length > 0) {
          console.warn("[VideoInsight] YouTube ingest diagnostics", {
            video_id: video.video_id,
            title: video.title,
            creator: video.creator,
            views: video.views,
            duration: video.duration,
            upload_date: video.upload_date,
            source_url: video.source_url,
            resolved_url: video.resolved_url,
            source_video_id: video.source_video_id,
            resolved_video_id: video.resolved_video_id,
            metadata_source: video.metadata_source,
            diagnostics,
          });
        } else {
          console.info("[VideoInsight] YouTube metadata loaded", {
            video_id: video.video_id,
            title: video.title,
            views: video.views,
            duration: video.duration,
            resolved_url: video.resolved_url,
            resolved_video_id: video.resolved_video_id,
            metadata_source: video.metadata_source,
          });
        }
      }

      setStatus("success");
    } catch (e: unknown) {
      console.error("[VideoInsight] ingest exception", e);
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
