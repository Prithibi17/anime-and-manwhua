import asyncio
from fastapi import APIRouter, Query, HTTPException, Response
from fastapi.responses import StreamingResponse
from typing import Optional, List, Dict, Any
import httpx
from urllib.parse import unquote, quote

from src.manga.vortex import fetch_vortex_posts, fetch_vortex_chapters, fetch_vortex_chapter_pages
from src.manga.toraka import fetch_toraka_series, fetch_toraka_chapters
from src.manga.mangadex import search_mangadex, fetch_mangadex_chapters, fetch_mangadex_chapter_pages
from src.manga.anilist_manga import query_anilist_manga

router = APIRouter(prefix="/manga", tags=["Manga / Manhwa / Manhua"])


import re

def normalize_manga_title(title: str) -> str:
    if not title:
        return ""
    t = title.replace("’", "'").replace("‘", "'").replace("“", '"').replace("”", '"').replace("\ufffd", "'")
    t = re.sub(r'\(.*?\)|\[.*?\]', '', t.lower())
    return re.sub(r'[^a-z0-9]', '', t).strip()

ANILIST_POSTER_CACHE: Dict[str, str] = {}
ANILIST_SEMAPHORE = asyncio.Semaphore(5)

def generate_title_search_variants(title: str) -> List[str]:
    """Generate search variants for light novel / manga titles ordered from most distinctive to broad."""
    if not title:
        return []
    t = title.replace("’", "'").replace("‘", "'").replace("“", '"').replace("”", '"').replace("\ufffd", "'")
    clean = re.sub(r'\(.*?\)|\[.*?\]', '', t).strip()
    clean = re.sub(r'\s+', ' ', clean)
    vars = [clean]
    
    clean_no_punct = re.sub(r"[^a-zA-Z0-9\s]", ' ', clean)
    clean_no_punct = re.sub(r'\s+', ' ', clean_no_punct).strip()
    if clean_no_punct != clean:
        vars.append(clean_no_punct)

    # 1. Before punctuation separator
    for sep in [' - ', ' : ', ' – ', ' — ', ' ~ ', ' | ']:
        if sep in clean:
            part = clean.split(sep)[0].strip()
            if len(part) >= 4:
                vars.append(part)
    
    # 2. First 4 words, first 3 words, first 2 words
    words = clean_no_punct.split()
    if len(words) >= 4:
        vars.append(' '.join(words[:4]))
    if len(words) >= 3:
        vars.append(' '.join(words[:3]))
    if len(words) >= 2 and len(words[0]) + len(words[1]) >= 8:
        vars.append(' '.join(words[:2]))

    res = []
    seen = set()
    for v in vars:
        c = re.sub(r'\s+', ' ', v).strip()
        if c and c.lower() not in seen:
            seen.add(c.lower())
            res.append(c)
    return res

async def get_or_fetch_anilist_poster(title: str) -> Optional[str]:
    """Retrieve official high-definition poster from AniList, with proxied MangaDex fallback."""
    if not title:
        return None
    norm = normalize_manga_title(title)
    if norm in ANILIST_POSTER_CACHE:
        return ANILIST_POSTER_CACHE[norm]

    variants = generate_title_search_variants(title)
    async with ANILIST_SEMAPHORE:
        # Step 1: AniList
        for v in variants:
            try:
                data = await query_anilist_manga(search=v, per_page=2)
                res = data.get("results", [])
                if res and res[0].get("cover"):
                    cover = res[0]["cover"]
                    ANILIST_POSTER_CACHE[norm] = cover
                    return cover
            except Exception:
                pass

        # Step 2: MangaDex fallback if AniList didn't match (proxied to bypass anti-hotlink)
        for v in variants:
            try:
                md_res = await search_mangadex(v, limit=1)
                if md_res and md_res[0].get("cover"):
                    raw_cover = md_res[0]["cover"]
                    cover = f"/manga/proxy_cover?url={quote(raw_cover, safe='')}" if "mangadex.org" in raw_cover else raw_cover
                    ANILIST_POSTER_CACHE[norm] = cover
                    return cover
            except Exception:
                pass

    return None

