from pydantic import BaseModel, Field
from typing import Optional, List


class IngestRequest(BaseModel):
    url_a: str
    url_b: str


class VideoMeta(BaseModel):
    video_id: str
    title: str = ""
    transcript: str = ""
    views: int = 0
    likes: int = 0
    comments: int = 0
    creator: str = ""
    follower_count: int = 0
    hashtags: List[str] = []
    upload_date: str = ""
    duration: float = 0.0
    engagement_rate: float = 0.0
    thumbnail: str = ""
    platform: str = ""
    source_url: str = ""
    resolved_url: str = ""
    diagnostics: List[str] = Field(default_factory=list)


class IngestResponse(BaseModel):
    A: VideoMeta
    B: VideoMeta
    message: str


class ChatRequest(BaseModel):
    session_id: str = Field(..., description="Stable conversation/thread id")
    message: str = Field(..., description="User query")
    metadata_a: Optional[VideoMeta] = None
    metadata_b: Optional[VideoMeta] = None


class MetadataResponse(BaseModel):
    video_id: str
    data: dict
