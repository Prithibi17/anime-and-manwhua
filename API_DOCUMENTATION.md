# Kuhi Anime & Manga Studio API Documentation
**Version:** 3.5  
**Base URL:** `http://localhost:5646` (or your deployed server domain)

Welcome to the **Kuhi Anime & Manga Studio API**. This API allows you to retrieve anime video streams with the website's built-in player (including horizontal hover volume slider, 10s skip buttons, AniSkip button at `bottom: 85px`, and yellow timeline markers), as well as complete manga, manhwa, and manhua information (official AniList high-resolution posters, synopses, chapters list, and chapter page images with a continuous web reader).

---

## Table of Contents
1. [Authentication & API Keys](#1-authentication--api-keys)
2. [API Key Management](#2-api-key-management)
3. [Anime Video & Built-in Player API](#3-anime-video--built-in-player-api)
   - [Get Built-in Player & Embed Code](#get-built-in-player--embed-code)
   - [Direct Video Stream URLs](#direct-video-stream-urls)
   - [Get Anime Episodes](#get-anime-episodes)
   - [Search Anime](#search-anime)
   - [Popular Anime](#popular-anime)
   - [Standalone Video Player URL](#standalone-video-player-url)
4. [Manga, Manhwa & Manhua API](#4-manga-manhwa--manhua-api)
   - [Search Manga / Manhwa / Manhua](#search-manga--manhwa--manhua)
   - [Popular / Trending Manga](#popular--trending-manga)
   - [Manga Details & Chapters](#manga-details--chapters)
   - [Chapter Pages & Reader Links](#chapter-pages--reader-links)
   - [Standalone Manga Reader URL](#standalone-manga-reader-url)
5. [Code Examples](#5-code-examples)
   - [cURL](#curl)
   - [JavaScript / Fetch](#javascript--fetch)
   - [Python (requests / httpx)](#python-requests--httpx)
   - [HTML iFrame Embed](#html-iframe-embed)

---

## 1. Authentication & API Keys

All `/api/anime/*` and `/api/manga/*` endpoints require a valid API key. You can authenticate using any of the three methods:

### Method A: Query Parameter (Simplest)
Append `?key=YOUR_API_KEY` (or `?api_key=YOUR_API_KEY`) to any URL:
```bash
http://localhost:5646/api/anime/player?id=21&episode=1&key=YOUR_API_KEY
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
> A pre-seeded development key is available in your workspace:  
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
      "calls": 12,
      "last_used": "2026-10-14 22:45:19",
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

## 3. Anime Video & Built-in Player API

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

**Response Example:**
```json
{
  "id": 21,
  "title": "One Piece",
  "format": "TV",
  "status": "RELEASING",
  "total_episodes": 1122,
  "poster": "https://s4.anilist.co/file/anilistcdn/media/anime/cover/large/bx21-YCDoj1EkASI2.jpg",
  "banner": "https://s4.anilist.co/file/anilistcdn/media/anime/banner/21-wf37VakJmZqs.jpg",
  "episodes": [
    {
      "number": 1,
      "title": "I'm Luffy! The Man Who Will Become the Pirate King!",
      "thumbnail": "https://...",
      "player_url": "http://localhost:5646/player?id=21&episode=1&key=YOUR_KEY",
      "iframe_embed": "<iframe src=\"http://localhost:5646/player?id=21&episode=1&key=YOUR_KEY\" width=\"100%\" height=\"100%\" frameborder=\"0\" allowfullscreen></iframe>"
    }
  ]
}
```

---

### Standalone Video Player URL
You can directly link or embed the player page in your web or mobile app:
```http
http://localhost:5646/player?id={anime_id}&episode={episode}&type={sub|dub}&key={YOUR_KEY}
```

#### Controls & Features Included:
- **Volume Slider:** Horizontal hover-expand slider with soft shadow (no dark square).
- **Skip Buttons:** 10s Rewind and 10s Forward buttons placed conveniently between the Play button and Volume button.
- **Floating Skip Intro / Outro:** AniSkip button appears at `bottom: 85px` (safely elevated above the timeline and controls).
- **Yellow Timeline Highlights:** Shows exact intro and outro segments on the seekbar.
- **Subtitles & Quality:** Built-in multi-subtitle support and quality/server switcher.
- **Direct Playback:** You can also pass an arbitrary video URL directly:  
  `http://localhost:5646/player?url={stream_url}&key={YOUR_KEY}`

---

## 4. Manga, Manhwa & Manhua API

### Search Manga / Manhwa / Manhua
Search across Vortex Scans, Toraka, MangaDex, and AniList with verified, high-resolution official posters.

```http
GET /api/manga/search?q={query}&type={all|manhwa|manga|manhua}&source={all|vortex|toraka|mangadex}&page={page}&key={YOUR_KEY}
```

**Query Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `q` | string | `None` | Search keyword (e.g. `Solo Leveling`, `Omniscient Reader`) |
| `type` | string | `all` | Filter by `all`, `manhwa`, `manga`, or `manhua` |
| `source` | string | `all` | Source filter: `all`, `vortex`, `toraka`, `mangadex`, `anilist` |
| `page` | int | `1` | Page number |
| `key` | string | **Required** | Your API key |

**Response Example:**
```json
{
  "page": 1,
  "type": "all",
  "source": "all",
  "total": 34,
  "results": [
    {
      "title": "Solo Leveling: Ragnarok",
      "slug": "solo-leveling-ragnarok",
      "source": "vortex",
      "type": "MANHWA",
      "poster": "https://s4.anilist.co/file/anilistcdn/media/manga/cover/large/bx178663-rR9k8jNq.jpg",
      "description": "The earth's existence is threatened once again...",
      "rating": 8.4,
      "genres": ["Action", "Fantasy"],
      "info_url": "http://localhost:5646/api/manga/info/solo-leveling-ragnarok?source=vortex&key=YOUR_KEY"
    }
  ]
}
```

---

### Popular / Trending Manga
```http
GET /api/manga/popular?type={all|manhwa|manga|manhua}&source={all|vortex|toraka|anilist}&key={YOUR_KEY}
```

---

### Manga Details & Chapters
Retrieves full synopsis, genres, official HD poster, and the complete chapter list with direct web reader links.

```http
GET /api/manga/info/{slug_or_id}?source={vortex|mangadex|toraka}&key={YOUR_KEY}
```

**Response Example:**
```json
{
  "title": "The Emperor's Sword",
  "slug": "the-emperors-sword",
  "source": "vortex",
  "poster": "https://s4.anilist.co/file/anilistcdn/media/manga/cover/large/bx175116-v0V2K.jpg",
  "description": "After losing his master and martial art school...",
  "status": "RELEASING",
  "type": "manhwa",
  "genres": ["Action", "Martial Arts", "Reincarnation"],
  "total_chapters": 90,
  "chapters": [
    {
      "id": "33926",
      "number": "1",
      "title": "Chapter 1",
      "is_locked": false,
      "release_date": "2024-08-20T14:00:00Z",
      "reader_url": "http://localhost:5646/manga/reader/33926?source=vortex&key=YOUR_KEY",
      "chapter_api": "http://localhost:5646/api/manga/chapter/33926?source=vortex&key=YOUR_KEY"
    }
  ]
}
```

---

### Chapter Pages & Reader Links
Retrieves all page image URLs for reading a chapter. Every image URL is pre-wrapped with `/proxy_image` so images load without CORS or Referer restrictions.

```http
GET /api/manga/chapter/{chapter_id}?source={vortex|mangadex}&key={YOUR_KEY}
```

**Response Example:**
```json
{
  "chapter_id": "33926",
  "number": 1,
  "title": "Chapter 1",
  "source": "vortex",
  "pages_count": 198,
  "next_chapter": "33927",
  "prev_chapter": null,
  "reader_url": "http://localhost:5646/manga/reader/33926?source=vortex&key=YOUR_KEY",
  "iframe_embed": "<iframe src=\"http://localhost:5646/manga/reader/33926?source=vortex&key=YOUR_KEY\" width=\"100%\" height=\"800\" frameborder=\"0\" allowfullscreen></iframe>",
  "pages": [
    {
      "page": 1,
      "url": "http://localhost:5646/proxy_image?url=https%3A%2F%2Fstorage.vortexscans.org%2Fupload%2Fseries%2F...webp&referer=https%3A%2F%2Fvortexscans.org%2F",
      "raw_url": "https://storage.vortexscans.org/upload/series/...webp"
    }
  ]
}
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

## 5. Code Examples

### cURL

```bash
# 1. Get Anime Player Embed
curl -X GET "http://localhost:5646/api/anime/player?id=21&episode=1&key=YOUR_API_KEY"

# 2. Search Manga
curl -X GET "http://localhost:5646/api/manga/search?q=Solo+Leveling&key=YOUR_API_KEY"

# 3. Get Chapter Pages
curl -X GET "http://localhost:5646/api/manga/chapter/33926?source=vortex&key=YOUR_API_KEY"
```

---

### JavaScript / Fetch

```javascript
const API_BASE = "http://localhost:5646";
const API_KEY = "YOUR_API_KEY";

// 1. Load built-in anime player inside your page
async function embedAnimePlayer(animeId, episodeNumber, containerElement) {
  const res = await fetch(`${API_BASE}/api/anime/player?id=${animeId}&episode=${episodeNumber}&key=${API_KEY}`);
  const data = await res.json();
  
  // Directly insert the iframe
  containerElement.innerHTML = data.iframe_embed;
}

// 2. Search Manhwa and display titles + HD posters
async function searchManhwa(query) {
  const res = await fetch(`${API_BASE}/api/manga/search?q=${encodeURIComponent(query)}&type=manhwa&key=${API_KEY}`);
  const data = await res.json();
  
  data.results.forEach(manga => {
    console.log(`${manga.title} - Poster: ${manga.poster}`);
    console.log(`Details: ${manga.info_url}`);
  });
}

// 3. Fetch Chapter Pages to display custom viewer
async function getChapterImages(chapterId) {
  const res = await fetch(`${API_BASE}/api/manga/chapter/${chapterId}?source=vortex&key=${API_KEY}`);
  const data = await res.json();
  
  data.pages.forEach(p => {
    const img = document.createElement("img");
    img.src = p.url; // Safe proxied URL
    document.body.appendChild(img);
  });
}
```

---

### Python (requests / httpx)

```python
import requests

API_BASE = "http://localhost:5646"
API_KEY = "YOUR_API_KEY"
headers = {"X-API-Key": API_KEY}

# 1. Get Anime Player Info
resp = requests.get(f"{API_BASE}/api/anime/player", params={"id": 21, "episode": 1}, headers=headers)
player_data = resp.json()
print("Player Web URL:", player_data["player_url"])
print("Iframe Code:", player_data["iframe_embed"])

# 2. Search Manga with AniList HD Covers
resp = requests.get(f"{API_BASE}/api/manga/search", params={"q": "Swordmaster"}, headers=headers)
results = resp.json()["results"]
for m in results:
    print(f"Title: {m['title']} | Cover: {m['poster']}")

# 3. Get Chapter Pages
resp = requests.get(f"{API_BASE}/api/manga/chapter/33926", params={"source": "vortex"}, headers=headers)
chapter_info = resp.json()
print(f"Total Pages: {chapter_info['pages_count']}")
for page in chapter_info["pages"][:5]:
    print("Page URL:", page["url"])
```

---

### HTML iFrame Embed

You can embed the anime player or manga reader anywhere on your website with a single line of code:

#### Anime Video Player Embed:
```html
<iframe
  src="http://localhost:5646/player?id=21&episode=1&type=sub&key=YOUR_API_KEY"
  width="100%"
  height="600"
  frameborder="0"
  allow="autoplay; fullscreen; picture-in-picture; encrypted-media"
  allowfullscreen>
</iframe>
```

#### Manga Reader Embed:
```html
<iframe
  src="http://localhost:5646/manga/reader/33926?source=vortex&key=YOUR_API_KEY"
  width="100%"
  height="850"
  frameborder="0"
  allowfullscreen>
</iframe>
```
