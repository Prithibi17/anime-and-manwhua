import asyncio
import re
from typing import Optional, List, Dict, Any
from urllib.parse import quote
from fastapi import APIRouter, Depends, Query, Request, HTTPException

from src.api_auth import require_api_key
from src.queries import MEDIA_LIST_FIELDS
from src.extractor import anilist_query
from src.parser import proxy_deep_images
from src.providers import _race as provider_race
from src.manga.vortex import fetch_vortex_posts, fetch_vortex_chapters, fetch_vortex_chapter_pages
from src.manga.toraka import fetch_toraka_series, fetch_toraka_chapters
from src.manga.mangadex import search_mangadex, fetch_mangadex_chapters, fetch_mangadex_chapter_pages
from src.manga.anilist_manga import query_anilist_manga
from src.manga.router import aggregate_and_deduplicate_manga, enrich_with_anilist_posters, get_or_fetch_anilist_poster

api_router = APIRouter(prefix="/api", tags=["Kuhi Public API"])


# ==========================================================
# 1. ANIME ENDPOINTS
# ==========================================================

@api_router.get("/anime/search")
async def api_anime_search(
    q: str = Query(..., min_length=1, description="Anime title search keyword"),
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(20, ge=1, le=50, description="Results per page"),
    auth: Dict[str, Any] = Depends(require_api_key)
):
    """Search for anime series with titles, HD poster, release year, format, and episode count."""
    gql = f"""
    query ($search: String, $page: Int, $perPage: Int) {{
        Page(page: $page, perPage: $perPage) {{
            pageInfo {{ total currentPage lastPage hasNextPage perPage }}
            media(search: $search, type: ANIME, sort: SEARCH_MATCH) {{
                {MEDIA_LIST_FIELDS}
            }}
        }}
    }}
    """
    data = await anilist_query(gql, {"search": q, "page": page, "perPage": per_page})
    page_data = data.get("Page", {})
    page_info = page_data.get("pageInfo", {})
    results = proxy_deep_images(page_data.get("media", []))

    # Format into developer-friendly objects
    formatted = []
    for item in results:
        t = item.get("title") or {}
        cov = item.get("coverImage") or {}
        st = item.get("startDate") or {}
        formatted.append({
            "id": item.get("id"),
            "mal_id": item.get("idMal"),
            "title": t.get("english") or t.get("romaji") or t.get("native"),
            "title_romaji": t.get("romaji"),
            "title_english": t.get("english"),
            "title_native": t.get("native"),
            "poster": cov.get("extraLarge") or cov.get("large"),
            "banner": item.get("bannerImage"),
            "format": item.get("format"),
            "status": item.get("status"),
            "year": st.get("year"),
            "season": item.get("season"),
            "episodes": item.get("episodes"),
            "score": item.get("averageScore"),
            "genres": item.get("genres", []),
            "description": item.get("description")
        })

    return {
        "page": page_info.get("currentPage", page),
        "per_page": page_info.get("perPage", per_page),
        "total": page_info.get("total", len(formatted)),
        "has_next_page": page_info.get("hasNextPage", False),
        "results": formatted
    }


@api_router.get("/anime/popular")
async def api_anime_popular(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=50),
    auth: Dict[str, Any] = Depends(require_api_key)
):
    """Retrieve trending and popular anime titles."""
    gql = f"""
    query ($page: Int, $perPage: Int) {{
        Page(page: $page, perPage: $perPage) {{
            pageInfo {{ total currentPage lastPage hasNextPage perPage }}
            media(type: ANIME, sort: [TRENDING_DESC, POPULARITY_DESC]) {{
                {MEDIA_LIST_FIELDS}
            }}
        }}
    }}
    """
    data = await anilist_query(gql, {"page": page, "perPage": per_page})
    page_data = data.get("Page", {})
    page_info = page_data.get("pageInfo", {})
    results = proxy_deep_images(page_data.get("media", []))

    formatted = []
    for item in results:
        t = item.get("title") or {}
        cov = item.get("coverImage") or {}
        st = item.get("startDate") or {}
        formatted.append({
            "id": item.get("id"),
            "mal_id": item.get("idMal"),
            "title": t.get("english") or t.get("romaji"),
            "poster": cov.get("extraLarge") or cov.get("large"),
            "banner": item.get("bannerImage"),
            "format": item.get("format"),
            "status": item.get("status"),
            "year": st.get("year"),
            "episodes": item.get("episodes"),
            "score": item.get("averageScore"),
            "genres": item.get("genres", [])
        })

    return {
        "page": page_info.get("currentPage", page),
        "per_page": page_info.get("perPage", per_page),
        "total": page_info.get("total", len(formatted)),
        "has_next_page": page_info.get("hasNextPage", False),
        "results": formatted
    }


