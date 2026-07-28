# MCP Server — Schema-Driven Architecture
# This is the heart of the application. It:
#   1. Discovers schema from ANY CRM connector (Pipedrive today, HubSpot tomorrow)
#   2. Uses LLM ONCE to create semantic field mappings
#   3. Caches everything
#   4. Normalizes all deals into universal format
#   5. Exposes only clean, normalized data to the AI

import json
import os
from dotenv import load_dotenv
from fastmcp import FastMCP
from thefuzz import fuzz

# Import the modular architecture
from crm.pipedrive import PipedriveConnector
from semantic.schema_loader import load_field_map, get_all_field_names
from semantic.semantic_mapper import create_semantic_map
from semantic.normalizer import normalize_deals
from semantic import cache

load_dotenv()

# Initialize FastMCP server
mcp = FastMCP("TreelifeCRM")

# ─── STARTUP: Schema Discovery & Semantic Mapping ───────────────────
# This runs ONCE. The LLM maps fields once, then it's cached forever.

def initialize():
    """
    Startup flow:
      1. Connect to CRM
      2. Fetch field definitions (GET /dealFields)
      3. Build field_map (human name → hash key)
      4. Ask LLM to create semantic_map (concept → human name)
      5. Cache both maps
    """
    if cache.is_initialized():
        return

    print("[Startup] Initializing schema discovery...")

    connector = PipedriveConnector()

    # Step 1: Build field map
    field_map = load_field_map(connector)
    print(f"[Startup] Field map built: {len(field_map)} fields discovered")

    # Step 2: Get separated custom vs built-in field names
    custom_fields, builtin_fields = get_all_field_names(connector)
    print(f"[Startup] Custom fields: {custom_fields}")
    print(f"[Startup] Built-in fields: {builtin_fields}")

    # Step 3: Ask LLM to create semantic mapping (custom fields prioritized)
    semantic_map = create_semantic_map(custom_fields, builtin_fields)
    print(f"[Startup] Semantic map: {json.dumps(semantic_map, indent=2)}")

    # Step 4: Cache everything
    cache.store(field_map, semantic_map)
    print("[Startup] Initialization complete.")


def load_data():
    """
    Fetches live deals and normalizes them using cached mappings.
    Returns normalized deals that the LLM can understand universally.
    """
    # Ensure initialized
    initialize()

    connector = PipedriveConnector()
    field_map = cache.get_field_map()
    semantic_map = cache.get_semantic_map()

    # Fetch raw deals from CRM
    raw_deals = connector.get_deals()

    # Normalize using the two-layer mapping
    deals = normalize_deals(raw_deals, field_map, semantic_map)

    return {"deals": deals}


# ─── MCP TOOLS ───────────────────────────────────────────────────────

@mcp.tool()
def get_crm_schema() -> str:
    """
    Returns the LIVE schema of the CRM, including unique values for each field.
    This is called dynamically — never hardcoded.
    """
    data = load_data()
    deals = data.get("deals", [])

    # Extract unique values for every normalized field
    unique_values = {}
    for concept in ["owner", "status", "folder", "priority", "organization"]:
        values = list(set([
            str(d.get(concept, ""))
            for d in deals
            if d.get(concept) is not None and str(d.get(concept)).strip() != ""
        ]))
        unique_values[f"unique_{concept}s"] = values

    # Build schema description from semantic map
    semantic_map = cache.get_semantic_map() or {}
    schema_fields = {}
    for concept, field_name in semantic_map.items():
        if field_name:
            schema_fields[concept] = f"Mapped from CRM field: '{field_name}'"

    context = {
        "fields": schema_fields,
        **unique_values,
        "total_records": len(deals)
    }

    return json.dumps(context, indent=2)


@mcp.tool()
def query_crm_deals(filters: dict, requesting_user_role: str = "admin") -> str:
    """
    Query normalized CRM deals using dictionary filters.
    Uses universal field names (owner, priority, status, folder, etc.)
    Use __not suffix for exclusion.
    Includes RBAC and Fuzzy Semantic matching.
    """
    filters_dict = filters if filters else {}

    data = load_data()
    deals = data.get("deals", [])

    # 1. RBAC (Security Layer)
    authorized_deals = []
    for deal in deals:
        val = deal.get("value", 0)
        if val is None:
            val = 0
        if requesting_user_role != "admin" and val > 100000:
            continue
        authorized_deals.append(deal)

    # 2. Fuzzy Semantic Filtering
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


if __name__ == "__main__":
    mcp.run()
