"""YouTube Data API search + caching of results in the resources table."""
import html
import time
from typing import List

import httpx
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.config import settings
from app.database.models import Resource, ResourceCompletion
from app.schemas.resource import ResourceOut
from app.services.errors import ExternalServiceError

YT_SEARCH_URL = "https://www.googleapis.com/youtube/v3/search"
CACHE_TTL_SECONDS = 24 * 3600

# query -> (timestamp, [resource ids]); saves API quota (each search costs 100 units/day)
_query_cache: dict = {}


def search_videos(query: str, max_results: int = 6) -> List[dict]:
    if not settings.YOUTUBE_API_KEY:
        raise ExternalServiceError("YOUTUBE_API_KEY is not configured on the server.", 503)

    params = {
        "part": "snippet",
        "type": "video",
        "q": query,
        "maxResults": max_results,
        "safeSearch": "strict",
        "relevanceLanguage": "en",
        "key": settings.YOUTUBE_API_KEY,
    }
    try:
        resp = httpx.get(YT_SEARCH_URL, params=params, timeout=20)
    except httpx.HTTPError:
        raise ExternalServiceError("Could not reach YouTube. Please try again.") from None

    if resp.status_code == 403:
        raise ExternalServiceError("YouTube API quota exceeded or key not allowed.", 503)
    if resp.status_code != 200:
        raise ExternalServiceError(f"YouTube returned an error (status {resp.status_code}).")

    videos = []
    for item in resp.json().get("items", []):
        video_id = (item.get("id") or {}).get("videoId")
        snippet = item.get("snippet") or {}
        if not video_id or not snippet.get("title"):
            continue
        thumbs = snippet.get("thumbnails") or {}
        thumb = (thumbs.get("high") or thumbs.get("medium") or thumbs.get("default") or {}).get("url")
        videos.append({
            "youtube_video_id": video_id,
            "title": html.unescape(snippet["title"])[:300],
            "url": f"https://www.youtube.com/watch?v={video_id}",
            "thumbnail": thumb,
            "channel": html.unescape(snippet.get("channelTitle", ""))[:200],
            "description": html.unescape(snippet.get("description", "")),
            "published_at": snippet.get("publishedAt"),
        })
    return videos


def _save_videos(db: Session, videos: List[dict], topic: str) -> List[Resource]:
    ids = [v["youtube_video_id"] for v in videos]
    if not ids:
        return []
    existing = {r.youtube_video_id for r in db.query(Resource).filter(Resource.youtube_video_id.in_(ids))}
    for v in videos:
        if v["youtube_video_id"] not in existing:
            db.add(Resource(**v, topic=topic[:150]))
            existing.add(v["youtube_video_id"])
    try:
        db.commit()
    except IntegrityError:  # two requests saved the same video at once: fine
        db.rollback()
    rows = {r.youtube_video_id: r for r in db.query(Resource).filter(Resource.youtube_video_id.in_(ids))}
    return [rows[i] for i in ids if i in rows]


def search_resources(db: Session, query: str) -> List[Resource]:
    key = query.strip().lower()
    hit = _query_cache.get(key)
    if hit and time.time() - hit[0] < CACHE_TTL_SECONDS:
        rows = {r.id: r for r in db.query(Resource).filter(Resource.id.in_(hit[1]))}
        ordered = [rows[i] for i in hit[1] if i in rows]
        if ordered:
            return ordered

    videos = search_videos(query.strip())
    resources = _save_videos(db, videos, topic=key)
    if len(_query_cache) > 500:
        _query_cache.clear()
    _query_cache[key] = (time.time(), [r.id for r in resources])
    return resources


def serialize_resources(db: Session, user_id: int, resources: List[Resource]) -> List[ResourceOut]:
    ids = [r.id for r in resources]
    done = set()
    if ids:
        done = {row.resource_id for row in db.query(ResourceCompletion).filter(
            ResourceCompletion.user_id == user_id, ResourceCompletion.resource_id.in_(ids))}
    out = []
    for r in resources:
        item = ResourceOut.model_validate(r)
        item.completed = r.id in done
        out.append(item)
    return out