@api_router.get("/anime/episodes/{anime_id}")
async def api_anime_episodes(
    anime_id: int,
    request: Request,
    auth: Dict[str, Any] = Depends(require_api_key)
):
    """Get full episode catalog for an anime, including direct built-in player URLs and iframe embed snippets."""
    key = auth.get("key", "")
    host = str(request.base_url).rstrip("/")

    # Fetch anime info
    gql = """
    query ($id: Int) {
        Media(id: $id, type: ANIME) {
            id
            idMal
            title { english romaji native }
            coverImage { large extraLarge }
            bannerImage
            episodes
            status
            format
        }
    }
    """
    media_data = await anilist_query(gql, {"id": anime_id})
    media = media_data.get("Media") or {}
    t = media.get("title") or {}
    title = t.get("english") or t.get("romaji") or f"Anime {anime_id}"

    # Fetch provider episodes (with 2.0s fast timeout)
    episodes_list = []
    try:
        native = await asyncio.wait_for(provider_race.merged_episodes(anime_id), timeout=2.0)
        if native and isinstance(native, dict) and "providers" in native:
            for p_name, p_data in native["providers"].items():
                p_eps = (p_data.get("episodes") or {}).get("sub") or (p_data.get("episodes") or {}).get("dub")
                if p_eps and isinstance(p_eps, list):
                    episodes_list = p_eps
                    break
    except Exception:
        pass

    # If no provider episode list found, create synthetic entries from Anilist count
    if not episodes_list:
        total_eps = media.get("episodes") or 1
        episodes_list = [{"number": i, "title": f"Episode {i}"} for i in range(1, total_eps + 1)]

    formatted_episodes = []
    for ep in episodes_list:
        num = ep.get("number") or ep.get("episode") or 1
        ep_title = ep.get("title") or f"Episode {num}"
        ep_thumb = ep.get("image") or ep.get("thumbnail") or (media.get("coverImage") or {}).get("large")
        player_url = f"{host}/player?id={anime_id}&episode={num}&key={quote(key)}"
        iframe_snippet = f'<iframe src="{player_url}" width="100%" height="100%" frameborder="0" allowfullscreen allow="autoplay; fullscreen; picture-in-picture"></iframe>'

        formatted_episodes.append({
            "number": num,
            "title": ep_title,
            "thumbnail": ep_thumb,
            "player_url": player_url,
            "iframe_embed": iframe_snippet
        })

    return {
        "id": anime_id,
        "mal_id": media.get("idMal"),
        "title": title,
        "format": media.get("format"),
        "status": media.get("status"),
        "total_episodes": len(formatted_episodes),
        "poster": (media.get("coverImage") or {}).get("extraLarge") or (media.get("coverImage") or {}).get("large"),
        "banner": media.get("bannerImage"),
        "episodes": formatted_episodes
    }


@api_router.get("/anime/releases/{anime_id}")
async def api_anime_releases(
    anime_id: int,
    type: str = Query("sub", description="Audio type: 'sub' or 'dub'"),
    request: Request = None,
    auth: Dict[str, Any] = Depends(require_api_key)
):
    """
    Get comprehensive release tracking for an anime series:
    - Exact count of episodes released / aired so far
    - Total expected episodes and airing status (RELEASING, FINISHED, NOT_YET_RELEASED)
    - Next episode countdown and scheduled airing timestamp (if currently airing)
    - Official AniList HD posters and banner
    - Latest released episode and complete list of released episodes with direct player URLs and iframe embed codes
    """
    key = auth.get("key", "")
    host = str(request.base_url).rstrip("/")

    gql = """
    query ($id: Int) {
        Media(id: $id, type: ANIME) {
            id
            idMal
            title { english romaji native }
            coverImage { extraLarge large medium color }
            bannerImage
            episodes
            status
            format
            genres
            averageScore
            description(asHtml: false)
            startDate { year month day }
            endDate { year month day }
            nextAiringEpisode {
                airingAt
                timeUntilAiring
                episode
            }
        }
    }
    """
    try:
        media_data = await anilist_query(gql, {"id": anime_id})
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"AniList query failed: {str(e)}")

    media = media_data.get("Media")
    if not media:
        raise HTTPException(status_code=404, detail=f"Anime with ID {anime_id} not found.")

    t = media.get("title") or {}
    title = t.get("english") or t.get("romaji") or t.get("native") or f"Anime {anime_id}"

    # Fetch provider streamable episodes
    provider_episodes = []
    try:
        native = await asyncio.wait_for(provider_race.merged_episodes(anime_id), timeout=2.5)
        if native and isinstance(native, dict) and "providers" in native:
            for p_name, p_data in native["providers"].items():
                p_eps = (p_data.get("episodes") or {}).get(type) or (p_data.get("episodes") or {}).get("sub") or (p_data.get("episodes") or {}).get("dub")
                if p_eps and isinstance(p_eps, list) and len(p_eps) > len(provider_episodes):
                    provider_episodes = p_eps
    except Exception:
        pass

    # Calculate released episodes count
    next_ep = media.get("nextAiringEpisode")
    status = media.get("status") or "UNKNOWN"
    total_expected = media.get("episodes")

    if next_ep and next_ep.get("episode"):
        released_count = max(0, int(next_ep["episode"]) - 1)
    elif status == "FINISHED" and total_expected:
        released_count = int(total_expected)
    elif provider_episodes:
        released_count = len(provider_episodes)
    elif total_expected:
        released_count = int(total_expected)
    else:
        released_count = max(len(provider_episodes), 1)

    # Calculate next airing countdown
    next_airing_info = None
    if next_ep:
        airing_at = next_ep.get("airingAt")
        seconds = next_ep.get("timeUntilAiring", 0)
        days = seconds // 86400
        hours = (seconds % 86400) // 3600
        mins = (seconds % 3600) // 60
        countdown_str = f"{days}d {hours}h {mins}m" if days > 0 else f"{hours}h {mins}m"
        next_airing_info = {
            "episode": next_ep.get("episode"),
            "airing_at_timestamp": airing_at,
            "time_until_airing_seconds": seconds,
            "countdown": countdown_str
        }

    # Format list of released episodes
    formatted_episodes = []
    max_ep_num = max(released_count, len(provider_episodes))
    prov_dict = {}
    for pe in provider_episodes:
        pnum = pe.get("number") or pe.get("episode")
        if pnum is not None:
            try:
                prov_dict[int(pnum)] = pe
            except ValueError:
                pass

    for i in range(1, max_ep_num + 1):
        pe = prov_dict.get(i)
        ep_title = (pe.get("title") if pe else None) or f"Episode {i}"
        ep_thumb = (pe.get("image") or pe.get("thumbnail") if pe else None) or (media.get("coverImage") or {}).get("large")
        player_url = f"{host}/player?id={anime_id}&episode={i}&key={quote(key)}"
        iframe_snippet = f'<iframe src="{player_url}" width="100%" height="100%" frameborder="0" allowfullscreen allow="autoplay; fullscreen; picture-in-picture"></iframe>'
        stream_api = f"{host}/api/anime/stream?id={anime_id}&episode={i}&type={type}&key={quote(key)}"

        formatted_episodes.append({
            "number": i,
            "title": ep_title,
            "thumbnail": ep_thumb,
            "player_url": player_url,
            "iframe_embed": iframe_snippet,
            "stream_api": stream_api
        })

    latest_ep = formatted_episodes[-1] if formatted_episodes else None
    first_ep = formatted_episodes[0] if formatted_episodes else None

    cov = media.get("coverImage") or {}
    poster = cov.get("extraLarge") or cov.get("large") or cov.get("medium")

    return {
        "id": anime_id,
        "mal_id": media.get("idMal"),
        "title": title,
        "title_english": t.get("english"),
        "title_romaji": t.get("romaji"),
        "title_native": t.get("native"),
        "format": media.get("format"),
        "status": status,
        "is_airing": status == "RELEASING",
        "released_episodes_count": len(formatted_episodes),
        "total_expected_episodes": total_expected,
        "latest_released_episode": latest_ep,
        "first_released_episode": first_ep,
        "next_airing": next_airing_info,
        "poster": poster,
        "banner": media.get("bannerImage"),
        "score": media.get("averageScore"),
        "genres": media.get("genres", []),
        "synopsis": media.get("description") or "",
        "episodes": formatted_episodes
    }


