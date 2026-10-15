import asyncio
import importlib
import time

from src.providers._media import build_ctx

RANKING = [
    "anikoto", "aniwaves", "anizone", "kaa", "animegg",
    "mkissa", "anineko", "animeonsen",
]

WATCH_TIMEOUT = 10.0
EPISODES_TIMEOUT = 3.5
WATCH_CACHE_TTL = 300.0
EPISODES_CACHE_TTL = 600.0

_latency: dict = {}
_ep_latency: dict = {}
_failures: dict = {}
_watch_cache: dict = {}
_episodes_cache: dict = {}


def _load(name):
    try:
        return importlib.import_module(f"src.providers.{name}")
    except Exception as e:
        print(f"[RACE] provider {name} unavailable: {e}")
        return None


def providers():
    mods = []
    for name in RANKING:
        mod = _load(name)
        if mod is not None:
            mods.append((name, mod))
    return mods


def record_latency(name: str, seconds: float, ok: bool, kind: str = "watch"):
    table = _latency if kind == "watch" else _ep_latency
    if ok:
        prev = table.get(name)
        table[name] = seconds if prev is None else round(0.7 * prev + 0.3 * seconds, 3)
        _failures[name] = 0
    else:
        _failures[name] = _failures.get(name, 0) + 1


def default_provider():
    if not _latency:
        return RANKING[0]
    return sorted(_latency.items(), key=lambda kv: kv[1])[0][0]


def latency_table() -> dict:
    return {name: {"avg_seconds": _latency.get(name),
                   "episodes_seconds": _ep_latency.get(name),
                   "failures": _failures.get(name, 0)}
            for name in RANKING}


async def _watch_one(mod, name, anilist_id, ep, audio, ctx):
    key = (name, anilist_id, ep, audio)
    hit = _watch_cache.get(key)
    if hit and hit[0] > time.time():
        return name, hit[1], 0.0, True
    t0 = time.time()
    try:
        streams = await asyncio.wait_for(mod.watch(anilist_id, audio, ep, ctx), WATCH_TIMEOUT)
        dt = round(time.time() - t0, 3)
        if streams:
            valid_streams = []
            for s in streams:
                u = s.get("url", "")
                if not u or not u.startswith("http"):
                    continue
                # Exclude known broken / dead domains
                if any(bad in u for bad in ("nukitashi.top", "animeapps.top", "playeng.animeapps")):
                    continue
                valid_streams.append(s)
            if valid_streams:
                _watch_cache[key] = (time.time() + WATCH_CACHE_TTL, valid_streams)
                return name, valid_streams, dt, True
        return name, None, dt, False
    except Exception as e:
        return name, None, round(time.time() - t0, 3), False


async def race_watch(anilist_id: int, ep: int, audio: str = "sub",
                     preferred: str | None = None) -> dict | None:
    mods = providers()
    if not mods:
        return None
    ctx = await build_ctx(anilist_id)
    if preferred:
        pick = next((m for m in mods if m[0] == preferred), None)
        if pick is not None:
            name, streams, dt, ok = await _watch_one(pick[1], pick[0], anilist_id, ep, audio, ctx)
            record_latency(name, dt, ok)
            if ok:
                return {"provider": name, "streams": streams,
                        "requestedProvider": preferred,
                        "timings": {name: {"seconds": dt, "ok": True}},
                        "defaultProvider": default_provider()}
            mods = [m for m in mods if m[0] != preferred]
            if not mods:
                return None
    pending = {asyncio.ensure_future(_watch_one(mod, name, anilist_id, ep, audio, ctx))
               for name, mod in mods}
    timings: dict = {}
    winner = None
    try:
        while pending:
            done, pending = await asyncio.wait(pending, return_when=asyncio.FIRST_COMPLETED)
            for task in done:
                name, streams, dt, ok = task.result()
                timings[name] = {"seconds": dt, "ok": ok}
                record_latency(name, dt, ok)
                if ok and winner is None:
                    winner = {"provider": name, "streams": streams}
            if winner is not None:
                break
    finally:
        for task in pending:
            task.cancel()

    if winner is None:
        return None
    winner["timings"] = timings
    winner["defaultProvider"] = default_provider()
    if preferred:
        winner["requestedProvider"] = preferred
    return winner


async def _episodes_one(mod, name, anilist_id, ctx):
    t0 = time.time()
    try:
        data = await asyncio.wait_for(mod.get_episodes(anilist_id, ctx), EPISODES_TIMEOUT)
        eps = (data.get("episodes") or {})
        count = sum(len(v) for v in eps.values() if isinstance(v, list))
        record_latency(name, time.time() - t0, count > 0, kind="episodes")
        return name, data if count > 0 else None
    except Exception as e:
        record_latency(name, time.time() - t0, False, kind="episodes")
        return name, None


async def merged_episodes(anilist_id: int) -> dict | None:
    hit = _episodes_cache.get(anilist_id)
    if hit and hit[0] > time.time():
        return hit[1]

    mods = providers()
    if not mods:
        return None
    ctx = await build_ctx(anilist_id)
    tasks = [asyncio.create_task(_episodes_one(mod, name, anilist_id, ctx)) for name, mod in mods]
    done, pending = await asyncio.wait(tasks, timeout=3.5)
    for t in pending:
        t.cancel()

    merged = {}
    for t in done:
        try:
            name, data = t.result()
            if data:
                merged[name] = data
        except Exception:
            pass

    if not merged:
        return None
    res = {"anilistId": anilist_id, "source": "native", "providers": merged}
    _episodes_cache[anilist_id] = (time.time() + EPISODES_CACHE_TTL, res)
    return res


def merge_subtitles(streams: list) -> list:
    seen, out = set(), []
    for s in streams or []:
        for sub in s.get("subtitles") or []:
            url = sub.get("url")
            if url and url not in seen:
                seen.add(url)
                out.append(sub)
    return out


def providers_status() -> dict:
    return {
        "defaultProvider": default_provider(),
        "ranking": RANKING,
        "available": [name for name, _ in providers()],
        "latency": latency_table(),
    }
