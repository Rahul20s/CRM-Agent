# CRM Connector Base Interface
# Every CRM connector (Pipedrive, HubSpot, Salesforce, Zoho) implements this interface.
# The rest of the application NEVER knows which CRM is behind it.

from abc import ABC, abstractmethod
from typing import List, Dict, Any


class CRMConnector(ABC):
    """
    Abstract base class for all CRM connectors.
    Any new CRM integration simply implements these 3 methods.
    """

    @abstractmethod
    def get_field_definitions(self) -> List[Dict[str, str]]:
        """
        Returns a list of all field definitions from the CRM.
        Each dict must have at minimum: {"name": "...", "key": "..."}
        """
        pass

    @abstractmethod
    def get_deals(self) -> List[Dict[str, Any]]:
        """
        Returns a list of raw deal dictionaries from the CRM.
        These contain the CRM's internal hash keys as field names.
        """
        pass

    @abstractmethod
    def get_crm_name(self) -> str:
        """Returns the name of the CRM (e.g., 'Pipedrive', 'HubSpot')."""
        pass