@api_router.get("/anime/stream")
async def api_anime_stream(
    id: int = Query(..., description="AniList Anime ID"),
    episode: int = Query(1, ge=1, description="Episode number"),
    type: str = Query("sub", description="Audio type: 'sub' or 'dub'"),
    server: Optional[str] = Query(None, description="Preferred server e.g. DatSaV or Vidplay"),
    request: Request = None,
    auth: Dict[str, Any] = Depends(require_api_key)
):
    """
    Extract raw video streams, proxy URLs, and subtitles for an episode.
    Proxied streams bypass CORS and Referer security checks for direct player integration.
    """
    host = str(request.base_url).rstrip("/")
    key = auth.get("key", "")

    # 1. Extract sources via native provider race
    extract_res = None
    try:
        raced = await asyncio.wait_for(provider_race.race_watch(id, episode, type, preferred=server), timeout=30.0)
        if raced and raced.get("streams"):
            extract_res = {
                "provider": raced.get("provider", "native"),
                "streams": raced["streams"],
                "subtitles": provider_race.merge_subtitles(raced["streams"])
            }
    except Exception as e:
        print(f"[API] race_watch failed for {id} ep {episode}: {e}")

    # 2. Fallback to miruro pipe targets if native race returned no streams
    if not extract_res or not extract_res.get("streams"):
        try:
            from src.endpoints import fetch_raw_episodes, encode_pipe_request, iter_miruro_pipe_targets, decode_pipe_response
            import base64
            import httpx
            raw_eps = await asyncio.wait_for(fetch_raw_episodes(id), timeout=8.0)
            provs = (raw_eps or {}).get("providers", {})
            ranking = ["zoro", "bee", "telli", "arc", "yugen", "jet", "neo", "kiwi"]
            for prov in ranking:
                if prov in provs:
                    eps_data = (provs[prov].get("episodes") or {}).get(type) or (provs[prov].get("episodes") or {}).get("sub")
                    if isinstance(eps_data, list):
                        for ep_item in eps_data:
                            if ep_item.get("number") == episode and ep_item.get("id"):
                                enc_id = base64.urlsafe_b64encode(ep_item["id"].encode()).decode().rstrip('=')
                                payload = {
                                    "path": "sources",
                                    "method": "GET",
                                    "query": {
                                        "episodeId": enc_id,
                                        "provider": prov,
                                        "category": type,
                                        "anilistId": id,
                                    },
                                    "body": None,
                                    "version": "0.1.0",
                                }
                                req_enc = encode_pipe_request(payload)
                                async with httpx.AsyncClient(timeout=8.0) as client:
                                    for pipe_target, pheaders in iter_miruro_pipe_targets(req_enc):
                                        res = await client.get(pipe_target, headers=pheaders)
                                        if res.status_code == 200:
                                            decoded = decode_pipe_response(res.text.strip())
                                            if decoded and decoded.get("streams"):
                                                extract_res = decoded
                                                break
                                if extract_res:
                                    break
                if extract_res:
                    break
        except Exception as e:
            print(f"[API] fallback pipe failed: {e}")

    if not extract_res or not extract_res.get("streams"):
        raise HTTPException(status_code=404, detail="No video streams found for this episode.")

    raw_streams = extract_res.get("streams", [])
    raw_subtitles = extract_res.get("subtitles", [])

    # Format streams with proxy links
    processed_streams = []
    for s in raw_streams:
        stype = (s.get("type") or "hls").lower()
        surl = s.get("url", "")
        sref = s.get("referer", "https://play.echovideo.ru/")
        server_name = s.get("server") or ("DatSaV" if stype == "mp4" else "Vidplay")

        if stype == "mp4":
            proxy_url = f"{host}/proxy_mp4?url={quote(surl, safe='')}&referer={quote(sref, safe='')}"
        else:
            proxy_url = f"{host}/proxy_m3u8?url={quote(surl, safe='')}&referer={quote(sref, safe='')}"

        processed_streams.append({
            "server": server_name,
            "type": stype,
            "quality": s.get("quality", "auto"),
            "stream_url": proxy_url,
            "raw_url": surl,
            "referer": sref
        })

    # Subtitles with CORS proxy
    processed_subtitles = []
    for sub in raw_subtitles:
        sub_url = sub.get("url", "")
        lang = sub.get("lang") or sub.get("label") or "English"
        if sub_url.startswith("http"):
            proxied_sub = f"{host}/proxy_sub?url={quote(sub_url, safe='')}"
        else:
            proxied_sub = sub_url

        processed_subtitles.append({
            "language": lang,
            "url": proxied_sub,
            "format": "srt" if sub_url.endswith(".srt") else "vtt"
        })

    # Fetch AniSkip skip times
    skip_info = {"found": False, "intro": None, "outro": None}
    try:
        import httpx
        skip_api = f"https://api.aniskip.com/v2/skip-times/{id}/{episode}?types=op&types=ed&episodeLength=0"
        async with httpx.AsyncClient(timeout=4.0) as client:
            s_resp = await client.get(skip_api)
            if s_resp.status_code == 200:
                s_data = s_resp.json()
                if s_data.get("found") and isinstance(s_data.get("results"), list):
                    for item in s_data["results"]:
                        st = item.get("skipType")
                        iv = item.get("interval") or {}
                        start = iv.get("startTime")
                        end = iv.get("endTime")
                        if start is not None and end is not None:
                            if st == "op" and not skip_info["intro"]:
                                skip_info["intro"] = {"start": round(float(start), 2), "end": round(float(end), 2)}
                                skip_info["found"] = True
                            elif st == "ed" and not skip_info["outro"]:
                                skip_info["outro"] = {"start": round(float(start), 2), "end": round(float(end), 2)}
                                skip_info["found"] = True
    except Exception:
        pass

    player_url = f"{host}/player?id={id}&episode={episode}&type={type}&key={quote(key)}"

    return {
        "anime_id": id,
        "episode": episode,
        "audio": type,
        "player_url": player_url,
        "iframe_embed": f'<iframe src="{player_url}" width="100%" height="100%" frameborder="0" allowfullscreen allow="autoplay; fullscreen; picture-in-picture"></iframe>',
        "skip_times": skip_info,
        "streams": processed_streams,
        "subtitles": processed_subtitles
    }


