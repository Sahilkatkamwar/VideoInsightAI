import type { IngestResponse } from "./types";

const DEFAULT_API_URL = "https://videoinsightai-backend.onrender.com";
const YOUTUBE_ID_ALIASES: Record<string, string> = {
  V_d3piTMEOY: "V_d3piTME0Y",
};

export const API_BASE_URL = (
  process.env.NEXT_PUBLIC_API_URL || DEFAULT_API_URL
).replace(/\/+$/, "");

export function apiUrl(path: string): string {
  return `${API_BASE_URL}${path.startsWith("/") ? path : `/${path}`}`;
}

function normalizeVideoUrl(url: string): { url: string; diagnostics: string[] } {
  const diagnostics: string[] = [];
  let normalized = url;

  for (const [badId, goodId] of Object.entries(YOUTUBE_ID_ALIASES)) {
    if (!normalized.includes(badId)) continue;

    normalized = normalized.replaceAll(badId, goodId);
    diagnostics.push(
      `Corrected YouTube video id before request: ${badId} -> ${goodId}`
    );
  }

  return { url: normalized, diagnostics };
}

export async function ingestVideos(
  urlA: string,
  urlB: string
): Promise<IngestResponse> {
  const normalizedA = normalizeVideoUrl(urlA);
  const normalizedB = normalizeVideoUrl(urlB);

  console.groupCollapsed("[VideoInsight] /ingest request");
  console.info("API base:", API_BASE_URL);
  console.info("Video A URL:", urlA);
  console.info("Video B URL:", urlB);
  console.info("Video A sent URL:", normalizedA.url);
  console.info("Video B sent URL:", normalizedB.url);
  for (const item of [...normalizedA.diagnostics, ...normalizedB.diagnostics]) {
    console.warn("[VideoInsight] URL normalized", item);
  }
  console.groupEnd();

  const res = await fetch(apiUrl("/ingest"), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      url_a: normalizedA.url,
      url_b: normalizedB.url,
    }),
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    console.error("[VideoInsight] /ingest failed", {
      status: res.status,
      error: err,
    });
    throw new Error(err.detail || "Ingestion failed");
  }

  const data = await res.json();
  console.warn("[VideoInsight] INGEST RESULT", data);
  console.groupCollapsed("[VideoInsight] /ingest response");
  console.info(data);
  console.table([
    {
      id: "A",
      platform: data.A?.platform,
      title: data.A?.title,
      creator: data.A?.creator,
      views: data.A?.views,
      likes: data.A?.likes,
      comments: data.A?.comments,
      duration: data.A?.duration,
      uploadDate: data.A?.upload_date,
      resolvedUrl: data.A?.resolved_url,
      sourceVideoId: data.A?.source_video_id,
      resolvedVideoId: data.A?.resolved_video_id,
      metadataSource: data.A?.metadata_source,
    },
    {
      id: "B",
      platform: data.B?.platform,
      title: data.B?.title,
      creator: data.B?.creator,
      views: data.B?.views,
      likes: data.B?.likes,
      comments: data.B?.comments,
      duration: data.B?.duration,
      uploadDate: data.B?.upload_date,
      resolvedUrl: data.B?.resolved_url,
      sourceVideoId: data.B?.source_video_id,
      resolvedVideoId: data.B?.resolved_video_id,
      metadataSource: data.B?.metadata_source,
    },
  ]);
  console.groupEnd();

  return data;
}

export async function checkStatus(): Promise<{
  ready: boolean;
  video_a_chunks: number;
  video_b_chunks: number;
}> {
  const res = await fetch(apiUrl("/status"));
  if (!res.ok) throw new Error("Status check failed");
  return res.json();
}
