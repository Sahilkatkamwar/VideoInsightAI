import requests
from fastapi import APIRouter, HTTPException
from fastapi.responses import Response

router = APIRouter()

@router.get("/thumbnail")
def proxy_thumbnail(url: str):
    try:
        r = requests.get(
            url,
            timeout=15,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/148.0.0.0 Safari/537.36"
                )
            },
        )
        r.raise_for_status()
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Thumbnail fetch failed: {e}")

    return Response(
        content=r.content,
        media_type=r.headers.get("content-type", "image/jpeg"),
    )