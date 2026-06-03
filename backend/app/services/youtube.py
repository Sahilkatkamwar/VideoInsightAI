import re
import yt_dlp
import requests
from youtube_transcript_api import YouTubeTranscriptApi


def get_youtube_id(url: str) -> str:
    patterns = [
        r"(?:v=)([A-Za-z0-9_-]{11})",
        r"(?:youtu\.be/)([A-Za-z0-9_-]{11})",
        r"(?:shorts/)([A-Za-z0-9_-]{11})",
    ]
    for p in patterns:
        m = re.search(p, url)
        if m:
            return m.group(1)
    raise ValueError(f"Cannot extract YouTube video ID from: {url}")


def fetch_youtube(url: str) -> dict:
    vid_id = get_youtube_id(url)

    print("=" * 60)
    print("VIDEO ID:", vid_id)
    print("=" * 60)

    # --- Transcript ---
    transcript_text = ""
    timed_chunks = []

    try:
        print(f"[Transcript] Fetching transcript for {vid_id}")

        transcript_list = YouTubeTranscriptApi.get_transcript(
            vid_id,
            languages=["en"]
        )

        transcript_text = " ".join(
            t["text"]
            for t in transcript_list
        )

        timed_chunks = [
            {
                "text": t["text"],
                "start": t["start"],
                "duration": t["duration"],
            }
            for t in transcript_list
        ]

        print(
            f"[Transcript] Success - "
            f"{len(transcript_list)} segments"
        )

    except Exception as e:
        print(
            f"[Transcript Error] "
            f"{type(e).__name__}: {e}"
        )

        transcript_text = ""
        timed_chunks = []

    # --- Metadata via yt-dlp ---
    ydl_opts = {
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,
        "extract_flat": False,
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(
            url,
            download=False
        )

    # Fallback if transcript unavailable
    if not transcript_text:

        subtitles = (
        info.get("automatic_captions", {})
        or info.get("subtitles", {})
        )

        if subtitles:

            print("[Fallback] Subtitle tracks found")

            preferred_langs = [
                "en",
                "en-US",
                "en-GB",
                "en-orig"
            ]

            selected_track = None

            for lang in preferred_langs:
                if lang in subtitles:
                    selected_track = subtitles[lang]
                    print(f"[Fallback] Using {lang}")
                    break

            if not selected_track:
                first_lang = next(iter(subtitles))
                selected_track = subtitles[first_lang]
                print(
                    f"[Fallback] Using first available language: "
                    f"{first_lang}"
                )

        # Prefer json3 captions
            json3_track = next(
                (
                    x for x in selected_track
                    if x.get("ext") == "json3"
                ),
                None,
            )

            if json3_track:

                try:
                    r = requests.get(
                        json3_track["url"],
                        timeout=15
                    )

                    data = r.json()

                    events = data.get("events", [])

                    texts = []

                    for event in events:

                        if "segs" not in event:
                            continue

                        line = "".join(
                            seg.get("utf8", "")
                            for seg in event["segs"]
                        ).strip()

                        if line:
                            texts.append(line)

                    transcript_text = "\n".join(texts)

                    print(
                        f"[Fallback] Extracted "
                        f"{len(transcript_text)} characters"
                    )

                except Exception as e:
                    print(
                        f"[Subtitle Parse Error] {e}"
                    )
                    
    description = info.get("description") or ""

    content_text_parts = [
        info.get("title") or "",
        description,
        transcript_text,
    ]

    content_text = "\n\n".join(
        part.strip()
        for part in content_text_parts
        if part and part.strip()
    )
                    
    return {
    "transcript": transcript_text,
    "content_text": content_text,
    "timed_chunks": timed_chunks,

    "views": info.get("view_count") or 0,
    "likes": info.get("like_count") or 0,
    "comments": info.get("comment_count") or 0,

    "creator": info.get("uploader")
    or info.get("channel")
    or "",

    "follower_count": info.get("channel_follower_count") or 0,

    "hashtags": info.get("tags") or [],

    "upload_date": info.get("upload_date") or "",

    "duration": info.get("duration") or 0,

    "title": info.get("title") or "",

    "thumbnail": info.get("thumbnail") or "",

    "platform": "youtube",
}
    