@api_router.get("/anime/player")
async def api_anime_player(
    id: int = Query(..., description="AniList Anime ID"),
    episode: int = Query(1, ge=1, description="Episode number"),
    type: str = Query("sub", description="Audio type: 'sub' or 'dub'"),
    server: Optional[str] = Query(None, description="Preferred video server"),
    request: Request = None,
    auth: Dict[str, Any] = Depends(require_api_key)
):
    """
    Get the ready-to-render Player metadata, player web URL, and iframe embed code.
    This provides the user's video with the website's built-in player (horizontal hover volume slider,
    10s skip backward/forward, AniSkip intro/outro button at bottom: 85px, and yellow timeline markers).
    """
    host = str(request.base_url).rstrip("/")
    key = auth.get("key", "")

    player_url = f"{host}/player?id={id}&episode={episode}&type={type}&key={quote(key)}"
    if server:
        player_url += f"&server={quote(server)}"

    iframe_code = (
        f'<iframe src="{player_url}" '
        f'width="100%" height="100%" '
        f'frameborder="0" '
        f'allow="autoplay; fullscreen; picture-in-picture; encrypted-media" '
        f'allowfullscreen></iframe>'
    )

    # Also resolve skip times
    skip_info = {"found": False, "intro": None, "outro": None}
    try:
        import httpx
        skip_api = f"https://api.aniskip.com/v2/skip-times/{id}/{episode}?types=op&types=ed&episodeLength=0"
        async with httpx.AsyncClient(timeout=4.0) as client:
            s_resp = await client.get(skip_api)
            if s_resp.status_code == 200:
                s_data = s_resp.json()
                if s_data.get("found") and isinstance(s_data.get("results"), list):
                    for item in s_data["results"]:
                        st = item.get("skipType")
                        iv = item.get("interval") or {}
                        start = iv.get("startTime")
                        end = iv.get("endTime")
                        if start is not None and end is not None:
                            if st == "op" and not skip_info["intro"]:
                                skip_info["intro"] = {"start": round(float(start), 2), "end": round(float(end), 2)}
                                skip_info["found"] = True
                            elif st == "ed" and not skip_info["outro"]:
                                skip_info["outro"] = {"start": round(float(start), 2), "end": round(float(end), 2)}
                                skip_info["found"] = True
    except Exception:
        pass

    return {
        "status": "success",
        "anime_id": id,
        "episode": episode,
        "audio": type,
        "player_url": player_url,
        "iframe_embed": iframe_code,
        "features": {
            "skip_buttons": "Rewind 10s & Forward 10s between play and volume",
            "volume_slider": "Horizontal hover-expand slider with drop shadow",
            "aniskip_button": "Floating button at bottom: 85px (above timeline)",
            "timeline_markers": "Yellow highlighted intro and outro intervals",
            "hotkeys": "Space (Play/Pause), Left/Right (Seek 5s), Up/Down (Volume), F (Fullscreen)"
        },
        "skip_times": skip_info
    }


