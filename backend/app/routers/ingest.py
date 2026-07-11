import asyncio
import traceback

from fastapi import APIRouter, HTTPException

from ..models.schemas import (
    IngestRequest,
    IngestResponse,
    VideoMeta,
)

from ..services.youtube import fetch_youtube
from ..services.instagram import fetch_instagram
from ..services.engagement import compute_engagement
from ..services.vectorstore import ingest_video
from ..services.embedder import embed

router = APIRouter()


def _detect_platform(url: str) -> str:
    if "youtu" in url:
        return "youtube"

    if "instagram" in url or "instagr.am" in url:
        return "instagram"

    raise ValueError(f"Unsupported platform URL: {url}")


def _fetch_video(url: str) -> dict:
    platform = _detect_platform(url)

    print(f"\n[Platform] Detected: {platform}")
    print(f"[URL] {url}")

    if platform == "youtube":
        return fetch_youtube(url)

    return fetch_instagram(url)


async def _ingest_one(video_id: str, url: str) -> dict:
    loop = asyncio.get_event_loop()

    print("\n" + "=" * 60)
    print(f"[INGEST START] Video {video_id}")
    print(f"URL: {url}")
    print("=" * 60)

    try:
        print(f"[{video_id}] Fetching metadata/transcript...")

        data = await loop.run_in_executor(
            None,
            _fetch_video,
            url
        )

        print(f"[{video_id}] Fetch successful")

        print(f"[{video_id}] Keys returned:")
        print(list(data.keys()))

        transcript = (
            data.get("content_text")
            or data.get("transcript", "")
        )

        print(
            f"[{video_id}] Content length: "
            f"{len(transcript) if transcript else 0}"
        )

        if not transcript:
            print(f"[{video_id}] WARNING: Transcript is empty")

        diagnostics = data.setdefault("diagnostics", [])

        if data.get("platform") == "youtube":
            if data.get("views", 0) == 0:
                diagnostics.append(
                    "Video card will show 0 views because YouTube metadata returned 0 views."
                )

            if data.get("duration", 0) == 0:
                diagnostics.append(
                    "Video card will show 0s because YouTube metadata returned no duration."
                )

            if data.get("resolved_url") and data.get("source_url"):
                if data["resolved_url"] not in data["source_url"]:
                    print(
                        f"[{video_id}] Resolved URL: "
                        f"{data['resolved_url']}"
                    )

        data["engagement_rate"] = compute_engagement(
            data.get("views", 0),
            data.get("likes", 0),
            data.get("comments", 0),
            data.get("follower_count", 0),
        )

        print(
            f"[{video_id}] Engagement rate: "
            f"{data['engagement_rate']}%"
        )

        print(f"[{video_id}] Sending to ChromaDB...")

        n_chunks = await loop.run_in_executor(
            None,
            ingest_video,
            video_id,
            transcript,
            data.get("timed_chunks", []),
            data,
            embed,
        )

        print(
            f"[{video_id}] SUCCESS -> "
            f"{n_chunks} chunks stored"
        )

        return data

    except Exception as e:
        print("\n")
        print("=" * 60)
        print(f"[ERROR INSIDE VIDEO {video_id}]")
        print(type(e).__name__)
        print(str(e))
        traceback.print_exc()
        print("=" * 60)
        print("\n")

        raise


@router.post("/ingest", response_model=IngestResponse)
async def ingest(req: IngestRequest):

    print("\n")
    print("#" * 80)
    print("INGEST REQUEST RECEIVED")
    print(f"URL A: {req.url_a}")
    print(f"URL B: {req.url_b}")
    print("#" * 80)
    print("\n")

    try:

        results = await asyncio.gather(
            _ingest_one("A", req.url_a),
            _ingest_one("B", req.url_b),
            return_exceptions=True,
        )

        result_a, result_b = results
        
        if isinstance(result_a, Exception):
            print("[A FAILED]", result_a)

        if isinstance(result_b, Exception):
            print("[B FAILED]", result_b)

    except ValueError as e:

        print("\n[VALUE ERROR]")
        traceback.print_exc()

        raise HTTPException(
            status_code=400,
            detail=str(e),
        )

    except Exception as e:

        print("\n")
        print("#" * 80)
        print("INGEST FAILED")
        traceback.print_exc()
        print("#" * 80)
        print("\n")

        raise HTTPException(
            status_code=500,
            detail=f"Ingestion failed: {str(e)}",
        )

    def to_meta(video_id: str, d: dict) -> VideoMeta:
        
        if isinstance(d, Exception):
            raise HTTPException(
            status_code=500,
            detail=f"Video {video_id} failed: {d}"
        )
        return VideoMeta(
            video_id=video_id,
            title=d.get("title", ""),
            transcript=d.get("content_text") or d.get("transcript", ""),
            views=d.get("views", 0),
            likes=d.get("likes", 0),
            comments=d.get("comments", 0),
            creator=d.get("creator", ""),
            follower_count=d.get("follower_count", 0),
            hashtags=d.get("hashtags", []),
            upload_date=d.get("upload_date", ""),
            duration=d.get("duration", 0),
            engagement_rate=d.get("engagement_rate", 0.0),
            thumbnail=d.get("thumbnail", ""),
            platform=d.get("platform", ""),
            source_url=d.get("source_url", ""),
            resolved_url=d.get("resolved_url", ""),
            diagnostics=d.get("diagnostics", []),
        )

    return IngestResponse(
        A=to_meta("A", result_a),
        B=to_meta("B", result_b),
        message="Both videos ingested successfully.",
    )
