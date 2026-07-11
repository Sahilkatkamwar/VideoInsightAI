import os
import re
import xml.etree.ElementTree as ET

import requests
from youtube_transcript_api import YouTubeTranscriptApi


YOUTUBE_ID_ALIASES = {
    # Common paste/read mistake: uppercase letter O instead of digit 0.
    "V_d3piTMEOY": "V_d3piTME0Y",
}


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


def _apply_known_video_id_alias(video_id: str) -> tuple[str, str | None]:
    resolved = YOUTUBE_ID_ALIASES.get(video_id)

    if not resolved:
        return video_id, None

    return resolved, f"Corrected known YouTube video id {video_id} -> {resolved}"


def _fetch_oembed(url: str) -> dict:
    try:
        response = requests.get(
            "https://www.youtube.com/oembed",
            params={"url": url, "format": "json"},
            timeout=10,
        )
        response.raise_for_status()
        data = response.json()
    except Exception as e:
        print(f"[YouTube oEmbed Error] {type(e).__name__}: {e}")
        return {}

    return {
        "title": data.get("title") or "",
        "creator": data.get("author_name") or "",
        "thumbnail": data.get("thumbnail_url") or "",
    }


def _parse_iso8601_duration(value: str) -> int:
    if not value:
        return 0

    match = re.fullmatch(
        r"P(?:(?P<days>\d+)D)?(?:T(?:(?P<hours>\d+)H)?(?:(?P<minutes>\d+)M)?(?:(?P<seconds>\d+)S)?)?",
        value,
    )

    if not match:
        return 0

    parts = {
        key: int(raw or 0)
        for key, raw in match.groupdict().items()
    }

    return (
        parts["days"] * 86400
        + parts["hours"] * 3600
        + parts["minutes"] * 60
        + parts["seconds"]
    )


def _int_value(value) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _best_thumbnail(thumbnails: dict) -> str:
    for key in ("maxres", "standard", "high", "medium", "default"):
        item = thumbnails.get(key)
        if item and item.get("url"):
            return item["url"]

    return ""


def _youtube_api_key() -> tuple[str, str]:
    for env_name in ("YOUTUBE_API_KEY", "YOUTUBE_DATA_API_KEY"):
        value = os.getenv(env_name)
        if value:
            return value, env_name

    return "", ""


def _youtube_api_error(payload: dict) -> str:
    error = payload.get("error") if isinstance(payload, dict) else {}

    if not isinstance(error, dict):
        return "Unknown API error"

    message = error.get("message") or "Unknown API error"
    details = error.get("errors") or []
    reason = ""

    if details and isinstance(details[0], dict):
        reason = details[0].get("reason") or ""

    return f"{message} ({reason})" if reason else message


def _fetch_youtube_api(video_id: str) -> tuple[dict, list[str]]:
    api_key, key_source = _youtube_api_key()

    if not api_key:
        message = (
            "YOUTUBE_API_KEY or YOUTUBE_DATA_API_KEY is not set; YouTube "
            "Data API v3 metadata cannot be loaded."
        )
        print(f"[YouTube Data API] {message}")
        return {}, [message]

    try:
        response = requests.get(
            "https://www.googleapis.com/youtube/v3/videos",
            params={
                "part": "snippet,statistics,contentDetails",
                "id": video_id,
                "key": api_key,
            },
            timeout=15,
        )
        payload = response.json()
        response.raise_for_status()
    except Exception as e:
        detail = ""

        if "response" in locals():
            try:
                detail = _youtube_api_error(payload)
            except Exception:
                detail = response.text[:300]

        message = (
            f"YouTube Data API v3 request failed using {key_source}: "
            f"{type(e).__name__}: {detail or e}"
        )
        print(f"[YouTube Data API Error] {message}")
        return {}, [message]

    items = payload.get("items") or []
    if not items:
        message = f"YouTube Data API v3 did not find video id {video_id}."
        print(f"[YouTube Data API] {message}")
        return {}, [message]

    item = items[0]
    snippet = item.get("snippet") or {}
    statistics = item.get("statistics") or {}
    content_details = item.get("contentDetails") or {}
    channel_id = snippet.get("channelId") or ""

    follower_count = _fetch_channel_subscribers(api_key, channel_id)
    published_at = snippet.get("publishedAt") or ""
    title = snippet.get("title") or ""
    description = snippet.get("description") or ""
    hashtags = re.findall(r"#([\w-]+)", f"{title} {description}")

    print(
        "[YouTube Data API] Loaded metadata for "
        f"{video_id} using {key_source}"
    )

    return {
        "metadata_source": "youtube_data_api_v3",
        "title": title,
        "description": description,
        "creator": snippet.get("channelTitle") or "",
        "channel_id": channel_id,
        "follower_count": follower_count,
        "hashtags": hashtags or snippet.get("tags") or [],
        "upload_date": published_at[:10].replace("-", "") if published_at else "",
        "duration": _parse_iso8601_duration(content_details.get("duration") or ""),
        "thumbnail": _best_thumbnail(snippet.get("thumbnails") or {}),
        "views": _int_value(statistics.get("viewCount")),
        "likes": _int_value(statistics.get("likeCount")),
        "comments": _int_value(statistics.get("commentCount")),
    }, []


