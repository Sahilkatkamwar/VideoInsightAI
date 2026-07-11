import os
import re
import xml.etree.ElementTree as ET

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


def _fetch_youtube_api(video_id: str) -> dict:
    api_key = os.getenv("YOUTUBE_API_KEY")

    if not api_key:
        print("[YouTube Data API] No YOUTUBE_API_KEY set")
        return {}

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
        response.raise_for_status()
        payload = response.json()
    except Exception as e:
        print(f"[YouTube Data API Error] {type(e).__name__}: {e}")
        return {}

    items = payload.get("items") or []
    if not items:
        print(f"[YouTube Data API] No video item found for {video_id}")
        return {}

    item = items[0]
    snippet = item.get("snippet") or {}
    statistics = item.get("statistics") or {}
    content_details = item.get("contentDetails") or {}
    channel_id = snippet.get("channelId") or ""

    follower_count = _fetch_channel_subscribers(api_key, channel_id)
    published_at = snippet.get("publishedAt") or ""

    return {
        "title": snippet.get("title") or "",
        "description": snippet.get("description") or "",
        "creator": snippet.get("channelTitle") or "",
        "channel_id": channel_id,
        "follower_count": follower_count,
        "hashtags": snippet.get("tags") or [],
        "upload_date": published_at[:10].replace("-", "") if published_at else "",
        "duration": _parse_iso8601_duration(content_details.get("duration") or ""),
        "thumbnail": _best_thumbnail(snippet.get("thumbnails") or {}),
        "views": _int_value(statistics.get("viewCount")),
        "likes": _int_value(statistics.get("likeCount")),
        "comments": _int_value(statistics.get("commentCount")),
    }


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


def _fetch_innertube(video_id: str) -> dict:
    api_key = os.getenv(
        "YOUTUBE_INNERTUBE_API_KEY",
        "AIzaSyAO_FJ2SlqU8Q4STEHLGCilw_Y9_11qcW8",
    )

    clients = (
        ("WEB", "2.20240726.00.00"),
        ("TVHTML5", "7.20240724.13.00"),
    )

    for client_name, client_version in clients:
        try:
            response = requests.post(
                f"https://www.youtube.com/youtubei/v1/player?key={api_key}",
                json={
                    "context": {
                        "client": {
                            "clientName": client_name,
                            "clientVersion": client_version,
                        }
                    },
                    "videoId": video_id,
                    "contentCheckOk": True,
                    "racyCheckOk": True,
                },
                headers={
                    "Content-Type": "application/json",
                    "User-Agent": (
                        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/126.0.0.0 Safari/537.36"
                    ),
                },
                timeout=15,
            )
            response.raise_for_status()
            payload = response.json()
        except Exception as e:
            print(f"[YouTube InnerTube Error] {type(e).__name__}: {e}")
            continue

        video_details = payload.get("videoDetails") or {}
        if not video_details:
            status = payload.get("playabilityStatus") or {}
            reason = status.get("reason") or status.get("status") or "no details"
            print(f"[YouTube InnerTube] {client_name} returned: {reason}")
            continue

        microformat = (
            payload.get("microformat", {})
            .get("playerMicroformatRenderer", {})
        )
        thumbnails = video_details.get("thumbnail", {}).get("thumbnails") or []
        best_thumb = thumbnails[-1]["url"] if thumbnails else ""
        upload_date = (
            microformat.get("publishDate")
            or microformat.get("uploadDate")
            or ""
        )
        upload_date = upload_date[:10].replace("-", "") if upload_date else ""

        return {
            "title": video_details.get("title") or "",
            "description": video_details.get("shortDescription") or "",
            "creator": video_details.get("author") or "",
            "follower_count": 0,
            "hashtags": video_details.get("keywords") or [],
            "upload_date": upload_date,
            "duration": _int_value(video_details.get("lengthSeconds")),
            "thumbnail": best_thumb,
            "views": _int_value(video_details.get("viewCount")),
            "likes": 0,
            "comments": 0,
        }

    return {}


def _video_id_candidates(video_id: str) -> list[str]:
    candidates = [video_id]

    if "O" not in video_id:
        return candidates

    seen = {video_id}
    queue = [video_id]

    for index, char in enumerate(video_id):
        if char != "O":
            continue

        for current in list(queue):
            candidate = current[:index] + "0" + current[index + 1:]
            if candidate not in seen:
                seen.add(candidate)
                queue.append(candidate)
                candidates.append(candidate)

        if len(candidates) >= 8:
            break

    return candidates


def _resolve_video_id(video_id: str) -> tuple[str, dict]:
    for candidate in _video_id_candidates(video_id):
        info = _fetch_innertube(candidate)

        if info.get("title") or info.get("views") or info.get("duration"):
            if candidate != video_id:
                print(
                    f"[YouTube Resolver] Corrected video id "
                    f"{video_id} -> {candidate}"
                )

            return candidate, info

    return video_id, {}


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
    vid_id, innertube_info = _resolve_video_id(original_vid_id)
    lookup_url = f"https://www.youtube.com/watch?v={vid_id}"

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

    # --- Metadata via YouTube Data API + oEmbed fallback. No yt-dlp here. ---
    api_info = _fetch_youtube_api(vid_id)
    if not innertube_info:
        innertube_info = _fetch_innertube(vid_id)
    oembed = _fetch_oembed(lookup_url)
    info = _merge_metadata(innertube_info, api_info)

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
                    
    return {
    "transcript": transcript_text,
    "content_text": content_text,
    "timed_chunks": timed_chunks,

    "views": info.get("views") or 0,
    "likes": info.get("likes") or 0,
    "comments": info.get("comments") or 0,

    "creator": creator,

    "follower_count": info.get("follower_count") or 0,

    "hashtags": info.get("hashtags") or info.get("tags") or [],

    "upload_date": info.get("upload_date") or "",

    "duration": info.get("duration") or 0,

    "title": title,

    "thumbnail": (
        info.get("thumbnail")
        or oembed.get("thumbnail")
        or f"https://i.ytimg.com/vi/{vid_id}/hqdefault.jpg"
    ),

    "platform": "youtube",
}
    
