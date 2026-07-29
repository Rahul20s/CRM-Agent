# MCP Server — Schema-Driven Architecture (Performance Optimized)
# Everything is fetched and cached ONCE at startup.
# Every user query hits ONLY the in-memory cache. Zero API calls per query.

import json
import os
import hashlib
from dotenv import load_dotenv
from thefuzz import fuzz

from crm.pipedrive import PipedriveConnector
from semantic.schema_loader import load_field_map, get_all_field_names
from semantic.semantic_mapper import create_semantic_map
from semantic.normalizer import normalize_deals
from semantic import cache

load_dotenv()


def initialize():
    """
    Production startup flow:
      1. Fetch field definitions from CRM
      2. Compute schema hash
      3. If hash matches cached version → load from disk (NO LLM call)
      4. If hash changed or no cache → call LLM, save to disk
      5. Fetch and normalize deals
      6. Cache everything in memory

    Result: LLM is called ONLY when the CRM schema changes.
    """
    if cache.is_initialized():
        return

    print("[Startup] Initializing schema discovery...")
    connector = PipedriveConnector()

    # Use API key hash as account identifier (stable across sessions)
    api_key = os.getenv("PIPEDRIVE_API_KEY", "default")
    account_id = hashlib.md5(api_key.encode()).hexdigest()[:12]

    # Step 1: Fetch field definitions
    raw_fields = connector.get_field_definitions()
    field_map = {}
    for field in raw_fields:
        name = field.get("name", "")
        key = field.get("key", "")
        if name and key:
            field_map[name] = key
    print(f"[Startup] Field map: {len(field_map)} fields")

    # Step 2: Compute schema hash
    schema_hash = cache.compute_schema_hash(raw_fields)
    print(f"[Startup] Schema hash: {schema_hash}")

    # Step 3: Check persistent cache
    if cache.has_cached_mapping(account_id, schema_hash):
        # Schema unchanged → load from disk, skip LLM entirely
        print("[Startup] Schema unchanged. Loading cached mappings from disk...")
        field_map_cached, semantic_map = cache.load_from_disk(account_id)
        field_map = field_map_cached
    else:
        # Schema changed or first run → call LLM
        print("[Startup] New schema detected. Calling LLM for semantic mapping...")
        custom_fields, builtin_fields = get_all_field_names(connector)
        print(f"[Startup] Custom: {custom_fields}")
        semantic_map = create_semantic_map(custom_fields, builtin_fields)
        print(f"[Startup] Semantic map: {json.dumps(semantic_map, indent=2)}")

        # Save to disk for future restarts
        cache.save_to_disk(account_id, field_map, semantic_map, schema_hash)

    # Step 4: Load into memory
    cache.store(field_map, semantic_map)

    # Step 5: Fetch and normalize ALL deals
    raw_deals = connector.get_deals()
    deals = normalize_deals(raw_deals, field_map, semantic_map)
    cache.store_deals(deals)

    # Step 6: Build and cache schema text
    unique_values = {}
    for concept in ["owner", "status", "folder", "priority", "organization"]:
        values = list(set([
            str(d.get(concept, ""))
            for d in deals
            if d.get(concept) is not None and str(d.get(concept)).strip() != ""
        ]))
        unique_values[f"unique_{concept}s"] = values

    schema_fields = {}
    for concept, field_name in semantic_map.items():
        if field_name:
            schema_fields[concept] = f"Mapped from CRM field: '{field_name}'"

    schema_text = json.dumps({
        "fields": schema_fields,
        "detected_custom_fields": [name for name in field_map.keys() if len(name) < 30 and not name.startswith("Source") and field_map[name] != name],
        **unique_values,
        "total_records": len(deals)
    }, indent=2)

    cache.store_schema_text(schema_text)
    print(f"[Startup] Complete. {len(deals)} deals cached. Ready for queries.")


# ─── MCP TOOLS (all read from cache, zero API calls) ─────────────────

def get_crm_schema() -> str:
    """Returns the cached LIVE schema. No API calls."""
    initialize()
    return cache.get_schema_text() or "{}"


def query_crm_deals(filters: dict, requesting_user_role: str = "admin") -> str:
    """
    Query normalized CRM deals from cache.
    Uses fuzzy semantic matching and RBAC.
    """
    initialize()
    filters_dict = filters if filters else {}
    deals = cache.get_deals() or []

    # RBAC
    authorized_deals = []
    for deal in deals:
        val = deal.get("value", 0)
        if val is None:
            val = 0
        if requesting_user_role != "admin" and val > 100000:
            continue
        authorized_deals.append(deal)

    # Fuzzy filtering
    filtered_deals = []
    for deal in authorized_deals:
        match = True
        for key, value in filters_dict.items():
            if key.endswith("__not"):
                actual_key = key.replace("__not", "")
                deal_val = str(deal.get(actual_key, "") or "").lower()
                query_val = str(value).lower()
                if fuzz.partial_ratio(query_val, deal_val) > 80:
                    match = False
                    break
            else:
                deal_val = str(deal.get(key, "") or "").lower()
                query_val = str(value).lower()
                if fuzz.partial_ratio(query_val, deal_val) < 80:
                    match = False
                    break
        if match:
            filtered_deals.append(deal)

    return json.dumps({
        "result_count": len(filtered_deals),
        "deals": filtered_deals
    }, indent=2)

