import os
import json
import re
import secrets
import time
import asyncio
import subprocess
from typing import Optional
from urllib.parse import quote, urljoin
import httpx
from fastapi import FastAPI, Query, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse, Response, StreamingResponse

from fastapi.staticfiles import StaticFiles

from src.endpoints import router
from src.manga.router import router as manga_router
from src.health.router import router as health_router
from src.api_routes import api_router

app = FastAPI(title="Kuhi Anime & Manga Studio API", version="3.5")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

if os.path.exists("assets"):
    app.mount("/assets", StaticFiles(directory="assets"), name="assets")

app.include_router(router, prefix="/anime")
app.include_router(manga_router)
app.include_router(health_router)
app.include_router(api_router)

# ==========================================================
# API KEYS PERSISTENCE & MANAGEMENT
# ==========================================================
DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
KEYS_FILE = os.path.join(DATA_DIR, "api_keys.json")

def _ensure_data_dir():
    if not os.path.exists(DATA_DIR):
        os.makedirs(DATA_DIR, exist_ok=True)
    if not os.path.exists(KEYS_FILE):
        default_keys = [
            {
                "id": "key_default_demo",
                "name": "Default Integration Key",
                "key": f"kuhi_live_{secrets.token_hex(16)}",
                "created_at": time.strftime("%Y-%m-%d %H:%M:%S"),
                "calls": 0,
                "status": "active"
            }
        ]
        with open(KEYS_FILE, "w", encoding="utf-8") as f:
            json.dump(default_keys, f, indent=2)

