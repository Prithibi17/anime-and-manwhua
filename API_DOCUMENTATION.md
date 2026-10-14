# Kuhi Anime & Manga Studio API Documentation
**Version:** 3.6  
**Base URL:** `http://localhost:5646` (or `https://anime-and-manwhua.vercel.app`)

Welcome to the **Kuhi Anime & Manga Studio API**. This API provides unified media data, exact release tracking (how many chapters or episodes have been released so far), countdown to next airing episodes, direct built-in anime video streaming player embeds, complete chapter lists, official AniList HD posters & banners, and full panel images for manga chapters with CORS-safe proxy delivery.

---

## Table of Contents
1. [Authentication & API Keys](#1-authentication--api-keys)
2. [API Key Management](#2-api-key-management)
3. [Release Tracking & Content API (New)](#3-release-tracking--content-api)
   - [Unified Release Tracker (Anime & Manga)](#unified-release-tracker)
   - [Anime Release Status & Episode Count](#anime-release-status--episode-count)
   - [Manga Release Status, Chapter Count & Panel Images](#manga-release-status-chapter-count--panel-images)
4. [Anime Video & Built-in Player API](#4-anime-video--built-in-player-api)
   - [Get Built-in Player & Embed Code](#get-built-in-player--embed-code)
   - [Direct Video Stream URLs](#direct-video-stream-urls)
   - [Get Anime Episodes](#get-anime-episodes)
   - [Search Anime](#search-anime)
   - [Popular Anime](#popular-anime)
   - [Standalone Video Player URL](#standalone-video-player-url)
5. [Manga, Manhwa & Manhua API](#5-manga-manhwa--manhua-api)
   - [Search Manga / Manhwa / Manhua](#search-manga--manhwa--manhua)
   - [Popular / Trending Manga](#popular--trending-manga)
   - [Manga Details & Chapters](#manga-details--chapters)
   - [Chapter Pages & Reader Links](#chapter-pages--reader-links)
   - [Standalone Manga Reader URL](#standalone-manga-reader-url)
6. [Code Examples](#6-code-examples)
   - [cURL](#curl)
   - [JavaScript / Fetch](#javascript--fetch)
   - [Python (requests / httpx)](#python-requests--httpx)
   - [HTML iFrame Embed](#html-iframe-embed)

---

## 1. Authentication & API Keys

All `/api/anime/*`, `/api/manga/*`, and `/api/releases` endpoints require a valid API key. You can authenticate using any of the three methods:

### Method A: Query Parameter (Simplest)
Append `?key=YOUR_API_KEY` (or `?api_key=YOUR_API_KEY`) to any URL:
```bash
https://anime-and-manwhua.vercel.app/api/releases?type=anime&id=21&key=YOUR_API_KEY
```

### Method B: HTTP Header `X-API-Key`
Pass the header in your HTTP request:
```http
X-API-Key: YOUR_API_KEY
```

### Method C: Authorization Bearer
```http
Authorization: Bearer YOUR_API_KEY
```

> **Default Demo Key:**  
> A pre-seeded development key is available for immediate testing:  
> `kuhi_live_27f453e42c851403fac890ac7d1cc803`

---

## 2. API Key Management

### List All Registered API Keys
```http
GET /api/keys
```
**Response:**
```json
{
  "keys": [
    {
      "id": "key_default_demo",
      "name": "Default Integration Key",
      "key": "kuhi_live_27f453e42c851403fac890ac7d1cc803",
      "created_at": "2026-10-14 13:09:58",
      "calls": 142,
      "last_used": "2026-10-15 00:55:19",
      "status": "active"
    }
  ]
}
```

### Create a New API Key
```http
POST /api/keys
Content-Type: application/json

{
  "name": "My Mobile App Key"
}
```

### Revoke / Delete an API Key
```http
DELETE /api/keys/{key_id_or_key}
```

---

## 3. Release Tracking & Content API

Use these endpoints when you need to know **how many episodes or chapters have been released**, when the next episode airs, official HD posters and banners, and **proper panel images** for reading manga chapters.

### Unified Release Tracker
Query release information for either Anime or Manga using one single endpoint.

```http
GET /api/releases?type={anime|manga}&id={id_or_slug}&key={YOUR_KEY}
```

**Query Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `type` | string | Yes | `anime` or `manga` (also accepts `manhwa`, `manhua`) |
| `id` | string | Yes | AniList Anime ID (e.g. `21`) or Manga slug/ID (e.g. `the-rebel-of-the-apocalypse-academy`) |
| `source` | string | No | For manga: `vortex` (default), `mangadex`, or `auto` |
| `include_pages` | boolean | No | For manga: whether to include full chapter panel images (default `false`) |
| `chapter` | string | No | For manga: target chapter (`latest`, `first`, `unlocked`, or number like `1`) |
| `sub_or_dub` | string | No | For anime: `sub` (default) or `dub` |
| `limit` | int | No | For manga: max chapters to return (default `250`, max `500`) |

---

### Anime Release Status & Episode Count
Returns the exact count of episodes released/aired so far, total planned episodes, next episode airing countdown, official AniList HD posters, and complete episode list with direct player URLs and iframe embed codes.

```http
GET /api/anime/releases/{anime_id}?type={sub|dub}&key={YOUR_KEY}
```

**Response Example (One Piece, ID 21):**
```json
{
  "id": 21,
  "mal_id": 21,
  "title": "ONE PIECE",
  "title_english": "One Piece",
  "title_romaji": "ONE PIECE",
  "title_native": "ONE PIECE",
  "format": "TV",
  "status": "RELEASING",
  "is_airing": true,
  "released_episodes_count": 1180,
  "total_expected_episodes": null,
  "latest_released_episode": {
    "number": 1180,
    "title": "Episode 1180",
    "thumbnail": "https://s4.anilist.co/file/anilistcdn/media/anime/cover/large/bx21-ELSYx3yMPcKM.jpg",
    "player_url": "http://localhost:5646/player?id=21&episode=1180&key=YOUR_KEY",
    "iframe_embed": "<iframe src=\"http://localhost:5646/player?id=21&episode=1180&key=YOUR_KEY\" width=\"100%\" height=\"100%\" frameborder=\"0\" allowfullscreen allow=\"autoplay; fullscreen; picture-in-picture\"></iframe>",
    "stream_api": "http://localhost:5646/api/anime/stream?id=21&episode=1180&type=sub&key=YOUR_KEY"
  },
  "first_released_episode": {
    "number": 1,
    "title": "Episode 1",
    "thumbnail": "https://s4.anilist.co/file/anilistcdn/media/anime/cover/large/bx21-ELSYx3yMPcKM.jpg",
    "player_url": "http://localhost:5646/player?id=21&episode=1&key=YOUR_KEY",
    "iframe_embed": "<iframe src=\"http://localhost:5646/player?id=21&episode=1&key=YOUR_KEY\" width=\"100%\" height=\"100%\" frameborder=\"0\" allowfullscreen allow=\"autoplay; fullscreen; picture-in-picture\"></iframe>",
    "stream_api": "http://localhost:5646/api/anime/stream?id=21&episode=1&type=sub&key=YOUR_KEY"
  },
  "next_airing": {
    "episode": 1181,
    "airing_at_timestamp": 1798985760,
    "time_until_airing_seconds": 6979800,
    "countdown": "80d 18h 50m"
  },
  "poster": "https://s4.anilist.co/file/anilistcdn/media/anime/cover/large/bx21-ELSYx3yMPcKM.jpg",
  "banner": "https://s4.anilist.co/file/anilistcdn/media/anime/banner/21-wf37VakJmZqd.jpg",
  "score": 88,
  "genres": ["Action", "Adventure", "Comedy", "Drama", "Fantasy"],
  "synopsis": "Gold Roger was known as the 'Pirate King'...",
  "episodes": [
    {
      "number": 1,
      "title": "Episode 1",
      "thumbnail": "https://...",
      "player_url": "http://localhost:5646/player?id=21&episode=1&key=YOUR_KEY",
      "iframe_embed": "<iframe src=\"...\" ...></iframe>",
      "stream_api": "http://localhost:5646/api/anime/stream?id=21&episode=1&type=sub&key=YOUR_KEY"
    }
  ]
}
```

---

### Manga Release Status, Chapter Count & Panel Images
Returns exact chapter release count, latest released chapter, highest unlocked/free chapter, official AniList HD cover, and full panel images for immediate reader rendering.

```http
GET /api/manga/releases/{slug_or_id}?include_pages=true&key={YOUR_KEY}
```

**Query Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `slug_or_id` | string (path) | Yes | Series slug (e.g. `the-rebel-of-the-apocalypse-academy`) or MangaDex UUID |
| `source` | string | No | `vortex` (default), `mangadex`, or `auto` |
| `include_pages` | boolean | No | Set to `true` to return full panel images for target chapter (default `false`) |
| `chapter` | string | No | Chapter target: `latest` (default), `unlocked`, `first`, or chapter number e.g. `15` |
| `limit` | int | No | Max chapters in list (default `250`, max `500`) |

**Response Example:**
```json
{
  "id": "695",
  "title": "The Rebel of the Apocalypse Academy",
  "slug": "the-rebel-of-the-apocalypse-academy",
  "type": "MANHWA",
  "source": "vortex",
  "status": "RELEASING",
  "released_chapters_count": 16,
  "poster": "https://s4.anilist.co/file/anilistcdn/media/manga/cover/medium/b167759-Uqb92EWWE3pp.jpg",
  "banner": null,
  "synopsis": "In a world overwhelmed by an apocalyptic disaster...",
  "genres": ["Action", "Fantasy", "School"],
  "score": 82,
  "latest_released_chapter": {
    "id": "34023",
    "number": "20",
    "title": "Chapter 20",
    "is_locked": true,
    "release_date": "2026-10-14T20:10:00.000Z",
    "reader_url": "http://localhost:5646/manga/reader/34023?source=vortex&key=YOUR_KEY",
    "chapter_api": "http://localhost:5646/api/manga/chapter/34023?source=vortex&key=YOUR_KEY"
  },
  "latest_unlocked_chapter": {
    "id": "34018",
    "number": "15",
    "title": "Chapter 15",
    "is_locked": false,
    "release_date": "2026-10-14T19:00:00.000Z",
    "reader_url": "http://localhost:5646/manga/reader/34018?source=vortex&key=YOUR_KEY",
    "chapter_api": "http://localhost:5646/api/manga/chapter/34018?source=vortex&key=YOUR_KEY"
  },
  "first_released_chapter": {
    "id": "34010",
    "number": "1",
    "title": "Chapter 1",
    "is_locked": false,
    "release_date": "2026-10-14T18:46:17.100Z",
    "reader_url": "http://localhost:5646/manga/reader/34010?source=vortex&key=YOUR_KEY",
    "chapter_api": "http://localhost:5646/api/manga/chapter/34010?source=vortex&key=YOUR_KEY"
  },
  "chapter_panels": {
    "chapter_id": "34018",
    "number": "15",
    "title": "Chapter 15",
    "is_locked": false,
    "pages_count": 32,
    "reader_url": "http://localhost:5646/manga/reader/34018?source=vortex&key=YOUR_KEY",
    "iframe_embed": "<iframe src=\"http://localhost:5646/manga/reader/34018?source=vortex&key=YOUR_KEY\" width=\"100%\" height=\"800\" frameborder=\"0\" allowfullscreen></iframe>",
    "pages": [
      {
        "page": 1,
        "url": "http://localhost:5646/proxy_image?url=https%3A%2F%2Fstorage.vortexscans.org%2Fupload%2F...webp&referer=https%3A%2F%2Fvortexscans.org%2F",
        "raw_url": "https://storage.vortexscans.org/upload/...webp"
      }
    ]
  },
  "chapters": [
    {
      "id": "34023",
      "number": "20",
      "title": "Chapter 20",
      "is_locked": true,
      "release_date": "2026-10-14T20:10:00.000Z",
      "reader_url": "http://localhost:5646/manga/reader/34023?source=vortex&key=YOUR_KEY",
      "chapter_api": "http://localhost:5646/api/manga/chapter/34023?source=vortex&key=YOUR_KEY"
    }
  ]
}
```

---

## 4. Anime Video & Built-in Player API

### Get Built-in Player & Embed Code
Returns the complete standalone player URL and ready-to-use `<iframe>` embed code.

```http
GET /api/anime/player?id={anime_id}&episode={episode}&type={sub|dub}&key={YOUR_KEY}
```

**Query Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `id` | int | Yes | AniList Anime ID (e.g., `21` for One Piece, `16498` for Attack on Titan) |
| `episode` | int | No | Episode number (default: `1`) |
| `type` | string | No | `sub` (default) or `dub` |
| `server` | string | No | Preferred server e.g., `DatSaV` (MP4) or `Vidplay` (HLS) |
| `key` | string | Yes | Your API key |

**Response Example:**
```json
{
  "status": "success",
  "anime_id": 21,
  "episode": 1,
  "audio": "sub",
  "player_url": "http://localhost:5646/player?id=21&episode=1&type=sub&key=YOUR_KEY",
  "iframe_embed": "<iframe src=\"http://localhost:5646/player?id=21&episode=1&type=sub&key=YOUR_KEY\" width=\"100%\" height=\"100%\" frameborder=\"0\" allow=\"autoplay; fullscreen; picture-in-picture; encrypted-media\" allowfullscreen></iframe>",
  "features": {
    "skip_buttons": "Rewind 10s & Forward 10s between play and volume",
    "volume_slider": "Horizontal hover-expand slider with drop shadow",
    "aniskip_button": "Floating button at bottom: 85px (above timeline)",
    "timeline_markers": "Yellow highlighted intro and outro intervals",
    "hotkeys": "Space (Play/Pause), Left/Right (Seek 5s), Up/Down (Volume), F (Fullscreen)"
  },
  "skip_times": {
    "found": true,
    "intro": { "start": 92.5, "end": 182.0 },
    "outro": { "start": 1340.0, "end": 1420.0 }
  }
}
```

---

### Direct Video Stream URLs
Returns direct stream URLs pre-configured with CORS & anti-hotlinking proxy endpoints (`/proxy_m3u8` and `/proxy_mp4`), subtitles (`/proxy_sub`), and AniSkip timestamps.

```http
GET /api/anime/stream?id={anime_id}&episode={episode}&type={sub|dub}&key={YOUR_KEY}
```

**Response Example:**
```json
{
  "anime_id": 21,
  "episode": 1,
  "audio": "sub",
  "player_url": "http://localhost:5646/player?id=21&episode=1&type=sub&key=YOUR_KEY",
  "skip_times": {
    "found": true,
    "intro": { "start": 92.5, "end": 182.0 },
    "outro": null
  },
  "streams": [
    {
      "server": "DatSaV",
      "type": "mp4",
      "quality": "auto",
      "stream_url": "http://localhost:5646/proxy_mp4?url=...&referer=...",
      "raw_url": "https://..."
    },
    {
      "server": "Vidplay",
      "type": "hls",
      "quality": "1080p",
      "stream_url": "http://localhost:5646/proxy_m3u8?url=...&referer=...",
      "raw_url": "https://..."
    }
  ],
  "subtitles": [
    {
      "language": "English",
      "url": "http://localhost:5646/proxy_sub?url=...",
      "format": "vtt"
    }
  ]
}
```

---

### Get Anime Episodes
Returns the full episode list for an anime, including direct built-in player URLs and thumbnail images.

```http
GET /api/anime/episodes/{anime_id}?key={YOUR_KEY}
```

---

### Search Anime
Search for titles across the AniList catalog.

```http
GET /api/anime/search?q={keyword}&page=1&per_page=20&key={YOUR_KEY}
```

---

### Popular Anime
Retrieve currently trending and top-rated anime titles.

```http
GET /api/anime/popular?page=1&per_page=20&key={YOUR_KEY}
```

---

### Standalone Video Player URL
If you want to view the built-in video player directly in your browser or an iframe:
```http
http://localhost:5646/player?id={anime_id}&episode={episode}&key={YOUR_KEY}
```

---

## 5. Manga, Manhwa & Manhua API

### Search Manga / Manhwa / Manhua
Search across Vortex Scans, Toraka, MangaDex, and AniList with deduplication and official AniList poster enrichment.

```http
GET /api/manga/search?q={query}&type={all|manhwa|manga|manhua}&source={all|vortex|mangadex}&page=1&key={YOUR_KEY}
```

---

### Popular / Trending Manga
Retrieve popular and trending manga and webtoon titles.

```http
GET /api/manga/popular?type=all&page=1&per_page=20&key={YOUR_KEY}
```

---

### Manga Details & Chapters
Fetch metadata, synopsis, status, and chapter list for a title.

```http
GET /api/manga/info/{slug_or_id}?source={vortex|mangadex}&key={YOUR_KEY}
```

---

### Chapter Pages & Reader Links
Retrieves all page image URLs for reading a chapter. Every image URL is pre-wrapped with `/proxy_image` so images load without CORS or Referer restrictions.

```http
GET /api/manga/chapter/{chapter_id}?source={vortex|mangadex}&key={YOUR_KEY}
```

---

### Standalone Manga Reader URL
To see chapter images properly in any browser or webview, simply navigate to or embed:
```http
http://localhost:5646/manga/reader/{chapter_id}?source={vortex|mangadex}&key={YOUR_KEY}
```

#### Reader Features:
- **Continuous Vertical Strip:** Native Webtoon/Manhwa reading experience.
- **Clean Dark Theme:** Designed for comfortable long-session reading.
- **Navigation Controls:** Next Chapter & Previous Chapter buttons with keyboard shortcuts (`Left` / `Right` arrows).
- **Responsive Sizing:** Width toggles (Compact, Standard, Full Width) and Fullscreen mode (`F`).
- **Auto Page Counter:** Floating pill tracking current page (`Page X / Y`).
- **CORS-Free Delivery:** All page images are streamed through the built-in image proxy.

---

## 6. Code Examples

### cURL

```bash
# 1. Check Anime Releases (One Piece)
curl -X GET "http://localhost:5646/api/anime/releases/21?key=YOUR_API_KEY"

# 2. Check Manga Releases with Panel Images
curl -X GET "http://localhost:5646/api/manga/releases/the-rebel-of-the-apocalypse-academy?include_pages=true&key=YOUR_API_KEY"

# 3. Unified Release Tracking Hub
curl -X GET "http://localhost:5646/api/releases?type=anime&id=21&key=YOUR_API_KEY"

# 4. Get Anime Player Embed
curl -X GET "http://localhost:5646/api/anime/player?id=21&episode=1&key=YOUR_API_KEY"

# 5. Get Chapter Pages
curl -X GET "http://localhost:5646/api/manga/chapter/34018?source=vortex&key=YOUR_API_KEY"
```

---

### JavaScript / Fetch

```javascript
const API_BASE = "https://anime-and-manwhua.vercel.app";
const API_KEY = "YOUR_API_KEY";

// 1. Check how many episodes have released and get next airing countdown
async function checkAnimeRelease(animeId) {
  const res = await fetch(`${API_BASE}/api/anime/releases/${animeId}?key=${API_KEY}`);
  const data = await res.json();
  console.log(`Title: ${data.title}`);
  console.log(`Episodes Released: ${data.released_episodes_count}`);
  if (data.next_airing) {
    console.log(`Episode ${data.next_airing.episode} airs in: ${data.next_airing.countdown}`);
  }
  return data;
}

// 2. Check how many chapters have released and get panel preview images
async function checkMangaRelease(mangaSlug) {
  const res = await fetch(`${API_BASE}/api/manga/releases/${mangaSlug}?include_pages=true&key=${API_KEY}`);
  const data = await res.json();
  console.log(`Title: ${data.title}`);
  console.log(`Chapters Released: ${data.released_chapters_count}`);
  console.log(`Latest Chapter: ${data.latest_released_chapter.number}`);
  console.log(`Panels count: ${data.chapter_panels?.pages_count}`);
  return data;
}

// 3. Embed anime player inside a container
async function embedPlayer(animeId, episode, container) {
  const res = await fetch(`${API_BASE}/api/anime/player?id=${animeId}&episode=${episode}&key=${API_KEY}`);
  const data = await res.json();
  container.innerHTML = data.iframe_embed;
}
```

---

### Python (httpx / requests)

```python
import httpx

API_BASE = "https://anime-and-manwhua.vercel.app"
API_KEY = "YOUR_API_KEY"

headers = {"X-API-Key": API_KEY}

# 1. Track Anime Release
res_anime = httpx.get(f"{API_BASE}/api/anime/releases/21", headers=headers)
anime = res_anime.json()
print(f"Anime: {anime['title']} | Released: {anime['released_episodes_count']} eps")

# 2. Track Manga Release with panels
res_manga = httpx.get(
    f"{API_BASE}/api/manga/releases/the-rebel-of-the-apocalypse-academy",
    params={"include_pages": "true"},
    headers=headers
)
manga = res_manga.json()
print(f"Manga: {manga['title']} | Released: {manga['released_chapters_count']} chs")
if manga.get("chapter_panels"):
    print(f"Panel 1 URL: {manga['chapter_panels']['pages'][0]['url']}")
```

---

### HTML iFrame Embed

```html
<!-- Embed the built-in anime player -->
<iframe 
  src="https://anime-and-manwhua.vercel.app/player?id=21&episode=1&key=YOUR_API_KEY" 
  width="100%" 
  height="600" 
  frameborder="0" 
  allow="autoplay; fullscreen; picture-in-picture" 
  allowfullscreen>
</iframe>

<!-- Embed the continuous manga webtoon reader -->
<iframe 
  src="https://anime-and-manwhua.vercel.app/manga/reader/34018?source=vortex&key=YOUR_API_KEY" 
  width="100%" 
  height="800" 
  frameborder="0" 
  allowfullscreen>
</iframe>
```
