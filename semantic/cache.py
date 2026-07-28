# Cache Layer
# Caches field_map and semantic_map so the LLM is called ONCE at startup.
# Every subsequent query reuses the cached mappings.

from typing import Dict, Optional

# In-memory cache (persists for the lifetime of the application process)
_cache = {
    "field_map": None,
    "semantic_map": None,
    "initialized": False
}


def is_initialized() -> bool:
    """Check if the cache has been populated."""
    return _cache["initialized"]


def store(field_map: Dict[str, str], semantic_map: Dict[str, str]):
    """Store both mappings in cache."""
    _cache["field_map"] = field_map
    _cache["semantic_map"] = semantic_map
    _cache["initialized"] = True
    print("[Cache] Schema mappings cached successfully.")


def get_field_map() -> Optional[Dict[str, str]]:
    """Retrieve cached field map."""
    return _cache.get("field_map")


def get_semantic_map() -> Optional[Dict[str, str]]:
    """Retrieve cached semantic map."""
    return _cache.get("semantic_map")


def clear():
    """Clear the cache (useful for testing or schema refresh)."""
    _cache["field_map"] = None
    _cache["semantic_map"] = None
    _cache["initialized"] = False
    print("[Cache] Cache cleared.")
