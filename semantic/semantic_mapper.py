# Semantic Mapper
# Uses LLM ONE TIME at startup to understand what each CRM field represents.
# This is the magic that makes the agent work with ANY CRM.

import os
import json
from openai import OpenAI
from typing import List, Dict


def create_semantic_map(field_names: List[str]) -> Dict[str, str]:
    """
    Given a list of CRM field names (e.g., ["Lead Owner", "Priority Tag", "CRM Status"]),
    asks the LLM ONCE to map them to universal semantic concepts.

    Returns:
      {
        "owner": "Lead Owner",
        "priority": "Priority Tag",
        "status": "CRM Status",
        "folder": "Folder Name",
        "organization": "org_name",
        "deal_name": "title",
        "deal_id": "Deal ID",
        "official_owner": "Official Owner",
        "value": "value"
      }
    """
    client = OpenAI(
        base_url="https://integrate.api.nvidia.com/v1",
        api_key=os.getenv("NVIDIA_API_KEY")
    )

    prompt = f"""You are a CRM schema analyst. Below is a list of all field names from a CRM system.

Field names:
{json.dumps(field_names, indent=2)}

Your job: Map each of these universal CRM concepts to the BEST matching field name from the list above.

Universal concepts to map:
1. "owner" — The person who owns/manages the deal (could be Lead Owner, Sales Rep, Account Manager, Assigned To, etc.)
2. "priority" — The urgency/importance of the deal (could be Priority, Priority Tag, Urgency, Criticality, etc.)
3. "status" — The current lifecycle status (could be CRM Status, Deal Status, Stage, Lifecycle, etc.)
4. "folder" — The pipeline folder/category (could be Folder Name, Pipeline, Stage Name, etc.)
5. "organization" — The company/org name (could be Organization, Company, Account, org_name, etc.)
6. "deal_name" — The title of the deal (could be Title, Deal Name, Name, Subject, etc.)
7. "deal_id" — A unique identifier (could be Deal ID, ID, Record ID, etc.)
8. "official_owner" — A secondary/official owner field if it exists (could be Official Owner, System Owner, etc.)
9. "value" — The monetary value (could be Value, Deal Value, Amount, Revenue, etc.)

IMPORTANT RULES:
- If a concept has no matching field, set it to null.
- Return ONLY valid JSON. No explanation, no markdown.
- Use the EXACT field name from the list (case-sensitive).

Return format:
{{"owner": "...", "priority": "...", "status": "...", "folder": "...", "organization": "...", "deal_name": "...", "deal_id": "...", "official_owner": "...", "value": "..."}}"""

    try:
        response = client.chat.completions.create(
            model="meta/llama-3.1-70b-instruct",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0
        )

        content = response.choices[0].message.content.strip()

        # Strip markdown code blocks if present
        if content.startswith("```"):
            content = content.split("\n", 1)[1]
            content = content.rsplit("```", 1)[0]
            content = content.strip()

        return json.loads(content)

    except Exception as e:
        print(f"[SemanticMapper] Error during LLM mapping: {e}")
        # Fallback: try common names
        return {
            "owner": "Lead Owner",
            "priority": "Priority Tag",
            "status": "CRM Status",
            "folder": "Folder Name",
            "organization": None,
            "deal_name": "title",
            "deal_id": "Deal ID",
            "official_owner": "Official Owner",
            "value": "value"
        }
