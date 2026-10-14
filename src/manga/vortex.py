import httpx
from typing import Optional, List, Dict, Any

VORTEX_API = "https://api.vortexscans.org/api"
TORAKA_API = "https://core.toraka.com/api/v1"
MANGADEX_API = "https://api.mangadex.org"
ANILIST_API = "https://graphql.anilist.co"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
}


async def fetch_vortex_posts(page: int = 1, query: Optional[str] = None) -> List[Dict[str, Any]]:
    """Fetch series list or search from Vortex Scans."""
    url = f"{VORTEX_API}/posts?page={page}"
    if query:
        url += f"&query={query}"
    async with httpx.AsyncClient(timeout=10.0, follow_redirects=True, verify=False) as client:
        res = await client.get(url, headers=HEADERS)
        if res.status_code != 200:
            return []
        data = res.json()
        posts = data.get("posts", [])
        results = []
        for p in posts:
            results.append({
                "id": str(p.get("id")),
                "slug": p.get("slug") or str(p.get("id")),
                "title": p.get("postTitle") or p.get("title") or "Unknown Title",
                "alt_titles": p.get("alternativeTitles") or "",
                "type": (p.get("seriesType") or "MANHWA").upper(),
                "cover": p.get("featuredImage") or p.get("featuredImageCL") or "",
                "status": p.get("seriesStatus") or "Ongoing",
                "chapters_count": len(p.get("chapters", [])),
                "source": "vortex",
                "source_label": "Vortex Scans"
            })
        return results


async def fetch_vortex_chapters(slug_or_id: str) -> Dict[str, Any]:
    """Fetch series details and full chapter catalog from Vortex Scans."""
    target = None

    async with httpx.AsyncClient(timeout=12.0, follow_redirects=True, verify=False) as client:
        # Search by slug/query first for exact match
        url_search = f"{VORTEX_API}/posts?query={slug_or_id}"
        res = await client.get(url_search, headers=HEADERS)
        if res.status_code == 200:
            posts = res.json().get("posts", [])
            for p in posts:
                if str(p.get("id")) == str(slug_or_id) or p.get("slug") == slug_or_id:
                    target = p
                    break
            if not target and posts:
                target = posts[0]

        # Fallback to page 1 list if still not found
        if not target:
            res = await client.get(f"{VORTEX_API}/posts?page=1", headers=HEADERS)
            if res.status_code == 200:
                posts = res.json().get("posts", [])
                for p in posts:
                    if str(p.get("id")) == str(slug_or_id) or p.get("slug") == slug_or_id:
                        target = p
                        break

        chapters = []
        if target:
            post_id = target.get("id")
            # Fetch all chapters for this post
            res_ch = await client.get(f"{VORTEX_API}/chapters?postId={post_id}&take=250", headers=HEADERS)
            if res_ch.status_code == 200:
                ch_data = res_ch.json()
                post_obj = ch_data.get("post") or {}
                raw_chs = post_obj.get("chapters") or target.get("chapters", [])
                for ch in raw_chs:
                    chapters.append({
                        "id": str(ch.get("id")),
                        "number": str(ch.get("number") or "0"),
                        "title": ch.get("title") or f"Chapter {ch.get('number')}",
                        "is_locked": bool(ch.get("isLocked") or ch.get("isLockedByCoins") or ch.get("isPermanentlyLocked") or ch.get("isAccessible") is False),
                        "created_at": ch.get("createdAt") or ""
                    })

    return {
        "id": str(target.get("id")) if target else slug_or_id,
        "title": target.get("postTitle") or "Manhwa",
        "slug": target.get("slug") if target else slug_or_id,
        "type": (target.get("seriesType") or "MANHWA").upper() if target else "MANHWA",
        "cover": target.get("featuredImage") if target else "",
        "chapters": chapters,
        "source": "vortex"
    }


async def fetch_vortex_chapter_pages(chapter_id: str) -> Dict[str, Any]:
    """Fetch chapter pages/images from Vortex Scans."""
    url = f"{VORTEX_API}/chapter?chapterId={chapter_id}"
    async with httpx.AsyncClient(timeout=15.0, follow_redirects=True, verify=False) as client:
        res = await client.get(url, headers=HEADERS)
        if res.status_code != 200:
            raise RuntimeError(f"Vortex chapter HTTP {res.status_code}")
        data = res.json()
        ch = data.get("chapter", {})
        raw_images = ch.get("images", [])
        raw_images.sort(key=lambda x: x.get("order", 0))
        images = [img.get("url") for img in raw_images if img.get("url")]

        return {
            "chapter_id": chapter_id,
            "number": ch.get("number"),
            "title": ch.get("title") or f"Chapter {ch.get('number')}",
            "pages_count": len(images),
            "pages": images,
            "next_chapter": (data.get("nextChapter") or {}).get("id"),
            "prev_chapter": (data.get("previousChapter") or {}).get("id"),
            "source": "vortex",
            "referer": "https://vortexscans.org/"
        }
