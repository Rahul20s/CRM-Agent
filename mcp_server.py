from fastmcp import FastMCP
import json
import os

# Initialize FastMCP server
mcp = FastMCP("TreelifeCRM")

DATA_FILE = "crm_data.json"

def load_data():
    if not os.path.exists(DATA_FILE):
        return {"fields_schema": {}, "deals": []}
    with open(DATA_FILE, 'r') as f:
        return json.load(f)

@mcp.tool()
def get_crm_schema() -> str:
    """
    Returns the schema of the CRM, including field names, their descriptions, 
    and unique values for categorical fields like 'folder_name' or 'status' to help understand the actual data structure.
    """
    data = load_data()
    schema = data.get("fields_schema", {})
    deals = data.get("deals", [])
    
    # Extract unique values for context
    unique_folders = list(set([d.get("folder_name") for d in deals if d.get("folder_name")]))
    unique_statuses = list(set([d.get("status") for d in deals if d.get("status")]))
    unique_lead_owners = list(set([d.get("Lead_Owner") for d in deals if d.get("Lead_Owner")]))
    
    context = {
        "fields": schema,
        "unique_folders_found": unique_folders,
        "unique_statuses_found": unique_statuses,
        "unique_lead_owners_found": unique_lead_owners,
        "total_records": len(deals)
    }
    
    return json.dumps(context, indent=2)

from thefuzz import fuzz

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
