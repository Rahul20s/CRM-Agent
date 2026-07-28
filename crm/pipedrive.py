# Pipedrive CRM Connector
# Implements the CRMConnector interface for Pipedrive.
# Handles: GET /dealFields, GET /deals (with pagination)

import os
import requests
from typing import List, Dict, Any
from crm.connector import CRMConnector


class PipedriveConnector(CRMConnector):
    """
    Pipedrive-specific connector. Fetches field definitions and deals
    using the Pipedrive REST API v1.
    """

    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.getenv("PIPEDRIVE_API_KEY")
        self.base_url = "https://api.pipedrive.com/v1"

    def get_field_definitions(self) -> List[Dict[str, str]]:
        """
        Calls GET /dealFields and returns a list of
        {"name": "Lead Owner", "key": "ecf716ae..."} dicts.
        """
        if not self.api_key:
            return []

        url = f"{self.base_url}/dealFields?api_token={self.api_key}"
        try:
            response = requests.get(url)
            data = response.json()

            fields = []
            if data.get("success") and data.get("data"):
                for field in data["data"]:
                    fields.append({
                        "name": field.get("name", ""),
                        "key": field.get("key", ""),
                        "field_type": field.get("field_type", "")
                    })
            return fields
        except Exception as e:
            print(f"[Pipedrive] Error fetching field definitions: {e}")
            return []

    def get_deals(self) -> List[Dict[str, Any]]:
        """
        Calls GET /deals with pagination and returns ALL raw deals.
        Each deal contains hash-key fields like "ecf716ae...": "Garima".
        """
        if not self.api_key:
            return []

        all_deals = []
        start = 0

        while True:
            url = f"{self.base_url}/deals?api_token={self.api_key}&start={start}&limit=500"
            try:
                response = requests.get(url)
                data = response.json()

                if data.get("success") and data.get("data"):
                    all_deals.extend(data["data"])

                    pagination = data.get("additional_data", {}).get("pagination", {})
                    if pagination.get("more_items_in_collection"):
                        start = pagination.get("next_start", start + 500)
                    else:
                        break
                else:
                    break
            except Exception as e:
                print(f"[Pipedrive] Error fetching deals: {e}")
                break

        return all_deals

    def get_crm_name(self) -> str:
        return "Pipedrive"