# ==========================================================
# 2. MANGA / MANHWA / MANHUA ENDPOINTS
# ==========================================================

@api_router.get("/manga/search")
async def api_manga_search(
    q: Optional[str] = Query(None, description="Search keyword"),
    type: str = Query("all", description="Type filter: 'all', 'manhwa', 'manga', 'manhua'"),
    source: str = Query("all", description="Source: 'all', 'vortex', 'toraka', 'mangadex', 'anilist'"),
    page: int = Query(1, ge=1),
    request: Request = None,
    auth: Dict[str, Any] = Depends(require_api_key)
):
    """
    Search manga, manhwa, and manhua across multiple sources.
    Every poster is automatically verified with official AniList HD art and MangaDex anti-hotlink proxies.
    """
    type_norm = type.lower()
    country_map = {"manhwa": "KR", "manhua": "CN", "manga": "JP"}
    target_country = country_map.get(type_norm)

    combined = []
    if source == "all":
        tasks = [
            fetch_vortex_posts(page=page, query=q),
            fetch_toraka_series(page=page, query=q),
            search_mangadex(q or "leveling", limit=15),
            query_anilist_manga(search=q, country=target_country, page=page, per_page=15)
        ]
        res_list = await asyncio.gather(*tasks, return_exceptions=True)
        for r in res_list:
            if isinstance(r, list):
                combined.extend(r)
            elif isinstance(r, dict) and "results" in r:
                combined.extend(r["results"])
    elif source == "vortex":
        combined = await fetch_vortex_posts(page=page, query=q)
    elif source == "toraka":
        combined = await fetch_toraka_series(page=page, query=q)
    elif source == "mangadex":
        combined = await search_mangadex(q or "leveling", limit=20)
    elif source == "anilist":
        data = await query_anilist_manga(search=q, country=target_country, page=page, per_page=20)
        combined = data.get("results", [])

    if type_norm in ("manhwa", "manga", "manhua"):
        combined = [r for r in combined if type_norm in r.get("type", "").lower()]

    aggregated = aggregate_and_deduplicate_manga(combined)
    aggregated = await enrich_with_anilist_posters(aggregated)

    host = str(request.base_url).rstrip("/")
    key = auth.get("key", "")

    # Format cleanly with reader and info links
    formatted = []
    for item in aggregated:
        slug = item.get("slug") or item.get("id") or ""
        src = item.get("default_source") or item.get("source") or "vortex"
        cover = item.get("cover") or item.get("image") or ""
        if cover.startswith("/"):
            cover = f"{host}{cover}"

        formatted.append({
            "title": item.get("title"),
            "slug": slug,
            "source": src,
            "type": item.get("type") or "manhwa",
            "poster": cover,
            "description": item.get("description"),
            "status": item.get("status"),
            "rating": item.get("score") or item.get("rating"),
            "genres": item.get("genres", []),
            "info_url": f"{host}/api/manga/info/{slug}?source={src}&key={quote(key)}"
        })

    return {
        "page": page,
        "type": type,
        "source": source,
        "total": len(formatted),
        "results": formatted
    }


