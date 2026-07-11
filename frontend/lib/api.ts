import type { IngestResponse } from "./types";

const DEFAULT_API_URL = "https://videoinsightai-backend.onrender.com";

export const API_BASE_URL = (
  process.env.NEXT_PUBLIC_API_URL || DEFAULT_API_URL
).replace(/\/+$/, "");

export function apiUrl(path: string): string {
  return `${API_BASE_URL}${path.startsWith("/") ? path : `/${path}`}`;
}

export async function ingestVideos(
  urlA: string,
  urlB: string
): Promise<IngestResponse> {
  const res = await fetch(apiUrl("/ingest"), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ url_a: urlA, url_b: urlB }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || "Ingestion failed");
  }
  return res.json();
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
