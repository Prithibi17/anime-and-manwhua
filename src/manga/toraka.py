import httpx
from typing import Optional, List, Dict, Any

TORAKA_API = "https://core.toraka.com/api/v1"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
}


async def fetch_toraka_series(page: int = 1, query: Optional[str] = None, per_page: int = 20) -> List[Dict[str, Any]]:
    """Fetch series list or search from Toraka API (ShineiAPI upstream)."""
    if query:
        url = f"{TORAKA_API}/search?q={query}&per_page={per_page}&page={page}"
    else:
        url = f"{TORAKA_API}/series?per_page={per_page}&page={page}"
    
    async with httpx.AsyncClient(timeout=12.0, follow_redirects=True, verify=False) as client:
        res = await client.get(url, headers=HEADERS)
        if res.status_code != 200:
            return []
        data = res.json()
        series_list = data.get("data", [])
        results = []
        for s in series_list:
            cov = s.get("cover")
            cover_url = ""
            if isinstance(cov, dict):
                cover_url = cov.get("large") or cov.get("small") or cov.get("original") or cov.get("url") or ""
            elif isinstance(cov, str):
                cover_url = cov

            raw_title = s.get("title") or s.get("name") or s.get("slug", "").replace("-", " ").title() or "Untitled Manhwa"

            results.append({
                "id": s.get("slug") or s.get("uuid"),
                "slug": s.get("slug") or s.get("uuid"),
                "title": raw_title,
                "synopsis": s.get("synopsis") or s.get("description") or "",
                "rating": s.get("rating") or 0,
                "cover": cover_url,
                "chapters_count": s.get("chapters_count") or 0,
                "type": "MANHWA",
                "source": "toraka",
                "source_label": "Toraka (ShineiAPI)"
            })
        return results


async def fetch_toraka_chapters(slug: str) -> Dict[str, Any]:
    """Fetch chapters for a series from Toraka."""
    url = f"{TORAKA_API}/series/{slug}/chapters?per_page=150"
    async with httpx.AsyncClient(timeout=12.0, follow_redirects=True, verify=False) as client:
        res = await client.get(url, headers=HEADERS)
        if res.status_code != 200:
            return {"chapters": []}
        data = res.json()
        chapters_data = data.get("data", [])
        chapters = []
        for c in chapters_data:
            sources = c.get("sources", [])
            chapters.append({
                "id": c.get("uuid") or str(c.get("name")),
                "number": str(c.get("name") or "0"),
                "title": c.get("title") or f"Chapter {c.get('name')}",
                "released_at": c.get("released_at") or "",
                "is_locked": False,
                "sources": sources
            })
        
        # Sort chapters descending by number if numeric
        try:
            chapters.sort(key=lambda x: float(x["number"]) if x["number"].replace('.', '', 1).isdigit() else 0, reverse=True)
        except Exception:
            pass

        return {
            "slug": slug,
            "chapters": chapters,
            "source": "toraka"
        }