def aggregate_and_deduplicate_manga(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Group manga items across multiple sources into a single unified record with selectable sources."""
    grouped: Dict[str, Dict[str, Any]] = {}
    order: List[str] = []

    for item in items:
        raw_title = item.get("title") or "Untitled Manga"
        norm = normalize_manga_title(raw_title)
        if not norm:
            norm = f"id_{item.get('id', '')}_{item.get('source', '')}"

        src = item.get("source", "vortex")
        src_label = item.get("source_label") or src.capitalize()
        source_entry = {
            "source": src,
            "label": src_label,
            "id": item.get("id"),
            "slug": item.get("slug") or item.get("id"),
            "title": raw_title,
            "chapters_count": item.get("chapters_count", 0),
            "cover": item.get("cover") or ""
        }

        # Cache AniList cover if present
        if src == "anilist" and item.get("cover"):
            ANILIST_POSTER_CACHE[norm] = item["cover"]

        is_anilist = (src == "anilist") or ("anilist.co" in (item.get("cover") or ""))

        if norm in grouped:
            entry = grouped[norm]
            entry["sources"][src] = source_entry
            if src not in entry["source_list"]:
                entry["source_list"].append(src)

            # Official AniList posters take highest priority
            if is_anilist and item.get("cover"):
                entry["cover"] = item["cover"]
                if item.get("banner"):
                    entry["banner"] = item["banner"]
                if item.get("genres"):
                    entry["genres"] = item["genres"]
                if item.get("score"):
                    entry["rating"] = item["score"]
            elif not entry.get("cover") or "placeholder" in entry.get("cover", ""):
                if item.get("cover"):
                    entry["cover"] = item["cover"]

            # Use best available synopsis
            if not entry.get("synopsis") and item.get("synopsis"):
                entry["synopsis"] = item["synopsis"]
            # Keep highest chapters count
            if item.get("chapters_count", 0) > entry.get("chapters_count", 0):
                entry["chapters_count"] = item["chapters_count"]
        else:
            order.append(norm)
            cover = item.get("cover") or ANILIST_POSTER_CACHE.get(norm, "")
            grouped[norm] = {
                "id": item.get("id"),
                "slug": item.get("slug") or item.get("id"),
                "title": raw_title,
                "type": item.get("type") or "MANHWA",
                "cover": cover,
                "banner": item.get("banner") or "",
                "synopsis": item.get("synopsis") or "",
                "status": item.get("status") or "Ongoing",
                "rating": item.get("rating") or item.get("score") or 0,
                "chapters_count": item.get("chapters_count") or 0,
                "sources": {src: source_entry},
                "source_list": [src],
                "default_source": src,
                "source": src
            }

    # Decide default source priority for each group:
    # 1. vortex (direct unbundled webtoon images)
    # 2. mangadex (global feed)
    # 3. toraka (ShineiAPI)
    for norm in order:
        entry = grouped[norm]
        # Check cache if cover is still missing AniList quality
        if norm in ANILIST_POSTER_CACHE and ("anilist.co" not in entry.get("cover", "")):
            entry["cover"] = ANILIST_POSTER_CACHE[norm]

        if "vortex" in entry["sources"]:
            entry["default_source"] = "vortex"
            entry["slug"] = entry["sources"]["vortex"]["slug"]
        elif "mangadex" in entry["sources"]:
            entry["default_source"] = "mangadex"
            entry["slug"] = entry["sources"]["mangadex"]["slug"]
        elif "toraka" in entry["sources"]:
            entry["default_source"] = "toraka"
            entry["slug"] = entry["sources"]["toraka"]["slug"]
        else:
            first_src = entry["source_list"][0]
            entry["default_source"] = first_src
            entry["slug"] = entry["sources"][first_src]["slug"]
        entry["source"] = entry["default_source"]
        entry["cover_image"] = entry.get("cover") or ""
        entry["image"] = entry.get("cover") or ""

    return [grouped[norm] for norm in order]


async def enrich_with_anilist_posters(items: List[Dict[str, Any]], limit_lookups: int = 120) -> List[Dict[str, Any]]:
    """Enrich manga items with official high-resolution posters from AniList, prioritizing missing or mangadex covers first."""
    lookups = 0
    tasks = []
    task_indices = []

    # Pass 1: Items with NO cover, placeholder, or raw mangadex/toraka cover that needs official poster
    for idx, item in enumerate(items):
        cover = item.get("cover") or ""
        needs_better_poster = not cover or "placeholder" in cover or "mangadex.org" in cover or "toraka.com" in cover
        if needs_better_poster and lookups < limit_lookups:
            title = item.get("title")
            if title:
                lookups += 1
                tasks.append(get_or_fetch_anilist_poster(title))
                task_indices.append(idx)

    # Pass 2: Remaining items that don't have an AniList poster yet
    for idx, item in enumerate(items):
        if idx in task_indices:
            continue
        cover = item.get("cover") or ""
        if "anilist.co" not in cover and lookups < limit_lookups:
            title = item.get("title")
            if title:
                lookups += 1
                tasks.append(get_or_fetch_anilist_poster(title))
                task_indices.append(idx)

    if tasks:
        results = await asyncio.gather(*tasks, return_exceptions=True)
        for idx, res in zip(task_indices, results):
            if isinstance(res, str) and res:
                items[idx]["cover"] = res
                items[idx]["cover_image"] = res
                items[idx]["image"] = res
                items[idx]["is_anilist_poster"] = True

    # Ensure any remaining MangaDex cover is always safely proxied to bypass anti-hotlinking
    for item in items:
        c = item.get("cover") or ""
        if "mangadex.org" in c and not c.startswith("/manga/proxy_cover"):
            proxied = f"/manga/proxy_cover?url={quote(c, safe='')}"
            item["cover"] = proxied
            item["cover_image"] = proxied
            item["image"] = proxied

    return items


@router.get("/search")
async def search_manga_endpoint(
    q: Optional[str] = Query(None, description="Search keyword"),
    type: str = Query("all", description="all, manga, manhwa, manhua"),
    source: str = Query("all", description="all, vortex, toraka, mangadex, anilist"),
    page: int = Query(1, ge=1)
):
    """Search Manga, Manhwa, and Manhua across multiple sources with AniList posters."""
    type_norm = type.lower()
    country_map = {"manhwa": "KR", "manhua": "CN", "manga": "JP"}
    target_country = country_map.get(type_norm)

    if source == "all":
        tasks = [
            fetch_vortex_posts(page=page, query=q),
            fetch_toraka_series(page=page, query=q),
            search_mangadex(q or "leveling", limit=15),
            query_anilist_manga(search=q, country=target_country, page=page, per_page=15)
        ]
        res_list = await asyncio.gather(*tasks, return_exceptions=True)
        combined = []
        for r in res_list:
            if isinstance(r, list):
                combined.extend(r)
            elif isinstance(r, dict) and "results" in r:
                combined.extend(r["results"])
        if type_norm in ("manhwa", "manga", "manhua"):
            combined = [r for r in combined if type_norm in r.get("type", "").lower()]
        aggregated = aggregate_and_deduplicate_manga(combined)
        aggregated = await enrich_with_anilist_posters(aggregated)
        return {"source": "all", "results": aggregated}

    elif source == "vortex":
        results = await fetch_vortex_posts(page=page, query=q)
        if type_norm in ("manhwa", "manga", "manhua"):
            results = [r for r in results if r.get("type", "").lower() == type_norm]
        aggregated = aggregate_and_deduplicate_manga(results)
        aggregated = await enrich_with_anilist_posters(aggregated)
        return {"source": "vortex", "results": aggregated}

    elif source == "toraka":
        results = await fetch_toraka_series(page=page, query=q)
        aggregated = aggregate_and_deduplicate_manga(results)
        aggregated = await enrich_with_anilist_posters(aggregated)
        return {"source": "toraka", "results": aggregated}

    elif source == "mangadex":
        results = await search_mangadex(q or "leveling", limit=20)
        if type_norm in ("manhwa", "manga", "manhua"):
            results = [r for r in results if r.get("type", "").lower() == type_norm]
        aggregated = aggregate_and_deduplicate_manga(results)
        aggregated = await enrich_with_anilist_posters(aggregated)
        return {"source": "mangadex", "results": aggregated}

    elif source == "anilist":
        data = await query_anilist_manga(search=q, country=target_country, page=page, per_page=20)
        return {"source": "anilist", "results": data.get("results", []), "pageInfo": data.get("pageInfo", {})}

    else:
        results = await fetch_vortex_posts(page=page, query=q)
        aggregated = aggregate_and_deduplicate_manga(results)
        aggregated = await enrich_with_anilist_posters(aggregated)
        return {"source": "vortex", "results": aggregated}


@router.get("/popular")
async def popular_manga_endpoint(
    type: str = Query("all", description="all, manga, manhwa, manhua"),
    source: str = Query("all", description="all, vortex, toraka, anilist")
):
    """Get popular / trending titles unified across multiple sources with AniList posters."""
    country_map = {"manhwa": "KR", "manhua": "CN", "manga": "JP"}
    target_country = country_map.get(type.lower()) if type != "all" else None

    if source == "all":
        tasks = [
            fetch_vortex_posts(page=1),
            fetch_toraka_series(page=1, per_page=15),
            search_mangadex("leveling", limit=12),
            query_anilist_manga(search=None, country=target_country, page=1, per_page=20, sort="POPULARITY_DESC")
        ]
        res_list = await asyncio.gather(*tasks, return_exceptions=True)
        combined = []
        for r in res_list:
            if isinstance(r, list):
                combined.extend(r)
            elif isinstance(r, dict) and "results" in r:
                combined.extend(r["results"])
        aggregated = aggregate_and_deduplicate_manga(combined)
        aggregated = await enrich_with_anilist_posters(aggregated)
        return {"source": "all", "results": aggregated}
    elif source == "vortex":
        results = await fetch_vortex_posts(page=1)
        aggregated = aggregate_and_deduplicate_manga(results)
        aggregated = await enrich_with_anilist_posters(aggregated)
        return {"source": "vortex", "results": aggregated}
    elif source == "toraka":
        results = await fetch_toraka_series(page=1, per_page=15)
        aggregated = aggregate_and_deduplicate_manga(results)
        aggregated = await enrich_with_anilist_posters(aggregated)
        return {"source": "toraka", "results": aggregated}
    else:
        data = await query_anilist_manga(search=None, country=target_country, page=1, per_page=16)
        return {"source": "anilist", "results": data.get("results", [])}


@router.get("/info/{slug_or_id}")
async def manga_info_endpoint(
    slug_or_id: str,
    source: str = Query("vortex", description="vortex, toraka, mangadex, anilist")
):
    """Get manga details and chapter list enriched with AniList poster."""
    info = {}
    if source == "vortex":
        info = await fetch_vortex_chapters(slug_or_id)
    elif source == "toraka":
        info = await fetch_toraka_chapters(slug_or_id)
    elif source == "mangadex":
        info = await fetch_mangadex_chapters(slug_or_id)
    else:
        info = await fetch_vortex_chapters(slug_or_id)

    # Automatically fetch and attach official AniList poster
    title = info.get("title") or slug_or_id.replace("-", " ")
    anilist_cover = await get_or_fetch_anilist_poster(title)
    if anilist_cover:
        info["cover"] = anilist_cover
        info["anilist_poster"] = anilist_cover

    return info


@router.get("/chapter/{chapter_id}")
async def manga_chapter_pages_endpoint(
    chapter_id: str,
    source: str = Query("vortex", description="vortex, mangadex, toraka")
):
    """Fetch chapter pages/images for reading."""
    try:
        if source == "mangadex":
            return await fetch_mangadex_chapter_pages(chapter_id)
        elif source == "toraka":
            return {
                "chapter_id": chapter_id,
                "number": "0",
                "pages_count": 0,
                "pages": [],
                "source": "toraka",
                "message": "Toraka chapters are aggregated external references. Switch source to Vortex Scans or MangaDex above to read pages."
            }
        else:
            return await fetch_vortex_chapter_pages(chapter_id)
    except Exception as e:
        return {
            "chapter_id": chapter_id,
            "number": "0",
            "pages_count": 0,
            "pages": [],
            "source": source,
            "error": str(e)
        }


COVER_CACHE: Dict[str, bytes] = {}
COVER_MIME_CACHE: Dict[str, str] = {}

@router.get("/proxy_cover")
async def proxy_cover(url: str):
    """Proxy manga covers to prevent anti-hotlinking blocking by upstream CDNs (e.g. MangaDex)."""
    raw_url = unquote(url).strip()
    if not raw_url:
        raise HTTPException(status_code=400, detail="Missing cover URL")

    # In-memory fast cache
    if raw_url in COVER_CACHE:
        return Response(
            content=COVER_CACHE[raw_url],
            media_type=COVER_MIME_CACHE.get(raw_url, "image/jpeg"),
            headers={"Cache-Control": "public, max-age=604800, immutable"}
        )

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Accept": "image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8",
    }
    if "mangadex.org" in raw_url:
        headers["Referer"] = "https://mangadex.org/"
    elif "toraka.com" in raw_url:
        headers["Referer"] = "https://toraka.com/"

    try:
        async with httpx.AsyncClient(timeout=20.0, follow_redirects=True, verify=False) as client:
            res = await client.get(raw_url, headers=headers)
            if res.status_code == 200 and len(res.content) > 0:
                content_type = res.headers.get("content-type", "image/jpeg")
                if len(COVER_CACHE) < 500:
                    COVER_CACHE[raw_url] = res.content
                    COVER_MIME_CACHE[raw_url] = content_type
                return Response(
                    content=res.content,
                    media_type=content_type,
                    headers={"Cache-Control": "public, max-age=604800, immutable"}
                )
    except Exception:
        pass

    raise HTTPException(status_code=404, detail="Cover unavailable")


@router.get("/cover_fallback")
async def cover_fallback(title: str = Query("Manga")):
    """Dynamically fetch official AniList poster or return a premium styled anime cover card."""
    cover = await get_or_fetch_anilist_poster(title)
    if cover and cover.startswith("http") and "mangadex.org" not in cover:
        try:
            async with httpx.AsyncClient(timeout=10.0, follow_redirects=True, verify=False) as client:
                res = await client.get(cover)
                if res.status_code == 200:
                    return Response(
                        content=res.content,
                        media_type=res.headers.get("content-type", "image/jpeg"),
                        headers={"Cache-Control": "public, max-age=604800"}
                    )
        except Exception:
            pass

    safe_title = title.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")[:28]
    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="300" height="420" viewBox="0 0 300 420">
      <defs>
        <linearGradient id="bg" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0%" stop-color="#0f172a"/>
          <stop offset="100%" stop-color="#1e1b4b"/>
        </linearGradient>
      </defs>
      <rect width="300" height="420" fill="url(#bg)"/>
      <rect x="12" y="12" width="276" height="396" rx="10" fill="none" stroke="#4338ca" stroke-width="1.5" stroke-dasharray="6 4" opacity="0.6"/>
      <circle cx="150" cy="180" r="38" fill="#312e81" opacity="0.7"/>
      <path d="M142 165 L165 180 L142 195 Z" fill="#818cf8"/>
      <text x="150" y="248" fill="#e2e8f0" font-family="-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif" font-size="15" font-weight="700" text-anchor="middle">{safe_title}</text>
      <text x="150" y="272" fill="#818cf8" font-family="-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif" font-size="11" font-weight="600" text-anchor="middle">MANGA &amp; MANHWA</text>
    </svg>"""
    return Response(content=svg, media_type="image/svg+xml", headers={"Cache-Control": "public, max-age=604800"})


