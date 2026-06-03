import os
import re
import tempfile
import traceback

from pathlib import Path

import yt_dlp
from .instagram_followers import get_instagram_followers
from faster_whisper import WhisperModel

# Good default for local / CPU-only use
WHISPER_MODEL = WhisperModel(
    "small",
    device="cpu",
    compute_type="int8",
)


def get_shortcode(url: str) -> str:
    """
    Extract Instagram shortcode from reel/post URL.
    """
    url = url.split("?")[0].rstrip("/")

    patterns = [
        r"/reels?/([A-Za-z0-9_-]+)",
        r"/p/([A-Za-z0-9_-]+)",
        r"/tv/([A-Za-z0-9_-]+)",
    ]

    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)

    raise ValueError(f"Cannot extract Instagram shortcode from: {url}")


def _download_instagram_audio(url: str) -> str:
    """
    Download the best available audio to a temp file and return the path.
    """
    tmp_dir = tempfile.mkdtemp(prefix="ig_audio_")

    ydl_opts = {
        "quiet": True,
        "no_warnings": True,
        "skip_download": False,
        "extract_flat": False,
        "format": "bestaudio/best",
        "outtmpl": os.path.join(tmp_dir, "%(id)s.%(ext)s"),
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)

        # yt-dlp may choose .m4a, .webm, etc.
        expected_path = ydl.prepare_filename(info)

        if os.path.exists(expected_path):
            return expected_path

        # Fallback: find the first file in temp dir
        for entry in Path(tmp_dir).iterdir():
            if entry.is_file():
                return str(entry)

    raise FileNotFoundError("Audio file could not be located after download.")


def _transcribe_audio(audio_path: str) -> str:
    """
    Transcribe local audio with faster-whisper.
    """
    segments, info = WHISPER_MODEL.transcribe(
        audio_path,
        beam_size=5,
        vad_filter=True,
    )

    text_parts = []
    for segment in segments:
        piece = (segment.text or "").strip()
        if piece:
            text_parts.append(piece)

    return " ".join(text_parts).strip()


def fetch_instagram(url: str) -> dict:
    """
    Fetch Instagram Reel/Post metadata using yt-dlp and transcribe audio locally.
    """

    print(f"[Instagram] Extracting URL: {url}")

    ydl_opts = {
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,
        "extract_flat": False,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            
            import json

            with open("instagram_debug.json", "w", encoding="utf-8") as f:
                json.dump(
                    info,
                    f,
                    indent=2,
                    ensure_ascii=False,
                    default=str
                )

            print("Instagram debug saved.")
            
    except Exception as e:
        raise RuntimeError(f"Failed to fetch Instagram URL: {e}")

    caption = info.get("description") or ""
    hashtags = re.findall(r"#(\w+)", caption)

    title = (
        caption[:100]
        if caption
        else info.get("title", "")
        or "Instagram Reel"
    )
    
    title = (
        caption[:100]
        if caption
        else info.get("title", "")
        or "Instagram Reel"
        ) 

    creator = (
       info.get("uploader")
        or info.get("channel")
        or ""
    )
    print(
    "[Instagram Creator]",
    creator
    )

    followers = (
        info.get("channel_follower_count")
        or info.get("follower_count")
        or 0
    )

    if not followers and creator:

        try:
            followers = get_instagram_followers(
            creator
            )

            print(
                f"[Instagram] Followers: "
                f"{followers}"
            )


        except Exception as e:
            print(f"[Instagram Followers Error] {repr(e)}")
            traceback.print_exc()

    # Try local audio transcription
    audio_transcript = ""
    audio_path = None
    try:
        audio_path = _download_instagram_audio(url)
        # print(f"[Instagram Audio] Downloaded: {audio_path}")
        audio_transcript = _transcribe_audio(audio_path)
        # print(f"[Instagram Audio] Transcript chars: {len(audio_transcript)}")
        # print(audio_transcript[:300])
    except Exception as e:
        # print(f"[Instagram Audio] Transcription failed: {e}")
        audio_transcript = ""
    finally:
        if audio_path and os.path.exists(audio_path):
            try:
                os.remove(audio_path)
            except Exception:
                pass

    content_text_parts = [
        title,
        caption,
        audio_transcript,
        " ".join(hashtags),
    ]

    content_text = "\n\n".join(
        part.strip()
        for part in content_text_parts
        if part and part.strip()
    )

    return {
        "transcript": caption,
        "content_text": content_text,
        "timed_chunks": [],

        "views": (info.get("view_count") or info.get("play_count") or info.get("video_play_count") or 0),
        "likes": info.get("like_count") or 0,
        "comments": info.get("comment_count") or 0,
        "follower_count": followers,
        # "follower_count": info.get("channel_follower_count") or info.get("follower_count") or 0,

        # "creator": (
        #     info.get("uploader")
        #     or info.get("channel")
        #     or ""
        # ),
        "creator": creator,
    
        "hashtags": hashtags,

        "upload_date": info.get("upload_date") or "",

        "duration": int(info.get("duration") or 0),

        "title": title,

        "thumbnail": info.get("thumbnail") or "",

        "platform": "instagram",
    }