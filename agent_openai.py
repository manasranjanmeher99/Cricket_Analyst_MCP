"""
agent_openai.py
---------------
GPT-powered agent for the Cricket Analyst MCP server.

The agent discovers the MCP tools at runtime, gives their JSON schemas to
OpenAI, executes requested tools through MCP, and returns the final answer.

Usage:
    set OPENAI_API_KEY=sk-...
    python agent_openai.py "Compare Virat Kohli and Rohit Sharma in ODI cricket."

Optional:
    set OPENAI_MODEL=gpt-5.6
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
from typing import Any

from dotenv import load_dotenv
from openai import OpenAI
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client, get_default_environment

# Load OPENAI_API_KEY / OPENAI_MODEL from a local .env file, if present.
# Without this, a .env file created per the README is silently ignored and
# os.environ.get("OPENAI_API_KEY") below will still be None.
load_dotenv()

MODEL = os.environ.get("OPENAI_MODEL", "gpt-5.6")
MAX_TOOL_TURNS = 8


def mcp_tool_to_openai_schema(mcp_tool: Any) -> dict:
    """Convert an MCP tool definition to the OpenAI Responses API schema."""
    return {
        "type": "function",
        "name": mcp_tool.name,
        "description": mcp_tool.description or "",
        "parameters": mcp_tool.inputSchema or {"type": "object", "properties": {}},
        "strict": False,
    }


def result_to_text(result: Any) -> str:
    """Extract text from an MCP CallToolResult safely."""
    parts = []
    for content in getattr(result, "content", []) or []:
        text = getattr(content, "text", None)
        if text is not None:
            parts.append(text)
        else:
            parts.append(str(content))
    return "\n".join(parts) or "{}"


async def run_agent(user_question: str) -> str:
    """Run one GPT agent turn-loop against the local MCP server."""
    if not os.environ.get("OPENAI_API_KEY"):
        raise RuntimeError(
            "OPENAI_API_KEY is not set. Add your OpenAI API key to the environment "
            "or create a .env file from .env.example."
        )

    # sys.executable fixes Windows/virtual-environment issues caused by using
    # the Unix-only `python3` command.
    server_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "server.py")

    # The MCP SDK only forwards a small safe subset of env vars (PATH, HOME,
    # etc.) to the spawned server.py subprocess by default - it does NOT
    # inherit CRICAPI_KEY, even if it's set here via .env. Without this,
    # server.py silently falls back to mock data even when a live API key is
    # configured. Forward it explicitly (and nothing else sensitive).
    server_env = get_default_environment()
    if os.environ.get("CRICAPI_KEY"):
        server_env["CRICAPI_KEY"] = os.environ["CRICAPI_KEY"]

    params = StdioServerParameters(command=sys.executable, args=[server_path], env=server_env)
    client = OpenAI()

    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            mcp_tools = (await session.list_tools()).tools
            openai_tools = [mcp_tool_to_openai_schema(t) for t in mcp_tools]

            # Responses API input is kept locally so tool outputs can be fed
            # back to the model without depending on deprecated APIs.
            conversation: list[dict] = [
                {"role": "user", "content": user_question}
            ]

            for _ in range(MAX_TOOL_TURNS):
                response = client.responses.create(
                    model=MODEL,
                    input=conversation,
                    tools=openai_tools,
                    tool_choice="auto",
                )

                function_calls = [
                    item for item in response.output
                    if getattr(item, "type", None) == "function_call"
                ]

                if not function_calls:
                    return response.output_text or "No answer was returned by the model."

                # Preserve the model's output items so the next request has the
                # complete tool-call context.
                conversation.extend(item.model_dump(exclude_none=True) for item in response.output)

                for call in function_calls:
                    try:
                        args = json.loads(call.arguments or "{}")
                    except json.JSONDecodeError as exc:
                        tool_output = json.dumps({"error": f"Invalid tool arguments: {exc}"})
                    else:
                        try:
                            result = await session.call_tool(call.name, args)
                            tool_output = result_to_text(result)
                        except Exception as exc:
                            tool_output = json.dumps({"error": f"MCP tool failed: {exc}"})

                    conversation.append(
                        {
                            "type": "function_call_output",
                            "call_id": call.call_id,
                            "output": tool_output,
                        }
                    )

            return "Reached the maximum number of MCP tool-call turns."


if __name__ == "__main__":
    question = " ".join(sys.argv[1:]).strip()
    question = question or "Compare Virat Kohli and Rohit Sharma in ODI cricket."
    try:
        answer = asyncio.run(run_agent(question))
        print(answer)
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        raise SystemExit(1)
