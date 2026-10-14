import httpx
from typing import Optional, List, Dict, Any

MANGADEX_API = "https://api.mangadex.org"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "application/json",
}


async def search_mangadex(query: str, limit: int = 15) -> List[Dict[str, Any]]:
    """Search MangaDex by query."""
    url = f"{MANGADEX_API}/manga?title={query}&limit={limit}&includes[]=cover_art&contentRating[]=safe&contentRating[]=suggestive"
    async with httpx.AsyncClient(timeout=12.0, follow_redirects=True, verify=False) as client:
        res = await client.get(url, headers=HEADERS)
        if res.status_code != 200:
            return []
        data = res.json()
        results = []
        for item in data.get("data", []):
            attrs = item.get("attributes", {})
            title_dict = attrs.get("title", {})
            
            # 1. Best title resolution: English first, then English altTitles, then romanized/native
            title = title_dict.get("en")
            if not title:
                for alt in attrs.get("altTitles", []):
                    if isinstance(alt, dict) and alt.get("en"):
                        title = alt.get("en")
                        break
            if not title and title_dict:
                title = list(title_dict.values())[0]
            if not title:
                for alt in attrs.get("altTitles", []):
                    if isinstance(alt, dict) and alt:
                        title = list(alt.values())[0]
                        break
            if not title:
                title = "Unknown Manga"
            
            # 2. Cover image resolution: direct high-quality filename without broken .256 suffix
            cover_file = ""
            for rel in item.get("relationships", []):
                if rel.get("type") == "cover_art":
                    cover_file = (rel.get("attributes") or {}).get("fileName")
            cover_url = f"https://uploads.mangadex.org/covers/{item['id']}/{cover_file}" if cover_file else ""
            
            # 3. Determine Manga / Manhwa / Manhua
            orig_lang = attrs.get("originalLanguage") or "ja"
            type_label = "MANGA"
            if orig_lang == "ko":
                type_label = "MANHWA"
            elif orig_lang in ("zh", "zh-hk"):
                type_label = "MANHUA"

            results.append({
                "id": item["id"],
                "slug": item["id"],
                "title": title,
                "alt_titles": [list(t.values())[0] for t in attrs.get("altTitles", []) if t][:3],
                "synopsis": (attrs.get("description") or {}).get("en") or "",
                "type": type_label,
                "status": attrs.get("status") or "ongoing",
                "year": attrs.get("year"),
                "cover": cover_url,
                "source": "mangadex",
                "source_label": "MangaDex"
            })
        return results


async def fetch_mangadex_chapters(manga_id: str, limit: int = 100) -> Dict[str, Any]:
    """Fetch chapters for a manga from MangaDex."""
    url = f"{MANGADEX_API}/manga/{manga_id}/feed?translatedLanguage[]=en&limit={limit}&order[chapter]=asc&contentRating[]=safe&contentRating[]=suggestive"
    async with httpx.AsyncClient(timeout=12.0, follow_redirects=True, verify=False) as client:
        res = await client.get(url, headers=HEADERS)
        if res.status_code != 200:
            return {"chapters": []}
        data = res.json()
        chapters = []
        for item in data.get("data", []):
            attrs = item.get("attributes", {})
            ch_num = attrs.get("chapter") or "0"
            chapters.append({
                "id": item["id"],
                "number": ch_num,
                "title": attrs.get("title") or f"Chapter {ch_num}",
                "pages_count": attrs.get("pages") or 0,
                "is_locked": False,
                "external_url": attrs.get("externalUrl"),
                "created_at": attrs.get("publishAt") or ""
            })
        return {
            "manga_id": manga_id,
            "chapters": chapters,
            "source": "mangadex"
        }


async def fetch_mangadex_chapter_pages(chapter_id: str) -> Dict[str, Any]:
    """Fetch all page image URLs for a chapter from MangaDex."""
    url = f"{MANGADEX_API}/at-home/server/{chapter_id}"
    async with httpx.AsyncClient(timeout=15.0, follow_redirects=True, verify=False) as client:
        res = await client.get(url, headers=HEADERS)
        if res.status_code != 200:
            raise RuntimeError(f"MangaDex chapter HTTP {res.status_code}")
        data = res.json()
        base_url = data.get("baseUrl")
        chapter_info = data.get("chapter", {})
        ch_hash = chapter_info.get("hash")
        files = chapter_info.get("data", [])
        images = [f"{base_url}/data/{ch_hash}/{f}" for f in files]

        return {
            "chapter_id": chapter_id,
            "pages_count": len(images),
            "pages": images,
            "source": "mangadex",
            "referer": "https://mangadex.org/"
        }
