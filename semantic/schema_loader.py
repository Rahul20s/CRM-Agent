# Schema Loader
# Takes any CRM connector and extracts its field definitions into a clean dictionary.

from typing import Dict, List
from crm.connector import CRMConnector


def load_field_map(connector: CRMConnector) -> Dict[str, str]:
    """
    Calls the CRM's field definitions API and builds:
      { "Lead Owner": "ecf716ae...", "Priority Tag": "23f818..." }

    This is the FIRST mapping layer:
      Human-readable field name → CRM internal hash key
    """
    fields = connector.get_field_definitions()

    field_map = {}
    for field in fields:
        name = field.get("name", "")
        key = field.get("key", "")
        if name and key:
            field_map[name] = key

    return field_map


def get_all_field_names(connector: CRMConnector) -> List[str]:
    """
    Returns just the human-readable field names.
    This list is sent to the LLM for semantic mapping.
    """
    fields = connector.get_field_definitions()
    return [f.get("name", "") for f in fields if f.get("name")]