@api_router.get("/manga/popular")
async def api_manga_popular(
    type: str = Query("all", description="Type filter: 'all', 'manhwa', 'manga', 'manhua'"),
    source: str = Query("all", description="Source: 'all', 'vortex', 'toraka', 'anilist'"),
    request: Request = None,
    auth: Dict[str, Any] = Depends(require_api_key)
):
    """Get trending and popular manhwa, manga, and manhua with HD posters and descriptions."""
    country_map = {"manhwa": "KR", "manhua": "CN", "manga": "JP"}
    target_country = country_map.get(type.lower()) if type != "all" else None

    combined = []
    if source == "all":
        tasks = [
            fetch_vortex_posts(page=1),
            fetch_toraka_series(page=1, per_page=15),
            search_mangadex("leveling", limit=12),
            query_anilist_manga(search=None, country=target_country, page=1, per_page=20, sort="POPULARITY_DESC")
        ]
        res_list = await asyncio.gather(*tasks, return_exceptions=True)
        for r in res_list:
            if isinstance(r, list):
                combined.extend(r)
            elif isinstance(r, dict) and "results" in r:
                combined.extend(r["results"])
    elif source == "vortex":
        combined = await fetch_vortex_posts(page=1)
    elif source == "toraka":
        combined = await fetch_toraka_series(page=1, per_page=15)
    else:
        data = await query_anilist_manga(search=None, country=target_country, page=1, per_page=16)
        combined = data.get("results", [])

    aggregated = aggregate_and_deduplicate_manga(combined)
    aggregated = await enrich_with_anilist_posters(aggregated)

    host = str(request.base_url).rstrip("/")
    key = auth.get("key", "")

    formatted = []
    for item in aggregated:
        slug = item.get("slug") or item.get("id") or ""
        src = item.get("default_source") or item.get("source") or "vortex"
        cover = item.get("cover") or item.get("image") or ""
        if cover.startswith("/"):
            cover = f"{host}{cover}"

        formatted.append({
            "title": item.get("title"),
            "slug": slug,
            "source": src,
            "type": item.get("type") or "manhwa",
            "poster": cover,
            "description": item.get("description"),
            "rating": item.get("score") or item.get("rating"),
            "genres": item.get("genres", []),
            "info_url": f"{host}/api/manga/info/{slug}?source={src}&key={quote(key)}"
        })

    return {
        "type": type,
        "source": source,
        "total": len(formatted),
        "results": formatted
    }


@api_router.get("/manga/info/{slug_or_id}")
async def api_manga_info(
    slug_or_id: str,
    source: str = Query("vortex", description="vortex, mangadex, toraka, anilist"),
    request: Request = None,
    auth: Dict[str, Any] = Depends(require_api_key)
):
    """
    Get full metadata for a manga/manhwa/manhua title including synopsis, official HD poster,
    and a complete list of chapters with direct reader links.
    """
    host = str(request.base_url).rstrip("/")
    key = auth.get("key", "")

    info = {}
    if source == "vortex":
        info = await fetch_vortex_chapters(slug_or_id)
    elif source == "toraka":
        info = await fetch_toraka_chapters(slug_or_id)
    elif source == "mangadex":
        info = await fetch_mangadex_chapters(slug_or_id)
    else:
        info = await fetch_vortex_chapters(slug_or_id)

    # Attach AniList poster
    title = info.get("title") or slug_or_id.replace("-", " ")
    anilist_cover = await get_or_fetch_anilist_poster(title)
    poster = anilist_cover or info.get("cover") or ""
    if poster.startswith("/"):
        poster = f"{host}{poster}"

    # Build chapter list with reader links
    raw_chapters = info.get("chapters", [])
    formatted_chapters = []
    for ch in raw_chapters:
        ch_id = ch.get("id") or ch.get("chapter_id")
        ch_num = ch.get("number") or ch.get("ch") or "1"
        ch_title = ch.get("title") or f"Chapter {ch_num}"
        reader_url = f"{host}/manga/reader/{ch_id}?source={source}&key={quote(key)}"

        formatted_chapters.append({
            "id": ch_id,
            "number": ch_num,
            "title": ch_title,
            "is_locked": ch.get("is_locked", False),
            "release_date": ch.get("releaseDate") or ch.get("date"),
            "reader_url": reader_url,
            "chapter_api": f"{host}/api/manga/chapter/{ch_id}?source={source}&key={quote(key)}"
        })

    return {
        "title": title,
        "slug": slug_or_id,
        "source": source,
        "poster": poster,
        "description": info.get("description") or info.get("synopsis") or "",
        "status": info.get("status"),
        "type": info.get("type") or "manhwa",
        "genres": info.get("genres", []),
        "total_chapters": len(formatted_chapters),
        "chapters": formatted_chapters
    }


