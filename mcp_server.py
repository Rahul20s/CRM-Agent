from fastmcp import FastMCP
import json
import os
import requests
from dotenv import load_dotenv
from thefuzz import fuzz

load_dotenv()

# Initialize FastMCP server
mcp = FastMCP("TreelifeCRM")

# ─── DYNAMIC FIELD MAPPING ───────────────────────────────────────────
# Fetches custom field definitions from Pipedrive so we never hardcode field keys.
# This means if the CRM schema changes, the agent adapts automatically.

def get_field_mapping():
    """
    Fetches all custom deal fields from Pipedrive and creates a
    human-readable-name -> hash-key mapping.
    """
    api_key = os.getenv("PIPEDRIVE_API_KEY")
    if not api_key:
        return {}
    
    url = f"https://api.pipedrive.com/v1/dealFields?api_token={api_key}"
    try:
        response = requests.get(url)
        data = response.json()
        
        field_map = {}
        if data.get("success") and data.get("data"):
            for field in data["data"]:
                field_map[field["name"]] = field["key"]
        return field_map
    except Exception as e:
        print(f"Error fetching field definitions: {e}")
        return {}

def load_data():
    """
    Fetches live deals from Pipedrive API and maps custom field hash-keys
    back to human-readable names.
    """
    api_key = os.getenv("PIPEDRIVE_API_KEY")
    if not api_key:
        print("Warning: PIPEDRIVE_API_KEY not found in .env")
        return {"fields_schema": {}, "deals": []}
    
    # Step 1: Get field mapping (human name -> hash key)
    field_map = get_field_mapping()
    
    # Step 2: Fetch all deals (handle pagination)
    all_raw_deals = []
    start = 0
    while True:
        url = f"https://api.pipedrive.com/v1/deals?api_token={api_key}&start={start}&limit=500"
        try:
            response = requests.get(url)
            data = response.json()
            
            if data.get("success") and data.get("data"):
                all_raw_deals.extend(data["data"])
                
                # Check if there are more pages
                pagination = data.get("additional_data", {}).get("pagination", {})
                if pagination.get("more_items_in_collection"):
                    start = pagination.get("next_start", start + 500)
                else:
                    break
            else:
                break
        except Exception as e:
            print(f"Error fetching deals: {e}")
            break
    
    # Step 3: Normalize each deal using the field mapping
    deals = []
    for d in all_raw_deals:
        deal = {
            "deal_id": d.get(field_map.get("Deal ID", ""), d.get("id")),
            "title": d.get("title", ""),
            "official_owner": d.get(field_map.get("Official Owner", ""), None),
            "Lead_Owner": d.get(field_map.get("Lead Owner", ""), ""),
            "CRM_Status": d.get(field_map.get("CRM Status", ""), ""),
            "folder_name": d.get(field_map.get("Folder Name", ""), ""),
            "priority_tag": d.get(field_map.get("Priority Tag", ""), ""),
            "value_usd": d.get("value", 0)
        }
        deals.append(deal)
    
    # Step 4: Build dynamic schema
    fields_schema = {
        "deal_id": "Unique identifier for the deal",
        "title": "Name of the deal",
        "official_owner": "The built-in CRM owner field (often left blank)",
        "Lead_Owner": "Custom field where the team actually types the owner's name",
        "CRM_Status": "Custom CRM status (Active, Won, Lost, Closed)",
        "folder_name": "The folder the deal is placed in (In Progress, Negotiation, Dead Leads, etc.)",
        "priority_tag": "Custom tag for priority (High, Low, Critical, Urgent, etc.)",
        "value_usd": "Estimated deal value"
    }
    
    return {
        "fields_schema": fields_schema,
        "deals": deals
    }


@mcp.tool()
def get_crm_schema() -> str:
    """
    Returns the schema of the CRM, including field names, their descriptions, 
    and unique values for categorical fields to help understand the actual data structure.
    """
    data = load_data()
    schema = data.get("fields_schema", {})
    deals = data.get("deals", [])
    
    # Extract unique values for context
    unique_folders = list(set([d.get("folder_name") for d in deals if d.get("folder_name")]))
    unique_statuses = list(set([d.get("CRM_Status") for d in deals if d.get("CRM_Status")]))
    unique_lead_owners = list(set([d.get("Lead_Owner") for d in deals if d.get("Lead_Owner")]))
    unique_priorities = list(set([d.get("priority_tag") for d in deals if d.get("priority_tag")]))
    
    context = {
        "fields": schema,
        "unique_folders_found": unique_folders,
        "unique_statuses_found": unique_statuses,
        "unique_lead_owners_found": unique_lead_owners,
        "unique_priorities_found": unique_priorities,
        "total_records": len(deals)
    }
    
    return json.dumps(context, indent=2)


@mcp.tool()
def query_crm_deals(filters: dict, requesting_user_role: str = "admin") -> str:
    """
    Query CRM deals using dictionary filters. Use __not suffix for exclusion.
    Includes basic Role-Based Access Control (RBAC) and Fuzzy Semantic matching.
    """
    filters_dict = filters if filters else {}
        
    data = load_data()
    deals = data.get("deals", [])
    
    # 1. RBAC (Security Layer): Block non-admins from seeing High value deals
    authorized_deals = []
    for deal in deals:
        if requesting_user_role != "admin" and deal.get("value_usd", 0) > 100000:
            continue # Unauthorized
        authorized_deals.append(deal)
    
    filtered_deals = []
    for deal in authorized_deals:
        match = True
        for key, value in filters_dict.items():
            if key.endswith("__not"):
                actual_key = key.replace("__not", "")
                deal_val = str(deal.get(actual_key, "")).lower()
                query_val = str(value).lower()
                
                # Fuzzy semantic match for exclusion
                if fuzz.partial_ratio(query_val, deal_val) > 80:
                    match = False
                    break
            else:
                deal_val = str(deal.get(key, "")).lower()
                query_val = str(value).lower()
                
                # Fuzzy semantic match for inclusion
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
    # Start the MCP server using standard input/output (stdio)
    mcp.run()
