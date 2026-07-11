import re
import traceback
import sys

import yt_dlp

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


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


def _minimal_instagram(url: str, error: str = "") -> dict:
    shortcode = get_shortcode(url)
    title = f"Instagram Reel {shortcode}"
    content = title

    if error:
        content += f"\nMetadata fetch failed: {error}"

    content += f"\n{url}"

    return {
        "transcript": content,
        "content_text": content,
        "timed_chunks": [],
        "views": 0,
        "likes": 0,
        "comments": 0,
        "follower_count": 0,
        "creator": "",
        "hashtags": [],
        "upload_date": "",
        "duration": 0,
        "title": title,
        "thumbnail": "",
        "platform": "instagram",
    }


def _fetch_instagram_with_instaloader(url: str) -> dict:
    from instaloader import Instaloader, Post

    shortcode = get_shortcode(url)
    loader = Instaloader(
        download_pictures=False,
        download_videos=False,
        download_video_thumbnails=False,
        save_metadata=False,
        compress_json=False,
        quiet=True,
    )

    post = Post.from_shortcode(loader.context, shortcode)
    caption = post.caption or ""
    hashtags = re.findall(r"#(\w+)", caption)
    title = caption[:100] if caption else f"Instagram Reel {shortcode}"

    followers = 0
    try:
        followers = post.owner_profile.followers or 0
    except Exception as e:
        print(f"[Instagram Followers Error] {repr(e)}")

    duration = getattr(post, "video_duration", None) or 0
    views = (
        getattr(post, "video_view_count", None)
        or getattr(post, "video_play_count", None)
        or 0
    )

    content_text_parts = [
        title,
        caption,
        " ".join(hashtags),
    ]

    content_text = "\n\n".join(
        part.strip()
        for part in content_text_parts
        if part and part.strip()
    ) or f"Instagram Reel {shortcode}\n{url}"

    return {
        "transcript": caption or content_text,
        "content_text": content_text,
        "timed_chunks": [],
        "views": views,
        "likes": post.likes or 0,
        "comments": post.comments or 0,
        "follower_count": followers,
        "creator": post.owner_username or "",
        "hashtags": hashtags,
        "upload_date": post.date_utc.strftime("%Y%m%d") if post.date_utc else "",
        "duration": int(duration or 0),
        "title": title,
        "thumbnail": post.url or "",
        "platform": "instagram",
    }


def fetch_instagram(url: str) -> dict:
    """
    Fetch Instagram Reel/Post metadata using yt-dlp.
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

            try:
                with open("instagram_debug.json", "w", encoding="utf-8") as f:
                    json.dump(
                        info,
                        f,
                        indent=2,
                        ensure_ascii=False,
                        default=str,
                    )

                print("Instagram debug saved.")
            except OSError as e:
                print(f"[Instagram Debug Write Error] {e}")

    except Exception as e:
        print(f"[Instagram yt-dlp Error] {type(e).__name__}: {e}")

        try:
            return _fetch_instagram_with_instaloader(url)
        except Exception as fallback_error:
            print(
                f"[Instagram instaloader Error] "
                f"{type(fallback_error).__name__}: {fallback_error}"
            )
            return _minimal_instagram(url, str(fallback_error))

    caption = info.get("description") or ""
    hashtags = re.findall(r"#(\w+)", caption)

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

    print("[Instagram Creator]", creator)

    followers = (
        info.get("channel_follower_count")
        or info.get("follower_count")
        or 0
    )

    if not followers and creator:
        try:
            followers = 0

            print(
                f"[Instagram] Followers: "
                f"{followers}"
            )

        except Exception as e:
            print(f"[Instagram Followers Error] {repr(e)}")
            traceback.print_exc()

    content_text_parts = [
        title,
        caption,
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
        "views": (
            info.get("view_count")
            or info.get("play_count")
            or info.get("video_play_count")
            or 0
        ),
        "likes": info.get("like_count") or 0,
        "comments": info.get("comment_count") or 0,
        "follower_count": followers,
        "creator": creator,
        "hashtags": hashtags,
        "upload_date": info.get("upload_date") or "",
        "duration": int(info.get("duration") or 0),
        "title": title,
        "thumbnail": info.get("thumbnail") or "",
        "platform": "instagram",
    }
