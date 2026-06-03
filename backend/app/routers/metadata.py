from fastapi import APIRouter, HTTPException
from ..services.vectorstore import _collection

router = APIRouter()


@router.get("/metadata/{video_id}")
async def get_metadata(video_id: str):
    """Return metadata for a specific video (A or B) from ChromaDB."""
    if video_id not in ("A", "B"):
        raise HTTPException(status_code=400, detail="video_id must be 'A' or 'B'")

    results = _collection.get(
        where={"video_id": video_id},
        limit=1,
        include=["metadatas"],
    )

    if not results["metadatas"]:
        raise HTTPException(
            status_code=404,
            detail=f"No data found for Video {video_id}. Ingest first.",
        )

    # Metadata is stored on every chunk — return from the first chunk
    meta = results["metadatas"][0]
    return {"video_id": video_id, "data": meta}


@router.get("/status")
async def status():
    """Quick health check — returns chunk counts for A and B."""
    a_count = len(_collection.get(where={"video_id": "A"})["ids"])
    b_count = len(_collection.get(where={"video_id": "B"})["ids"])
    return {
        "status": "ok",
        "video_a_chunks": a_count,
        "video_b_chunks": b_count,
        "ready": a_count > 0 and b_count > 0,
    }