@api_router.get("/manga/chapter/{chapter_id}")
async def api_manga_chapter(
    chapter_id: str,
    source: str = Query("vortex", description="vortex or mangadex"),
    request: Request = None,
    auth: Dict[str, Any] = Depends(require_api_key)
):
    """
    Get all page image URLs for a chapter.
    Images are pre-formatted with our `/proxy_image` endpoint so you can embed them
    in any app or website without CORS or Referer blocking.
    Also provides a direct web reader URL and iframe embed code.
    """
    host = str(request.base_url).rstrip("/")
    key = auth.get("key", "")

    try:
        if source == "mangadex":
            raw_data = await fetch_mangadex_chapter_pages(chapter_id)
        else:
            raw_data = await fetch_vortex_chapter_pages(chapter_id)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Failed to fetch chapter images: {str(e)}")

    pages_list = raw_data.get("pages", [])
    referer = raw_data.get("referer", "https://vortexscans.org/")

    # Construct CORS-safe, Referer-safe image links
    formatted_pages = []
    for idx, img_url in enumerate(pages_list, 1):
        proxied_url = f"{host}/proxy_image?url={quote(img_url, safe='')}&referer={quote(referer, safe='')}"
        formatted_pages.append({
            "page": idx,
            "url": proxied_url,
            "raw_url": img_url
        })

    reader_url = f"{host}/manga/reader/{chapter_id}?source={source}&key={quote(key)}"
    iframe_embed = f'<iframe src="{reader_url}" width="100%" height="800" frameborder="0" allowfullscreen></iframe>'

    return {
        "chapter_id": chapter_id,
        "number": raw_data.get("number"),
        "title": raw_data.get("title") or f"Chapter {raw_data.get('number', '')}",
        "source": source,
        "pages_count": len(formatted_pages),
        "next_chapter": raw_data.get("next_chapter"),
        "prev_chapter": raw_data.get("prev_chapter"),
        "reader_url": reader_url,
        "iframe_embed": iframe_embed,
        "pages": formatted_pages
    }


@api_router.get("/manga/releases/{slug_or_id}")
async def api_manga_releases(
    slug_or_id: str,
    source: str = Query("vortex", description="Source provider: 'vortex', 'mangadex', or 'auto'"),
    include_pages: bool = Query(False, description="Whether to include panel images for the target chapter"),
    chapter: Optional[str] = Query(None, description="'latest', 'first', or specific chapter number/ID to retrieve panel images"),
    limit: int = Query(250, ge=1, le=500, description="Max chapters to return"),
    request: Request = None,
    auth: Dict[str, Any] = Depends(require_api_key)
):
    """
    Get detailed release tracking for a manga, manhwa, or manhua:
    - Exact count of chapters released so far
    - Latest released chapter & first released chapter
    - High-definition official posters and banner
    - Panel images of the latest (or selected) chapter formatted with CORS-safe /proxy_image URLs
    - Complete ordered chapter catalog with direct reader URLs and iframe embed snippets
    """
    key = auth.get("key", "")
    host = str(request.base_url).rstrip("/")

    chapters_data = None
    used_source = source

    if source in ("vortex", "auto"):
        try:
            v_res = await fetch_vortex_chapters(slug_or_id)
            if v_res and v_res.get("chapters"):
                chapters_data = v_res
                used_source = "vortex"
        except Exception:
            pass

    if not chapters_data and source in ("mangadex", "auto"):
        try:
            is_uuid = "-" in slug_or_id and len(slug_or_id) >= 32
            target_id = slug_or_id
            target_title = slug_or_id
            if not is_uuid:
                md_s = await search_mangadex(slug_or_id, limit=1)
                if md_s:
                    target_id = md_s[0]["id"]
                    target_title = md_s[0]["title"]
            md_res = await fetch_mangadex_chapters(target_id, limit=limit)
            if md_res and md_res.get("chapters"):
                md_res["title"] = target_title
                md_res["slug"] = target_id
                md_res["type"] = "MANGA"
                chapters_data = md_res
                used_source = "mangadex"
        except Exception:
            pass

    if not chapters_data or not chapters_data.get("chapters"):
        raise HTTPException(
            status_code=404,
            detail=f"No released chapters found for '{slug_or_id}' on source '{source}'."
        )

    raw_chapters = chapters_data.get("chapters", [])
    series_title = chapters_data.get("title") or slug_or_id
    series_slug = chapters_data.get("slug") or slug_or_id
    series_type = chapters_data.get("type") or "MANHWA"

    # Sort chapters in descending order by chapter number (latest first)
    def parse_ch_num(ch_obj):
        val = str(ch_obj.get("number") or "0")
        try:
            return float(re.findall(r"\d+(?:\.\d+)?", val)[0])
        except Exception:
            return 0.0

    sorted_chapters = sorted(raw_chapters, key=parse_ch_num, reverse=True)

    # Fetch official AniList poster, banner, and metadata
    poster = None
    banner = None
    synopsis = ""
    status = "RELEASING"
    genres = []
    score = None

    try:
        anilist_meta = await query_anilist_manga(search=series_title, per_page=1)
        res_list = anilist_meta.get("results", [])
        if res_list:
            top_meta = res_list[0]
            poster = top_meta.get("cover")
            banner = top_meta.get("banner")
            synopsis = top_meta.get("synopsis") or ""
            status = top_meta.get("status") or "RELEASING"
            genres = top_meta.get("genres") or []
            score = top_meta.get("score")
    except Exception:
        pass

    if not poster:
        poster = await get_or_fetch_anilist_poster(series_title)
    if not poster:
        poster = chapters_data.get("cover")

    formatted_chapters = []
    for ch in sorted_chapters[:limit]:
        ch_id = str(ch.get("id"))
        ch_num = str(ch.get("number") or "0")
        ch_title = ch.get("title") or f"Chapter {ch_num}"
        reader_url = f"{host}/manga/reader/{ch_id}?source={used_source}&key={quote(key)}"
        chapter_api = f"{host}/api/manga/chapter/{ch_id}?source={used_source}&key={quote(key)}"
        formatted_chapters.append({
            "id": ch_id,
            "number": ch_num,
            "title": ch_title,
            "is_locked": ch.get("is_locked", False),
            "release_date": ch.get("created_at") or ch.get("releaseDate") or ch.get("date"),
            "reader_url": reader_url,
            "chapter_api": chapter_api
        })

    latest_ch = formatted_chapters[0] if formatted_chapters else None
    first_ch = formatted_chapters[-1] if formatted_chapters else None
    latest_unlocked_ch = next((c for c in formatted_chapters if not c.get("is_locked")), latest_ch)

    # Handle panel images
    chapter_panels = None
    if include_pages or chapter is not None:
        target_ch = latest_ch
        if chapter:
            if chapter.lower() == "first":
                target_ch = first_ch
            elif chapter.lower() == "latest":
                target_ch = latest_ch
            elif chapter.lower() in ("latest_unlocked", "unlocked", "free"):
                target_ch = latest_unlocked_ch
            else:
                found = next((c for c in formatted_chapters if c["number"] == chapter or c["id"] == chapter), None)
                if found:
                    target_ch = found
        elif latest_ch and latest_ch.get("is_locked") and latest_unlocked_ch:
            target_ch = latest_unlocked_ch

        if target_ch:
            target_id = target_ch["id"]
            try:
                if used_source == "mangadex":
                    raw_pages_data = await fetch_mangadex_chapter_pages(target_id)
                else:
                    raw_pages_data = await fetch_vortex_chapter_pages(target_id)

                p_list = raw_pages_data.get("pages", [])
                p_ref = raw_pages_data.get("referer", "https://vortexscans.org/")
                formatted_pages = []
                for idx, p_url in enumerate(p_list, 1):
                    proxied_url = f"{host}/proxy_image?url={quote(p_url, safe='')}&referer={quote(p_ref, safe='')}"
                    formatted_pages.append({
                        "page": idx,
                        "url": proxied_url,
                        "raw_url": p_url
                    })

                ch_reader_url = f"{host}/manga/reader/{target_id}?source={used_source}&key={quote(key)}"
                chapter_panels = {
                    "chapter_id": target_id,
                    "number": target_ch["number"],
                    "title": target_ch["title"],
                    "is_locked": target_ch.get("is_locked", False),
                    "pages_count": len(formatted_pages),
                    "reader_url": ch_reader_url,
                    "iframe_embed": f'<iframe src="{ch_reader_url}" width="100%" height="800" frameborder="0" allowfullscreen></iframe>',
                    "pages": formatted_pages
                }
            except Exception as e:
                chapter_panels = {
                    "chapter_id": target_id,
                    "error": f"Failed to fetch panel images: {str(e)}"
                }

    return {
        "id": chapters_data.get("id"),
        "title": series_title,
        "slug": series_slug,
        "type": series_type,
        "source": used_source,
        "status": status,
        "released_chapters_count": len(sorted_chapters),
        "poster": poster,
        "banner": banner,
        "synopsis": synopsis,
        "genres": genres,
        "score": score,
        "latest_released_chapter": latest_ch,
        "latest_unlocked_chapter": latest_unlocked_ch,
        "first_released_chapter": first_ch,
        "chapter_panels": chapter_panels,
        "chapters": formatted_chapters
    }