def _fetch_channel_subscribers(api_key: str, channel_id: str) -> int:
    if not channel_id:
        return 0

    try:
        response = requests.get(
            "https://www.googleapis.com/youtube/v3/channels",
            params={
                "part": "statistics",
                "id": channel_id,
                "key": api_key,
            },
            timeout=15,
        )
        response.raise_for_status()
        payload = response.json()
    except Exception as e:
        print(f"[YouTube Channel API Error] {type(e).__name__}: {e}")
        return 0

    items = payload.get("items") or []
    if not items:
        return 0

    stats = items[0].get("statistics") or {}
    if stats.get("hiddenSubscriberCount"):
        return 0

    return _int_value(stats.get("subscriberCount"))


def _merge_metadata(*sources: dict) -> dict:
    merged = {}

    for source in sources:
        for key, value in source.items():
            if value not in ("", None, [], 0):
                merged[key] = value
            elif key not in merged:
                merged[key] = value

    return merged


def _get_transcript_segments(video_id: str) -> list[dict]:
    languages = ["en", "en-US", "en-GB", "en-orig"]

    try:
        fetched = YouTubeTranscriptApi().fetch(
            video_id,
            languages=languages,
        )

        if hasattr(fetched, "to_raw_data"):
            return fetched.to_raw_data()

        return [
            {
                "text": snippet.text,
                "start": snippet.start,
                "duration": snippet.duration,
            }
            for snippet in fetched
        ]
    except AttributeError:
        return YouTubeTranscriptApi.get_transcript(
            video_id,
            languages=languages,
        )


def _fetch_timedtext_transcript(video_id: str) -> tuple[str, list[dict]]:
    endpoints = (
        "https://www.youtube.com/api/timedtext",
        "https://video.google.com/timedtext",
    )

    for endpoint in endpoints:
        for params in (
            {"v": video_id, "lang": "en", "fmt": "json3"},
            {"v": video_id, "lang": "en"},
        ):
            try:
                response = requests.get(endpoint, params=params, timeout=15)
                response.raise_for_status()
            except Exception as e:
                print(f"[TimedText Error] {type(e).__name__}: {e}")
                continue

            text = response.text.strip()
            if not text:
                continue

            if params.get("fmt") == "json3":
                parsed = _parse_json3_transcript(response.json())
            else:
                parsed = _parse_xml_transcript(text)

            if parsed[0]:
                return parsed

    return "", []


def _parse_json3_transcript(data: dict) -> tuple[str, list[dict]]:
    chunks = []

    for event in data.get("events", []):
        segs = event.get("segs") or []
        line = "".join(seg.get("utf8", "") for seg in segs).strip()

        if not line:
            continue

        chunks.append(
            {
                "text": line,
                "start": (event.get("tStartMs") or 0) / 1000,
                "duration": (event.get("dDurationMs") or 0) / 1000,
            }
        )

    return " ".join(chunk["text"] for chunk in chunks), chunks


def _parse_xml_transcript(text: str) -> tuple[str, list[dict]]:
    try:
        root = ET.fromstring(text)
    except ET.ParseError as e:
        print(f"[TimedText XML Parse Error] {e}")
        return "", []

    chunks = []

    for item in root.findall("text"):
        line = "".join(item.itertext()).strip()

        if not line:
            continue

        chunks.append(
            {
                "text": line,
                "start": float(item.attrib.get("start") or 0),
                "duration": float(item.attrib.get("dur") or 0),
            }
        )

    return " ".join(chunk["text"] for chunk in chunks), chunks