def _get_keys() -> list:
    _ensure_data_dir()
    try:
        with open(KEYS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []

def _save_keys(keys: list):
    _ensure_data_dir()
    with open(KEYS_FILE, "w", encoding="utf-8") as f:
        json.dump(keys, f, indent=2)


@app.get("/api/keys")
async def list_api_keys():
    """List all registered API keys"""
    return {"keys": _get_keys()}


@app.post("/api/keys")
async def create_api_key(request: Request):
    """Create a new API key with a custom label"""
    body = {}
    try:
        body = await request.json()
    except Exception:
        pass
    
    name = body.get("name", "").strip() or f"Integration Key {time.strftime('%b %d')}"
    new_entry = {
        "id": f"key_{secrets.token_hex(6)}",
        "name": name,
        "key": f"kuhi_live_{secrets.token_hex(16)}",
        "created_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "calls": 0,
        "status": "active"
    }
    keys = _get_keys()
    keys.append(new_entry)
    _save_keys(keys)
    return new_entry


@app.delete("/api/keys/{key_id}")
async def delete_api_key(key_id: str):
    """Revoke/Delete an API key"""
    keys = _get_keys()
    keys = [k for k in keys if k.get("id") != key_id and k.get("key") != key_id]
    _save_keys(keys)
    return {"success": True, "message": f"Key {key_id} deleted"}


# ==========================================================
# ANIME SKIP TIMES (ANI-SKIP INTEGRATION)
# ==========================================================
_SKIP_CACHE = {}

@app.get("/anime/skip/{id}/{episode}")
async def get_skip_times(id: int, episode: int, mal_id: int | None = None):
    """Fetch accurate intro (OP) and outro (ED) skip timestamps from AniSkip"""
    actual_mal_id = mal_id or id
    cache_key = f"{actual_mal_id}_{episode}"
    if cache_key in _SKIP_CACHE:
        return _SKIP_CACHE[cache_key]

    url = f"https://api.aniskip.com/v2/skip-times/{actual_mal_id}/{episode}?types=op&types=ed&episodeLength=0"
    result = {"found": False, "intro": None, "outro": None}

    try:
        async with httpx.AsyncClient(timeout=6.0) as client:
            res = await client.get(url)
            if res.status_code == 200:
                data = res.json()
                if data.get("found") and isinstance(data.get("results"), list):
                    for item in data["results"]:
                        stype = item.get("skipType")
                        interval = item.get("interval") or {}
                        start = interval.get("startTime")
                        end = interval.get("endTime")
                        if start is not None and end is not None:
                            if stype == "op" and not result["intro"]:
                                result["intro"] = {"start": round(float(start), 2), "end": round(float(end), 2)}
                                result["found"] = True
                            elif stype == "ed" and not result["outro"]:
                                result["outro"] = {"start": round(float(start), 2), "end": round(float(end), 2)}
                                result["found"] = True
    except Exception as e:
        print(f"AniSkip query error: {e}")

    _SKIP_CACHE[cache_key] = result
    return result


# ==========================================================
# STREAM PROXIES (M3U8, SEGMENTS, MP4)
# ==========================================================
def _norm_url(url: str) -> str | None:
    url = (url or "").strip()
    if url.startswith("//"):
        return "https:" + url
    if url.startswith("http://") or url.startswith("https://"):
        return url
    return None


@app.get("/proxy_m3u8")
async def proxy_m3u8(url: str, referer: str):
    url = _norm_url(url)
    if not url:
        return Response(content='{"detail":"bad proxy url"}', status_code=400,
                        media_type="application/json")
    async with httpx.AsyncClient(timeout=15.0, follow_redirects=True, verify=False) as client:
        h = HEADERS.copy()
        h["Referer"] = referer
        resp = await client.get(url, headers=h)

        content = resp.text
        lines = []
        is_variant = False
        for line in content.splitlines():
            stripped = line.strip()
            if not stripped:
                lines.append(line)
                continue

            # Handle URI inside EXT-X-MEDIA (audio/subtitles)
            if stripped.startswith('#EXT-X-MEDIA:'):
                def _sub_media(m):
                    media_url = urljoin(url, m.group(1))
                    return f'URI="/proxy_m3u8?url={quote(media_url, safe="")}&referer={quote(referer, safe="")}"'
                line = re.sub(r'URI="([^"]+)"', _sub_media, line)
                lines.append(line)
                continue

            # Handle URI inside EXT-X-MAP (initialization header segment)
            if stripped.startswith('#EXT-X-MAP:'):
                def _sub_map(m):
                    seg_url = urljoin(url, m.group(1))
                    return f'URI="/proxy_segment?url={quote(seg_url, safe="")}&referer={quote(referer, safe="")}"'
                line = re.sub(r'URI="([^"]+)"', _sub_map, line)
                lines.append(line)
                continue

            if stripped.startswith('#EXT-X-STREAM-INF:') or stripped.startswith('#EXT-X-I-FRAME-STREAM-INF:'):
                is_variant = True
                lines.append(line)
                continue

            if stripped.startswith('#'):
                lines.append(line)
                continue

            # Non-comment line (URL)
            absolute_url = urljoin(url, stripped)
            if is_variant or '.m3u8' in stripped.lower():
                line = f"/proxy_m3u8?url={quote(absolute_url, safe='')}&referer={quote(referer, safe='')}"
            else:
                line = f"/proxy_segment?url={quote(absolute_url, safe='')}&referer={quote(referer, safe='')}"
            is_variant = False
            lines.append(line)

        return Response(content='\n'.join(lines), media_type="application/vnd.apple.mpegurl")


@app.get("/proxy_segment")
async def proxy_segment(url: str, referer: str, request: Request):
    url = _norm_url(url)
    if not url:
        return Response(content='{"detail":"bad proxy url"}', status_code=400,
                        media_type="application/json")
    async with httpx.AsyncClient(timeout=30.0, follow_redirects=True, verify=False) as client:
        h = HEADERS.copy()
        h["Referer"] = referer
        range_h = request.headers.get("Range")
        if range_h:
            h["Range"] = range_h
        resp = await client.get(url, headers=h)
        res_h = {"Content-Type": "video/mp2t", "Accept-Ranges": "bytes"}
        if "content-range" in resp.headers:
            res_h["Content-Range"] = resp.headers["content-range"]
        return Response(content=resp.content, status_code=resp.status_code, headers=res_h)


@app.get("/proxy_mp4")
async def proxy_mp4(url: str, referer: str, request: Request, download: bool = False, filename: Optional[str] = None):
    url = _norm_url(url)
    if not url:
        return Response(content='{"detail":"bad proxy url"}', status_code=400,
                        media_type="application/json")

    headers = HEADERS.copy()
    headers["Referer"] = referer
    range_header = request.headers.get("range")
    if range_header:
        headers["Range"] = range_header

    client = httpx.AsyncClient(timeout=30.0, follow_redirects=True, verify=False)
    try:
        req = client.build_request("GET", url, headers=headers)
        resp = await client.send(req, stream=True)

        resp_headers = {}
        for h in ("content-type", "content-length", "accept-ranges", "content-range"):
            val = resp.headers.get(h)
            if val:
                resp_headers[h] = val
        if "content-type" not in resp_headers:
            resp_headers["content-type"] = "video/mp4"
        if "accept-ranges" not in resp_headers:
            resp_headers["accept-ranges"] = "bytes"
        if download:
            fn = filename or "episode.mp4"
            if not fn.endswith(".mp4"):
                fn += ".mp4"
            resp_headers["content-disposition"] = f'attachment; filename="{fn}"'

        async def stream_generator():
            try:
                async for chunk in resp.aiter_bytes():
                    yield chunk
            finally:
                await resp.aclose()
                await client.aclose()

        return StreamingResponse(
            stream_generator(),
            status_code=resp.status_code,
            headers=resp_headers
        )
    except Exception as e:
        await client.aclose()
        return Response(content=f'{{"detail":"failed to proxy mp4: {str(e)}"}}', status_code=502,
                        media_type="application/json")


@app.get("/download_stream")
async def download_stream(
    url: str,
    referer: str = "https://play.echovideo.ru/",
    filename: Optional[str] = None,
    type: str = "auto"
):
    """
    Direct 1-click episode video downloader.
    - If MP4: Streams MP4 directly as a downloaded attachment.
    - If HLS (.m3u8): Streams dynamically transmuxed MP4 via FFmpeg directly to the browser.
    """
    url = _norm_url(url)
    if not url:
        raise HTTPException(status_code=400, detail="Invalid stream URL")

    fn = filename or "episode.mp4"
    if not fn.lower().endswith(".mp4"):
        fn += ".mp4"
    safe_fn = re.sub(r'[^a-zA-Z0-9_\-\. ]', '_', fn).strip()
    if not safe_fn.lower().endswith(".mp4"):
        safe_fn += ".mp4"

    is_mp4 = (type.lower() == "mp4") or (".mp4" in url.lower() and ".m3u8" not in url.lower())

    if is_mp4:
        headers = HEADERS.copy()
        headers["Referer"] = referer
        client = httpx.AsyncClient(timeout=60.0, follow_redirects=True, verify=False)
        try:
            req = client.build_request("GET", url, headers=headers)
            resp = await client.send(req, stream=True)
            resp_headers = {
                "content-type": "video/mp4",
                "content-disposition": f'attachment; filename="{safe_fn}"',
                "accept-ranges": "bytes",
                "access-control-allow-origin": "*"
            }
            cl = resp.headers.get("content-length")
            if cl:
                resp_headers["content-length"] = cl

            async def mp4_generator():
                try:
                    async for chunk in resp.aiter_bytes(64 * 1024):
                        yield chunk
                finally:
                    await resp.aclose()
                    await client.aclose()

            return StreamingResponse(
                mp4_generator(),
                status_code=resp.status_code,
                headers=resp_headers
            )
        except Exception as e:
            await client.aclose()
            raise HTTPException(status_code=502, detail=f"MP4 streaming failed: {e}")

    # HLS Stream -> Fast MP4 conversion via FFmpeg
    headers_arg = f"User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64)\r\nReferer: {referer}\r\n"
    cmd = [
        "ffmpeg", "-nostdin", "-v", "warning",
        "-headers", headers_arg,
        "-protocol_whitelist", "file,http,https,tcp,tls,crypto,data",
        "-allowed_extensions", "ALL",
        "-allowed_segment_extensions", "ALL",
        "-extension_picky", "false",
        "-f", "hls",
        "-i", url,
        "-c", "copy",
        "-bsf:a", "aac_adtstoasc",
        "-f", "mp4",
        "-movflags", "frag_keyframe+empty_moov+default_base_moof",
        "pipe:1"
    ]

    try:
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            bufsize=64 * 1024
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start downloader: {e}")

    resp_headers = {
        "content-type": "video/mp4",
        "content-disposition": f'attachment; filename="{safe_fn}"',
        "accept-ranges": "bytes",
        "access-control-allow-origin": "*"
    }

    def hls_ffmpeg_generator():
        try:
            while True:
                chunk = proc.stdout.read(64 * 1024)
                if not chunk:
                    break
                yield chunk
        finally:
            if proc.poll() is None:
                try:
                    proc.kill()
                except Exception:
                    pass

    return StreamingResponse(
        hls_ffmpeg_generator(),
        media_type="video/mp4",
        headers=resp_headers
    )


@app.get("/proxy_sub")
async def proxy_sub(url: str, referer: Optional[str] = None):
    """Proxy WebVTT/SRT subtitles with CORS headers to prevent cross-origin blocking."""
    url = _norm_url(url)
    if not url:
        return Response(content='WEBVTT\n\n', status_code=400, media_type="text/vtt")

    headers = HEADERS.copy()
    if referer:
        headers["Referer"] = referer

    client = httpx.AsyncClient(timeout=15.0, follow_redirects=True, verify=False)
    try:
        resp = await client.get(url, headers=headers)
        content_type = resp.headers.get("content-type", "text/vtt; charset=utf-8")
        res_headers = {
            "Content-Type": content_type,
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, OPTIONS",
            "Cache-Control": "public, max-age=86400"
        }
        return Response(content=resp.content, status_code=resp.status_code, headers=res_headers)
    except Exception as e:
        return Response(content=f'WEBVTT\n\nNOTE error: {str(e)}\n', status_code=502, media_type="text/vtt")
    finally:
        await client.aclose()


@app.get("/proxy_image")
async def proxy_image(url: str, referer: Optional[str] = None):
    url = _norm_url(url)
    if not url:
        return Response(content='{"detail":"bad image url"}', status_code=400, media_type="application/json")

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Accept": "image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8",
    }
    if referer:
        headers["Referer"] = referer
    else:
        headers["Referer"] = "https://vortexscans.org/"

    client = httpx.AsyncClient(timeout=20.0, follow_redirects=True, verify=False)
    try:
        resp = await client.get(url, headers=headers)
        media_type = resp.headers.get("content-type", "image/webp")
        res_headers = {
            "Content-Type": media_type,
            "Access-Control-Allow-Origin": "*",
            "Cache-Control": "public, max-age=86400"
        }
        return Response(content=resp.content, status_code=resp.status_code, headers=res_headers)
    except Exception as e:
        return Response(content=f'{{"detail":"failed to proxy image: {str(e)}"}}', status_code=502, media_type="application/json")
    finally:
        await client.aclose()



