import os
import json
import time
import secrets
from typing import Optional, List, Dict, Any
from fastapi import Request, HTTPException, Security
from fastapi.security import APIKeyHeader, APIKeyQuery

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
KEYS_FILE = os.path.join(DATA_DIR, "api_keys.json")
TMP_KEYS_FILE = "/tmp/api_keys.json" if os.name != "nt" else os.path.join(os.environ.get("TEMP", "C:/tmp"), "api_keys.json")

_IN_MEMORY_KEYS = [
    {
        "id": "key_default_demo",
        "name": "Default Integration Key",
        "key": "kuhi_live_27f453e42c851403fac890ac7d1cc803",
        "created_at": "2026-10-14 13:09:58",
        "calls": 0,
        "last_used": None,
        "status": "active"
    }
]

def ensure_data_dir():
    try:
        if not os.path.exists(DATA_DIR):
            os.makedirs(DATA_DIR, exist_ok=True)
        if not os.path.exists(KEYS_FILE):
            with open(KEYS_FILE, "w", encoding="utf-8") as f:
                json.dump(_IN_MEMORY_KEYS, f, indent=2)
    except Exception:
        # Pass silently on serverless read-only filesystems (e.g. Vercel)
        pass

def get_keys() -> List[Dict[str, Any]]:
    global _IN_MEMORY_KEYS
    # 1. Try reading from /tmp first (holds dynamic keys in serverless)
    if os.path.exists(TMP_KEYS_FILE):
        try:
            with open(TMP_KEYS_FILE, "r", encoding="utf-8") as f:
                loaded = json.load(f)
                if loaded and isinstance(loaded, list):
                    _IN_MEMORY_KEYS = loaded
                    return _IN_MEMORY_KEYS
        except Exception:
            pass

    # 2. Try reading from project data file
    if os.path.exists(KEYS_FILE):
        try:
            with open(KEYS_FILE, "r", encoding="utf-8") as f:
                loaded = json.load(f)
                if loaded and isinstance(loaded, list):
                    _IN_MEMORY_KEYS = loaded
                    return _IN_MEMORY_KEYS
        except Exception:
            pass

    return _IN_MEMORY_KEYS

def save_keys(keys: List[Dict[str, Any]]):
    global _IN_MEMORY_KEYS
    _IN_MEMORY_KEYS = keys

    # 1. Try local data file
    try:
        ensure_data_dir()
        with open(KEYS_FILE, "w", encoding="utf-8") as f:
            json.dump(keys, f, indent=2)
            return
    except Exception:
        pass

    # 2. Fallback to /tmp on serverless environments
    try:
        tmp_dir = os.path.dirname(TMP_KEYS_FILE)
        if tmp_dir and not os.path.exists(tmp_dir):
            os.makedirs(tmp_dir, exist_ok=True)
        with open(TMP_KEYS_FILE, "w", encoding="utf-8") as f:
            json.dump(keys, f, indent=2)
    except Exception:
        pass

def extract_api_key(request: Request) -> Optional[str]:
    """Extract API key from query parameter, header, or bearer token."""
    # 1. Query parameter (?key=... or ?api_key=...)
    k = request.query_params.get("key") or request.query_params.get("api_key")
    if k:
        return k.strip()
    
    # 2. X-API-Key Header
    k = request.headers.get("x-api-key") or request.headers.get("X-API-Key")
    if k:
        return k.strip()
        
    # 3. Authorization: Bearer <key>
    auth = request.headers.get("authorization") or request.headers.get("Authorization")
    if auth and auth.startswith("Bearer "):
        return auth[7:].strip()

    return None

def validate_and_record_api_key(key: Optional[str]) -> Dict[str, Any]:
    """Validate key and increment its usage counter."""
    if not key:
        raise HTTPException(
            status_code=401,
            detail={
                "error": "Unauthorized",
                "message": "Missing API Key. Provide it via query param (?key=YOUR_KEY) or header ('X-API-Key: YOUR_KEY').",
                "documentation": "/docs, /documentation, or /llms.txt",
                "manage_keys": "/api/keys"
            }
        )

    keys = get_keys()
    for k in keys:
        if k.get("key") == key:
            if k.get("status") != "active":
                raise HTTPException(
                    status_code=403,
                    detail={"error": "Forbidden", "message": "This API key has been revoked or deactivated."}
                )
            k["calls"] = k.get("calls", 0) + 1
            k["last_used"] = time.strftime("%Y-%m-%d %H:%M:%S")
            try:
                save_keys(keys)
            except Exception:
                pass
            return k

    raise HTTPException(
        status_code=401,
        detail={
            "error": "Unauthorized",
            "message": "Invalid API Key. Generate or view your keys at /api/keys.",
            "documentation": "/docs"
        }
    )

async def require_api_key(request: Request) -> Dict[str, Any]:
    """FastAPI dependency for endpoints requiring a valid API key."""
    key = extract_api_key(request)
    return validate_and_record_api_key(key)