def fetch_youtube(url: str) -> dict:
    original_vid_id = get_youtube_id(url)
    initial_vid_id, alias_diagnostic = _apply_known_video_id_alias(original_vid_id)
    vid_id = initial_vid_id
    lookup_url = f"https://www.youtube.com/watch?v={vid_id}"
    diagnostics = []

    if alias_diagnostic:
        print(f"[YouTube Resolver] {alias_diagnostic}")
        diagnostics.append(alias_diagnostic)

    if vid_id != original_vid_id and not alias_diagnostic:
        diagnostics.append(
            f"Corrected YouTube video id {original_vid_id} -> {vid_id}"
        )

    print("=" * 60)
    print("VIDEO ID:", vid_id)
    print("=" * 60)

    # --- Transcript ---
    transcript_text = ""
    timed_chunks = []
    info = {}

    try:
        print(f"[Transcript] Fetching transcript for {vid_id}")

        transcript_list = _get_transcript_segments(vid_id)

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

    if not transcript_text:
        transcript_text, timed_chunks = _fetch_timedtext_transcript(vid_id)

        if transcript_text:
            print(
                f"[TimedText] Extracted "
                f"{len(transcript_text)} characters"
            )

    # --- Metadata via official YouTube Data API v3. No yt-dlp here. ---
    api_info, api_diagnostics = _fetch_youtube_api(vid_id)
    diagnostics.extend(api_diagnostics)

    oembed = {}
    if api_info:
        info = api_info
    else:
        oembed = _fetch_oembed(lookup_url)
        info = _merge_metadata(
            {"metadata_source": "youtube_oembed_fallback"},
            oembed,
        )

        if oembed:
            diagnostics.append(
                "Using YouTube oEmbed only for title/thumbnail; "
                "views, likes, comments, and duration require "
                "YouTube Data API v3."
            )

    title = (
        info.get("title")
        or oembed.get("title")
        or f"YouTube video {vid_id}"
    )

    creator = (
        info.get("creator")
        or info.get("uploader")
        or info.get("channel")
        or oembed.get("creator")
        or ""
    )

    description = info.get("description") or ""

    content_text_parts = [
        title,
        description,
        transcript_text,
    ]

    content_text = "\n\n".join(
        part.strip()
        for part in content_text_parts
        if part and part.strip()
    )

    if not content_text:
        content_text = f"YouTube video {vid_id}\n{url}"

    views = info.get("views") or 0
    likes = info.get("likes") or 0
    comments = info.get("comments") or 0
    duration = info.get("duration") or 0
    upload_date = info.get("upload_date") or ""
    thumbnail = (
        info.get("thumbnail")
        or oembed.get("thumbnail")
        or f"https://i.ytimg.com/vi/{vid_id}/hqdefault.jpg"
    )
    metadata_source = info.get("metadata_source") or "minimal"

    if not api_info and not oembed:
        diagnostics.append(
            "YouTube metadata could not be loaded; configure "
            "YOUTUBE_API_KEY for YouTube Data API v3."
        )

    if views == 0:
        if api_info:
            diagnostics.append("YouTube Data API v3 returned 0 views.")
        else:
            diagnostics.append(
                "Video card will show 0 views until YouTube Data API v3 "
                "metadata is available."
            )

    if duration == 0:
        if api_info:
            diagnostics.append("YouTube Data API v3 returned no duration.")
        else:
            diagnostics.append(
                "Video card will show 0s until YouTube Data API v3 "
                "metadata is available."
            )

    if not transcript_text:
        diagnostics.append(
            "No YouTube transcript/captions were available."
        )

    return {
        "transcript": transcript_text,
        "content_text": content_text,
        "timed_chunks": timed_chunks,
        "views": views,
        "likes": likes,
        "comments": comments,
        "creator": creator,
        "follower_count": info.get("follower_count") or 0,
        "hashtags": info.get("hashtags") or info.get("tags") or [],
        "upload_date": upload_date,
        "duration": duration,
        "title": title,
        "thumbnail": thumbnail,
        "platform": "youtube",
        "source_url": url,
        "resolved_url": lookup_url,
        "source_video_id": original_vid_id,
        "resolved_video_id": vid_id,
        "metadata_source": metadata_source,
        "diagnostics": diagnostics,
    }
