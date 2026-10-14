import httpx
from typing import Optional, List, Dict, Any

ANILIST_URL = "https://graphql.anilist.co"


async def query_anilist_manga(
    search: Optional[str] = None,
    country: Optional[str] = None,
    page: int = 1,
    per_page: int = 20,
    sort: str = "POPULARITY_DESC"
) -> Dict[str, Any]:
    """Search or list Manga, Manhwa, and Manhua via AniList GraphQL."""
    query = """
    query ($search: String, $country: CountryCode, $page: Int, $perPage: Int, $sort: [MediaSort]) {
      Page(page: $page, perPage: $perPage) {
        pageInfo {
          total
          currentPage
          lastPage
          hasNextPage
          perPage
        }
        media(search: $search, type: MANGA, countryOfOrigin: $country, sort: $sort) {
          id
          title {
            romaji
            english
            native
          }
          countryOfOrigin
          format
          status
          chapters
          volumes
          coverImage {
            large
            extraLarge
          }
          bannerImage
          description
          averageScore
          genres
          startDate {
            year
          }
        }
      }
    }
    """
    variables: Dict[str, Any] = {
        "page": page,
        "perPage": per_page,
        "sort": [sort]
    }
    if search:
        variables["search"] = search
    if country:
        variables["country"] = country

    async with httpx.AsyncClient(timeout=12.0, follow_redirects=True, verify=False) as client:
        res = await client.post(
            ANILIST_URL,
            json={"query": query, "variables": variables},
            headers={"Content-Type": "application/json", "Accept": "application/json"}
        )
        if res.status_code != 200:
            return {"results": [], "pageInfo": {}}
        
        data = res.json().get("data", {}).get("Page", {})
        results = []
        for m in data.get("media", []):
            country_code = m.get("countryOfOrigin") or "JP"
            type_label = "MANGA"
            if country_code == "KR":
                type_label = "MANHWA"
            elif country_code == "CN":
                type_label = "MANHUA"

            title_eng = (m.get("title") or {}).get("english")
            title_rom = (m.get("title") or {}).get("romaji")
            title_nat = (m.get("title") or {}).get("native")

            results.append({
                "id": m.get("id"),
                "title": title_eng or title_rom or "Unknown",
                "title_romaji": title_rom,
                "title_native": title_nat,
                "type": type_label,
                "country": country_code,
                "status": m.get("status"),
                "chapters": m.get("chapters"),
                "volumes": m.get("volumes"),
                "cover": (m.get("coverImage") or {}).get("extraLarge") or (m.get("coverImage") or {}).get("large"),
                "banner": m.get("bannerImage"),
                "synopsis": m.get("description") or "",
                "score": m.get("averageScore"),
                "genres": m.get("genres") or [],
                "year": (m.get("startDate") or {}).get("year"),
                "source": "anilist",
                "source_label": "AniList Catalog"
            })

        return {
            "results": results,
            "pageInfo": data.get("pageInfo", {})
        }
