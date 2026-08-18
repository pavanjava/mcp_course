import asyncio
from typing import Any
import json

from fastmcp import Client

client = Client("http://localhost:8000/mcp")

async def call_tool(tool_name: str):
    async with client:
        tool_result: Any = await client.call_tool(name=tool_name)
        for tool in tool_result.content:
            for obj in json.loads(tool.text):
                print(obj['database'])


asyncio.run(call_tool("ListDatabases"))