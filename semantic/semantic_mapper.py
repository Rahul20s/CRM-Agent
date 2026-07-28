# Semantic Mapper
# Uses LLM ONE TIME at startup to understand what each CRM field represents.
# This is the magic that makes the agent work with ANY CRM.
# CRITICAL: Prioritizes CUSTOM fields over built-in fields.

import os
import json
from openai import OpenAI
from typing import List, Dict


def create_semantic_map(custom_fields: List[str], builtin_fields: List[str]) -> Dict[str, str]:
    """
    Given two lists of CRM field names (custom and built-in),
    asks the LLM ONCE to map them to universal semantic concepts.
    Custom fields are ALWAYS prioritized over built-in fields.

    Returns:
      {
        "owner": "Lead Owner",
        "priority": "Priority Tag",
        "status": "CRM Status",
        "folder": "Folder Name",
        ...
      }
    """
    client = OpenAI(
        base_url="https://integrate.api.nvidia.com/v1",
        api_key=os.getenv("NVIDIA_API_KEY")
    )

    prompt = f"""You are a CRM schema analyst. A company has a CRM with two types of fields:

CUSTOM FIELDS (created by the team — ALWAYS prefer these over built-in fields):
{json.dumps(custom_fields, indent=2)}

BUILT-IN FIELDS (system defaults — only use these if no custom field matches):
{json.dumps(builtin_fields, indent=2)}

Your job: Map each universal concept below to the BEST matching field name.

CRITICAL RULE: If a custom field matches a concept, you MUST choose the custom field, NOT the built-in one. For example, if custom fields include "Lead Owner" and built-in fields include "Owner", you MUST choose "Lead Owner".

Universal concepts to map:
1. "owner" — The person who owns/manages the deal (e.g., Lead Owner, Sales Rep, Account Manager, Assigned To)
2. "priority" — The urgency/importance (e.g., Priority Tag, Urgency, Criticality)
3. "status" — The lifecycle status (e.g., CRM Status, Deal Status, Stage, Lifecycle)
4. "folder" — The pipeline folder/category (e.g., Folder Name, Pipeline, Stage Name)
5. "organization" — The company/org name (e.g., Organization, Company, Account)
6. "deal_name" — The title of the deal (e.g., Title, Deal Name, Name)
7. "deal_id" — A unique identifier (e.g., Deal ID, ID, Record ID)
8. "official_owner" — A secondary/official owner field if it exists (e.g., Official Owner, System Owner)
9. "value" — The monetary value (e.g., Value, Deal Value, Amount)

RULES:
- ALWAYS prefer custom fields over built-in fields.
- If a concept has no matching field at all, set it to null.
- Return ONLY valid JSON. No explanation, no markdown, no code blocks.
- Use the EXACT field name from the lists above (case-sensitive).

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

        result = json.loads(content)
        print(f"[SemanticMapper] LLM returned: {json.dumps(result, indent=2)}")
        return result

    except Exception as e:
        print(f"[SemanticMapper] Error during LLM mapping: {e}")
        print("[SemanticMapper] Using fallback mapping based on common custom field names.")

        # Intelligent fallback: try to find custom fields by common patterns
        fallback = {
            "owner": None,
            "priority": None,
            "status": None,
            "folder": None,
            "organization": "Organization",
            "deal_name": "Title",
            "deal_id": None,
            "official_owner": None,
            "value": "Value"
        }

        # Try to match custom fields to concepts
        owner_keywords = ["lead owner", "sales rep", "account manager", "assigned to", "owner"]
        priority_keywords = ["priority", "urgency", "criticality", "importance"]
        status_keywords = ["crm status", "deal status", "status", "lifecycle", "stage"]
        folder_keywords = ["folder", "pipeline", "stage name", "category"]
        id_keywords = ["deal id", "record id", "id"]
        official_keywords = ["official owner", "system owner"]

        for field in custom_fields:
            fl = field.lower()
            if any(k in fl for k in owner_keywords) and fallback["owner"] is None:
                fallback["owner"] = field
            elif any(k in fl for k in priority_keywords) and fallback["priority"] is None:
                fallback["priority"] = field
            elif any(k in fl for k in status_keywords) and fallback["status"] is None:
                fallback["status"] = field
            elif any(k in fl for k in folder_keywords) and fallback["folder"] is None:
                fallback["folder"] = field
            elif any(k in fl for k in id_keywords) and fallback["deal_id"] is None:
                fallback["deal_id"] = field
            elif any(k in fl for k in official_keywords) and fallback["official_owner"] is None:
                fallback["official_owner"] = field

        print(f"[SemanticMapper] Fallback mapping: {json.dumps(fallback, indent=2)}")
        return fallback
