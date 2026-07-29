# MCP Server — Schema-Driven Architecture (Performance Optimized)
# Everything is fetched and cached ONCE at startup.
# Every user query hits ONLY the in-memory cache. Zero API calls per query.

import json
import os
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
    Runs ONCE at startup:
      1. Fetch field definitions from CRM
      2. Build field_map
      3. LLM creates semantic_map
      4. Fetch all deals from CRM
      5. Normalize deals
      6. Cache EVERYTHING (mappings + deals + schema text)
    
    After this, ZERO API calls are made per user query.
    """
    if cache.is_initialized():
        return

    print("[Startup] Initializing schema discovery...")
    connector = PipedriveConnector()

    # Step 1: Build field map
    field_map = load_field_map(connector)
    print(f"[Startup] Field map: {len(field_map)} fields")

    # Step 2: Separate custom vs built-in fields
    custom_fields, builtin_fields = get_all_field_names(connector)
    print(f"[Startup] Custom: {custom_fields}")

    # Step 3: LLM semantic mapping (called ONCE, then cached)
    semantic_map = create_semantic_map(custom_fields, builtin_fields)
    print(f"[Startup] Semantic map: {json.dumps(semantic_map, indent=2)}")

    # Step 4: Cache the mappings
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
                if fuzz.partial_ratio(query_val, deal_val) < 70:
                    match = False
                    break
        if match:
            filtered_deals.append(deal)

    return json.dumps({
        "result_count": len(filtered_deals),
        "deals": filtered_deals
    }, indent=2)