# ==========================================================
# UI SERVING
# ==========================================================
TEMPLATES_DIR = os.path.join(os.path.dirname(__file__), "templates")
TESTER_FILE = os.path.join(TEMPLATES_DIR, "tester.html")
PLAYER_FILE = os.path.join(TEMPLATES_DIR, "player.html")
READER_FILE = os.path.join(TEMPLATES_DIR, "reader.html")
LLMS_FILE = os.path.join(os.path.dirname(__file__), "..", "llms.txt")
DOCS_MD_FILE = os.path.join(os.path.dirname(__file__), "..", "API_DOCUMENTATION.md")


@app.get("/", response_class=HTMLResponse)
@app.get("/tester", response_class=HTMLResponse)
@app.get("/keys", response_class=HTMLResponse)
@app.get("/documentation", response_class=HTMLResponse)
async def home():
    if os.path.exists(TESTER_FILE):
        with open(TESTER_FILE, "r", encoding="utf-8") as f:
            return f.read()
    return "<h1>Kuhi Anime Studio</h1><p>tester.html not found</p>"


@app.get("/llms.txt", response_class=Response)
async def serve_llms_txt():
    """AI-readable complete API specification for LLMs and autonomous agents."""
    if os.path.exists(LLMS_FILE):
        with open(LLMS_FILE, "r", encoding="utf-8") as f:
            return Response(content=f.read(), media_type="text/plain; charset=utf-8")
    return Response(content="# Kuhi Anime & Manga Studio API\nSee /docs", media_type="text/plain")


