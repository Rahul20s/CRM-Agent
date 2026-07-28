# Agent — Fully Dynamic, Zero Hardcoding
# Uses modular LLM prompts, guardrails, and dynamic schema from MCP server.

import os
import json
import asyncio
import re
import ast
from openai import AsyncOpenAI
from dotenv import load_dotenv

# Import tools from the schema-driven MCP server
from mcp_server import query_crm_deals, get_crm_schema

# Import modular LLM components
from llm.guardrails import check_guardrails
from llm.prompts import build_system_prompt, build_tool_definition

load_dotenv()

# Initialize NVIDIA NIM OpenAI Client
client = AsyncOpenAI(
    base_url="https://integrate.api.nvidia.com/v1",
    api_key=os.getenv("NVIDIA_API_KEY")
)

MODEL_NAME = "meta/llama-3.1-70b-instruct"


async def ask_treelife_agent(user_question: str):
    """
    Main function that asks the LLM to answer the user's question using the CRM tools.
    Fully dynamic — zero hardcoded schemas or field names.
    """

    # 1. PRE-FLIGHT GUARDRAILS (Security Layer)
    guardrail_status = await check_guardrails(user_question)
    if "BLOCK" in guardrail_status.upper():
        return ("🛡️ **Guardrail Alert:** I am a CRM Data Assistant. "
                "I am restricted to querying and summarizing deal data. "
                "I cannot process this request.")

    # 2. Dynamically fetch the LIVE schema from the CRM (never hardcoded)
    crm_schema_text = get_crm_schema()

    # 3. Build system prompt and tool definitions from the prompts module
    system_prompt = build_system_prompt(crm_schema_text)
    tools = build_tool_definition()

    # 4. Send to LLM
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_question}
    ]

    try:
        response = await client.chat.completions.create(
            model=MODEL_NAME,
            messages=messages,
            tools=tools,
            tool_choice="auto"
        )

        message = response.choices[0].message

        # 5. NATIVE TOOL CALL
        if message.tool_calls:
            messages.append(message.model_dump(exclude_unset=True))

            for tool_call in message.tool_calls:
                if tool_call.function.name == "query_crm_deals":
                    args = json.loads(tool_call.function.arguments)
                    filters_val = args.get("filters", {})

                    if isinstance(filters_val, str):
                        try:
                            filters_dict = json.loads(filters_val)
                        except:
                            filters_dict = ast.literal_eval(filters_val)
                    else:
                        filters_dict = filters_val

                    # DIRECT CALL to schema-driven MCP tool
                    result_text = query_crm_deals(filters_dict)

                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": result_text
                    })

            final_response = await client.chat.completions.create(
                model=MODEL_NAME,
                messages=messages
            )
            return final_response.choices[0].message.content

        # 6. FALLBACK JSON PARSER
        elif message.content and "query_crm_deals" in message.content:
            try:
                match = re.search(r'\{.*\}', message.content, re.DOTALL)
                if match:
                    json_str = match.group(0)
                    try:
                        parsed = json.loads(json_str)
                    except:
                        parsed = ast.literal_eval(json_str)

                    if "parameters" in parsed and "filters" in parsed["parameters"]:
                        filters_val = parsed["parameters"]["filters"]

                        if isinstance(filters_val, str):
                            try:
                                filters_dict = json.loads(filters_val)
                            except:
                                filters_dict = ast.literal_eval(filters_val)
                        else:
                            filters_dict = filters_val

                        result_text = query_crm_deals(filters_dict)

                        messages.append({"role": "assistant", "content": message.content})
                        messages.append({
                            "role": "user",
                            "content": (
                                f"The database returned: {result_text}\n\n"
                                "Now, provide the final answer to my original question "
                                "and explain how you mapped the fields."
                            )
                        })

                        final_response = await client.chat.completions.create(
                            model=MODEL_NAME,
                            messages=messages
                        )
                        return final_response.choices[0].message.content
            except Exception as e:
                print("FALLBACK ERROR:", str(e))
                pass

        return message.content
    except Exception as e:
        return f"Error connecting to AI API: {str(e)}"


# For testing independently
if __name__ == "__main__":
    import sys
    question = "How many active deals does Garima own?"
    if len(sys.argv) > 1:
        question = sys.argv[1]
    print(f"Question: {question}\n")
    answer = asyncio.run(ask_treelife_agent(question))
    print(f"Answer:\n{answer}")
