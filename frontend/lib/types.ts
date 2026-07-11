export interface VideoMeta {
  video_id: string;
  title: string;
  transcript: string;
  views: number;
  likes: number;
  comments: number;
  creator: string;
  follower_count: number;
  hashtags: string[];
  upload_date: string;
  duration: number;
  engagement_rate: number;
  thumbnail: string;
  platform: "youtube" | "instagram";
  source_url?: string;
  resolved_url?: string;
  diagnostics?: string[];
}

export interface Source {
  video_id: string;
  chunk_index: number;
  start_time: number;
  text_preview?: string;
  score: number;
  title?: string;
  creator?: string;
}

export interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  sources?: Source[];
  streaming?: boolean;
}

export interface IngestResponse {
  A: VideoMeta;
  B: VideoMeta;
  message: string;
}
