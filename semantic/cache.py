# Cache Layer — Persistent File-Based Caching with Schema Hash Detection
# Saves field_map and semantic_map to disk as JSON files.
# LLM is called ONLY when the CRM schema changes (detected via hash).
# Supports multi-tenant: each API key/account gets its own cache folder.

import os
import json
import hashlib
from typing import Dict, List, Any, Optional

# Directory where all cache files are stored
CACHE_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "cache")

# In-memory cache (fast access during runtime)
_memory = {
    "field_map": None,
    "semantic_map": None,
    "deals": None,
    "schema_text": None,
    "initialized": False
}


def _get_cache_path(account_id: str) -> str:
    """Returns the cache folder path for a specific account."""
    path = os.path.join(CACHE_DIR, account_id)
    os.makedirs(path, exist_ok=True)
    return path


def compute_schema_hash(field_definitions: list) -> str:
    """
    Computes a fingerprint of the CRM schema.
    If field names change, the hash changes, triggering a new LLM call.
    """
    names = sorted([f.get("name", "") for f in field_definitions])
    raw = json.dumps(names, sort_keys=True)
    return hashlib.md5(raw.encode()).hexdigest()


def has_cached_mapping(account_id: str, current_hash: str) -> bool:
    """
    Checks if a valid cached semantic map exists AND the schema hasn't changed.
    Returns True only if both semantic_map.json and matching schema_hash.txt exist.
    """
    cache_path = _get_cache_path(account_id)
    hash_file = os.path.join(cache_path, "schema_hash.txt")
    map_file = os.path.join(cache_path, "semantic_map.json")

    if not os.path.exists(hash_file) or not os.path.exists(map_file):
        return False

    with open(hash_file, "r") as f:
        stored_hash = f.read().strip()

    return stored_hash == current_hash


def save_to_disk(account_id: str, field_map: dict, semantic_map: dict, schema_hash: str):
    """Persists all mappings to disk."""
    cache_path = _get_cache_path(account_id)

    with open(os.path.join(cache_path, "field_map.json"), "w") as f:
        json.dump(field_map, f, indent=2)

    with open(os.path.join(cache_path, "semantic_map.json"), "w") as f:
        json.dump(semantic_map, f, indent=2)

    with open(os.path.join(cache_path, "schema_hash.txt"), "w") as f:
        f.write(schema_hash)

    print(f"[Cache] Saved to disk: {cache_path}")


def load_from_disk(account_id: str) -> tuple:
    """Loads field_map and semantic_map from disk."""
    cache_path = _get_cache_path(account_id)

    with open(os.path.join(cache_path, "field_map.json"), "r") as f:
        field_map = json.load(f)

    with open(os.path.join(cache_path, "semantic_map.json"), "r") as f:
        semantic_map = json.load(f)

    print(f"[Cache] Loaded from disk: {cache_path}")
    return field_map, semantic_map


# ─── In-Memory Cache (for fast access during runtime) ────────────────

def is_initialized() -> bool:
    return _memory["initialized"]


def store(field_map: Dict[str, str], semantic_map: Dict[str, str]):
    _memory["field_map"] = field_map
    _memory["semantic_map"] = semantic_map
    _memory["initialized"] = True
    print("[Cache] Schema mappings loaded into memory.")


def store_deals(deals: List[Dict[str, Any]]):
    _memory["deals"] = deals
    print(f"[Cache] {len(deals)} normalized deals in memory.")


def store_schema_text(text: str):
    _memory["schema_text"] = text


def get_field_map() -> Optional[Dict[str, str]]:
    return _memory.get("field_map")


def get_semantic_map() -> Optional[Dict[str, str]]:
    return _memory.get("semantic_map")


def get_deals() -> Optional[List[Dict[str, Any]]]:
    return _memory.get("deals")


def get_schema_text() -> Optional[str]:
    return _memory.get("schema_text")


def clear():
    _memory["field_map"] = None
    _memory["semantic_map"] = None
    _memory["deals"] = None
    _memory["schema_text"] = None
    _memory["initialized"] = False
    print("[Cache] Memory cleared.")
