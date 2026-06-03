from pydantic import BaseModel
from typing import Optional


class IngestRequest(BaseModel):
    url_a: str
    url_b: str


class VideoMeta(BaseModel):
    video_id: str
    title: str
    transcript: str
    views: int
    likes: int
    comments: int
    creator: str
    follower_count: int
    hashtags: list[str]
    upload_date: str
    duration: int
    engagement_rate: float
    thumbnail: str
    platform: str  # "youtube" or "instagram"


class IngestResponse(BaseModel):
    A: VideoMeta
    B: VideoMeta
    message: str


class ChatRequest(BaseModel):
    message: str
    session_id: str
    metadata_a: dict
    metadata_b: dict


class MetadataResponse(BaseModel):
    video_id: str
    data: dict
