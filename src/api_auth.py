import os
import json
import time
import secrets
from typing import Optional, List, Dict, Any
from fastapi import Request, HTTPException, Security
from fastapi.security import APIKeyHeader, APIKeyQuery

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
KEYS_FILE = os.path.join(DATA_DIR, "api_keys.json")

def ensure_data_dir():
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
                "last_used": None,
                "status": "active"
            }
        ]
        with open(KEYS_FILE, "w", encoding="utf-8") as f:
            json.dump(default_keys, f, indent=2)

def get_keys() -> List[Dict[str, Any]]:
    ensure_data_dir()
    try:
        with open(KEYS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []

def save_keys(keys: List[Dict[str, Any]]):
    ensure_data_dir()
    with open(KEYS_FILE, "w", encoding="utf-8") as f:
        json.dump(keys, f, indent=2)

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
                "documentation": "/docs or API_DOCUMENTATION.md",
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
            save_keys(keys)
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

async def optional_api_key(request: Request) -> Optional[Dict[str, Any]]:
    """FastAPI dependency for endpoints that can optionally track an API key."""
    key = extract_api_key(request)
    if key:
        try:
            return validate_and_record_api_key(key)
        except Exception:
            return None
    return None