@app.get("/api/docs/raw", response_class=Response)
async def serve_raw_docs():
    """Raw Markdown documentation for developer tools and AI models."""
    if os.path.exists(DOCS_MD_FILE):
        with open(DOCS_MD_FILE, "r", encoding="utf-8") as f:
            return Response(content=f.read(), media_type="text/markdown; charset=utf-8")
    return Response(content="# Kuhi Anime & Manga Studio API Documentation\nSee /docs", media_type="text/markdown")


@app.get("/player", response_class=HTMLResponse)
async def player_page():
    """Built-in custom video player with horizontal hover volume slider, 10s skip buttons, and AniSkip button at bottom: 85px."""
    if os.path.exists(PLAYER_FILE):
        with open(PLAYER_FILE, "r", encoding="utf-8") as f:
            return f.read()
    return "<h1>Kuhi Player</h1><p>player.html not found</p>"


@app.get("/manga/reader/{chapter_id}", response_class=HTMLResponse)
async def manga_reader_page(chapter_id: str):
    """Built-in clean manga/manhwa chapter reader with vertical continuous scroll and page switcher."""
    if os.path.exists(READER_FILE):
        with open(READER_FILE, "r", encoding="utf-8") as f:
            return f.read()
    return "<h1>Kuhi Manga Reader</h1><p>reader.html not found</p>"
