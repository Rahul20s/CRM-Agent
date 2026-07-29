# Cache Layer
# Caches field_map, semantic_map, AND normalized deals
# so Pipedrive API + LLM are called ONCE at startup, not on every query.

from typing import Dict, List, Any, Optional

# In-memory cache (persists for the lifetime of the application process)
_cache = {
    "field_map": None,
    "semantic_map": None,
    "deals": None,
    "schema_text": None,
    "initialized": False
}


def is_initialized() -> bool:
    return _cache["initialized"]


def store(field_map: Dict[str, str], semantic_map: Dict[str, str]):
    _cache["field_map"] = field_map
    _cache["semantic_map"] = semantic_map
    _cache["initialized"] = True
    print("[Cache] Schema mappings cached.")


def store_deals(deals: List[Dict[str, Any]]):
    _cache["deals"] = deals
    print(f"[Cache] {len(deals)} normalized deals cached.")


def store_schema_text(text: str):
    _cache["schema_text"] = text


def get_field_map() -> Optional[Dict[str, str]]:
    return _cache.get("field_map")


def get_semantic_map() -> Optional[Dict[str, str]]:
    return _cache.get("semantic_map")


def get_deals() -> Optional[List[Dict[str, Any]]]:
    return _cache.get("deals")


def get_schema_text() -> Optional[str]:
    return _cache.get("schema_text")


def clear():
    _cache["field_map"] = None
    _cache["semantic_map"] = None
    _cache["deals"] = None
    _cache["schema_text"] = None
    _cache["initialized"] = False
    print("[Cache] Cache cleared.")
