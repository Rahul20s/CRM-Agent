# Schema Loader
# Takes any CRM connector and extracts its field definitions into a clean dictionary.
# Separates CUSTOM fields from BUILT-IN fields so the LLM can prioritize correctly.

from typing import Dict, List, Tuple
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


def get_all_field_names(connector: CRMConnector) -> Tuple[List[str], List[str]]:
    """
    Returns two separate lists:
      1. Custom field names (created by the user — these are the important ones)
      2. Built-in field names (system defaults like Title, Value, ID)

    This separation helps the LLM prioritize custom fields.
    """
    fields = connector.get_field_definitions()

    custom_fields = []
    builtin_fields = []

    for f in fields:
        name = f.get("name", "")
        if not name:
            continue
        if f.get("is_custom", False):
            custom_fields.append(name)
        else:
            builtin_fields.append(name)

    return custom_fields, builtin_fields