# ==========================================================
# 3. UNIFIED RELEASES ENDPOINT
# ==========================================================

@api_router.get("/releases")
async def api_unified_releases(
    type: str = Query(..., description="Media type: 'anime' or 'manga'"),
    id: str = Query(..., description="AniList Anime ID (for anime) or Manga slug/ID (for manga)"),
    source: str = Query("vortex", description="For manga: 'vortex', 'mangadex', or 'auto'"),
    include_pages: bool = Query(False, description="For manga: whether to include chapter panel images"),
    chapter: Optional[str] = Query(None, description="For manga: target chapter ('latest', 'first', or chapter number)"),
    sub_or_dub: str = Query("sub", description="For anime: audio type 'sub' or 'dub'"),
    limit: int = Query(250, ge=1, le=500, description="For manga: max chapters to return"),
    request: Request = None,
    auth: Dict[str, Any] = Depends(require_api_key)
):
    """
    Unified Release Tracking Hub for both Anime & Manga/Manhwa:
    - Automatically routes to Anime Releases or Manga Releases
    - Returns exact counts of released episodes or chapters
    - High-definition official posters and artwork
    - Proper panel preview images and direct streaming/reading players
    """
    media_type = type.strip().lower()
    if media_type == "anime":
        try:
            anime_id = int(id)
        except ValueError:
            raise HTTPException(status_code=400, detail="For anime releases, 'id' must be an integer AniList ID.")
        return await api_anime_releases(anime_id=anime_id, type=sub_or_dub, request=request, auth=auth)
    elif media_type in ("manga", "manhwa", "manhua"):
        return await api_manga_releases(
            slug_or_id=id,
            source=source,
            include_pages=include_pages,
            chapter=chapter,
            limit=limit,
            request=request,
            auth=auth
        )
    else:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid media type '{type}'. Please specify 'anime' or 'manga'."
        )
