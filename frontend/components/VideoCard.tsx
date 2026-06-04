import { memo } from "react";
import type { VideoMeta } from "@/lib/types";

interface Props {
  video: VideoMeta;
  label: "A" | "B";
}

export const VideoCard = memo(function VideoCard({ video, label }: Props) {
  const platformIcon = video.platform === "youtube" ? "▶" : "◈";
  const uploadFormatted = video.upload_date
    ? `${video.upload_date.slice(0, 4)}-${video.upload_date.slice(4, 6)}-${video.upload_date.slice(6, 8)}`
    : "N/A";
  console.log("thumbnail:", video.thumbnail);
  return (
    <div style={{
      background: "#0f0f0f",
      border: "1px solid #222",
      borderRadius: 12,
      overflow: "hidden",
      flex: 1,
      minWidth: 0,
    }}>
      {/* Label badge */}
      <div style={{
        background: label === "A" ? "#6c63ff" : "#ff6b9d",
        color: "#fff",
        fontSize: 11,
        fontWeight: 700,
        letterSpacing: 1,
        padding: "4px 12px",
        textTransform: "uppercase",
      }}>
        {platformIcon} Video {label} — {video.platform}
      </div>

      {/* Thumbnail */}
      {video.thumbnail && (
        <div style={{ aspectRatio: "16/9", background: "#1a1a1a", overflow: "hidden" }}>
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img
            src={`${process.env.NEXT_PUBLIC_API_URL}/thumbnail?url=${encodeURIComponent(video.thumbnail)}`}
            alt={video.title}
            loading="lazy"
            style={{ width: "100%", height: "100%", objectFit: "cover" }}
          />
        </div>
      )}

      <div style={{ padding: "14px 16px" }}>
        {/* Title */}
        <p style={{
          color: "#f0f0f0",
          fontSize: 13,
          fontWeight: 600,
          margin: "0 0 10px",
          lineHeight: 1.4,
          display: "-webkit-box",
          WebkitLineClamp: 2,
          WebkitBoxOrient: "vertical",
          overflow: "hidden",
        }}>
          {video.title || "No title"}
        </p>

        {/* Creator */}
        <p style={{ color: "#aaa", fontSize: 12, margin: "0 0 12px" }}>
          @{video.creator}
          {video.follower_count > 0 && (
            <span style={{ color: "#666", marginLeft: 6 }}>
              · {formatNum(video.follower_count)} followers
            </span>
          )}
        </p>

        {/* Stats grid */}
        <div style={{
          display: "grid",
          gridTemplateColumns: "1fr 1fr",
          gap: 8,
        }}>
          <Stat label="Views" value={formatNum(video.views)} />
          <Stat label="Likes" value={formatNum(video.likes)} />
          <Stat label="Comments" value={formatNum(video.comments)} />
          <Stat
            label="Engagement"
            value={`${video.engagement_rate}%`}
            highlight
          />
          <Stat label="Duration" value={`${video.duration}s`} />
          <Stat label="Uploaded" value={uploadFormatted} />
        </div>

        {/* Hashtags */}
        {video.hashtags.length > 0 && (
          <div style={{ marginTop: 10, display: "flex", flexWrap: "wrap", gap: 4 }}>
            {video.hashtags.slice(0, 6).map((tag) => (
              <span key={tag} style={{
                background: "#1e1e1e",
                border: "1px solid #2a2a2a",
                borderRadius: 4,
                color: "#888",
                fontSize: 11,
                padding: "2px 6px",
              }}>
                #{tag}
              </span>
            ))}
          </div>
        )}
      </div>
    </div>
  );
});

function Stat({ label, value, highlight }: {
  label: string;
  value: string;
  highlight?: boolean;
}) {
  return (
    <div style={{
      background: "#1a1a1a",
      borderRadius: 6,
      padding: "8px 10px",
    }}>
      <p style={{ color: "#666", fontSize: 10, margin: "0 0 2px", textTransform: "uppercase", letterSpacing: 0.5 }}>
        {label}
      </p>
      <p style={{
        color: highlight ? "#50fa7b" : "#f0f0f0",
        fontSize: 14,
        fontWeight: 600,
        margin: 0,
      }}>
        {value}
      </p>
    </div>
  );
}

function formatNum(n: number): string {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1_000) return `${(n / 1_000).toFixed(1)}K`;
  return n.toString();
}
