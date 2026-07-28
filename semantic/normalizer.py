# Normalizer
# Converts raw CRM deals (with hash-key fields) into normalized, universal format.
# The LLM NEVER sees Pipedrive/HubSpot/Salesforce-specific fields. Only clean data.

from typing import List, Dict, Any


def normalize_deals(
    raw_deals: List[Dict[str, Any]],
    field_map: Dict[str, str],
    semantic_map: Dict[str, str]
) -> List[Dict[str, Any]]:
    """
    Converts raw CRM deals into normalized format.

    Two-layer resolution:
      semantic concept → human-readable field name → CRM hash key

      "owner" → "Lead Owner" → "ecf716ae..." → "Garima"

    Returns a list of clean, universal deal dictionaries.
    """
    normalized = []

    for deal in raw_deals:
        norm_deal = {}

        for concept, field_name in semantic_map.items():
            if field_name is None:
                norm_deal[concept] = None
                continue

            # Check if the field_name is a hash-mapped custom field
            if field_name in field_map:
                hash_key = field_map[field_name]
                norm_deal[concept] = deal.get(hash_key, None)
            else:
                # It's a built-in field (like "title", "value", "id")
                norm_deal[concept] = deal.get(field_name, None)

        # Always include the raw title and value as fallbacks
        if not norm_deal.get("deal_name"):
            norm_deal["deal_name"] = deal.get("title", deal.get("name", ""))
        if not norm_deal.get("value"):
            norm_deal["value"] = deal.get("value", 0)

        normalized.append(norm_deal)

    return normalized
