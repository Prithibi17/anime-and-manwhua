import asyncio
import time
import httpx
from fastapi import APIRouter
from typing import Dict, Any, List

router = APIRouter(prefix="/health", tags=["Health & Diagnostics"])

ANIME_PROVIDERS = [
    {"id": "aniwaves", "name": "AniWaves", "type": "anime"}
]


MANGA_PROVIDERS = [
    {"id": "vortex", "name": "Vortex Scans", "url": "https://api.vortexscans.org/api/posts?page=1", "type": "manga/manhwa"},
    {"id": "toraka", "name": "Toraka (ShineiAPI)", "url": "https://core.toraka.com/api/v1/series?per_page=2", "type": "manga/manhwa"},
    {"id": "mangadex", "name": "MangaDex", "url": "https://api.mangadex.org/manga?limit=2", "type": "manga/manhwa/manhua"},
    {"id": "anilist", "name": "AniList Catalog", "url": "https://graphql.anilist.co", "type": "catalog"}
]


async def _test_anime_provider(client: httpx.AsyncClient, p: Dict[str, Any]) -> Dict[str, Any]:
    prov_id = p["id"]
    test_url = f"http://127.0.0.1:5646/anime/extract/21827?e=1&type=sub&provider={prov_id}"
    t0 = time.time()
    try:
        res = await client.get(test_url, timeout=12.0)
        dur = round((time.time() - t0) * 1000)
        if res.status_code == 200:
            data = res.json()
            stream_count = len(data.get("streams", []))
            return {
                "id": prov_id,
                "name": p["name"],
                "category": "anime",
                "status": "online" if stream_count > 0 else "empty",
                "latency_ms": dur,
                "streams_found": stream_count,
                "message": f"Returned {stream_count} streams in {dur}ms"
            }
        else:
            return {
                "id": prov_id,
                "name": p["name"],
                "category": "anime",
                "status": "error",
                "latency_ms": dur,
                "streams_found": 0,
                "message": f"HTTP {res.status_code}"
            }
    except Exception as e:
        dur = round((time.time() - t0) * 1000)
        return {
            "id": prov_id,
            "name": p["name"],
            "category": "anime",
            "status": "offline",
            "latency_ms": dur,
            "streams_found": 0,
            "message": str(e)[:120]
        }


async def _test_manga_provider(client: httpx.AsyncClient, p: Dict[str, Any]) -> Dict[str, Any]:
    prov_id = p["id"]
    url = p["url"]
    t0 = time.time()
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        if prov_id == "anilist":
            res = await client.post(url, json={"query": "query { Page(page:1, perPage:1) { media(type:MANGA) { id } } }"}, headers=headers, timeout=8.0)
        else:
            res = await client.get(url, headers=headers, timeout=8.0)
        
        dur = round((time.time() - t0) * 1000)
        is_ok = res.status_code in (200, 201)
        return {
            "id": prov_id,
            "name": p["name"],
            "category": p["type"],
            "status": "online" if is_ok else "degraded",
            "latency_ms": dur,
            "message": f"HTTP {res.status_code} ({dur}ms)"
        }
    except Exception as e:
        dur = round((time.time() - t0) * 1000)
        return {
            "id": prov_id,
            "name": p["name"],
            "category": p["type"],
            "status": "offline",
            "latency_ms": dur,
            "message": str(e)[:120]
        }


@router.get("/all")
async def check_all_providers():
    """Runs concurrent health check across all anime extractors and manga providers."""
    async with httpx.AsyncClient(follow_redirects=True, verify=False) as client:
        anime_tasks = [_test_anime_provider(client, p) for p in ANIME_PROVIDERS]
        manga_tasks = [_test_manga_provider(client, p) for p in MANGA_PROVIDERS]
        
        results = await asyncio.gather(*anime_tasks, *manga_tasks)

    anime_results = [r for r in results if r.get("category") == "anime"]
    manga_results = [r for r in results if r.get("category") != "anime"]

    return {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "anime_total": len(anime_results),
        "anime_online": sum(1 for r in anime_results if r["status"] == "online"),
        "manga_total": len(manga_results),
        "manga_online": sum(1 for r in manga_results if r["status"] == "online"),
        "providers": results
    }
