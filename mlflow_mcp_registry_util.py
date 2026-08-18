import asyncio
from typing import Any

import mlflow

# Point at the same MLflow server your browser UI is connected to.
# Check the URL in your browser's address bar — commonly http://127.0.0.1:5000
mlflow.set_tracking_uri("http://127.0.0.1:5000")

async def register_postgresql_mcp_server():
    version = mlflow.genai.register_mcp_server(
        server_json={
            "name": "io.github.pavanjava/postgresql-server",
            "version": "0.1.0",
            "description": "PostgreSQL FastMCP server exposing DB tools",
            "remotes": [
                {"url": "http://localhost:8000/mcp", "type": "streamable-http"},
            ],
        },
        status="active",
        source="local dev server via fastmcp",
        create_access_endpoints_from_remotes=True,
    )
    print(f"Registered '{version.name}' version {version.version}")

async def register_qdrant_mcp_server():
    version = mlflow.genai.register_mcp_server(
        server_json={
            "name": "io.github.qdrant/mcp-server-qdrant",
            "version": "0.1.0",
            "description": "Qdrant MCP server exposing vector search tools",
            "packages": [
                {
                    "registryType": "pypi",
                    "identifier": "mcp-server-qdrant",
                    "version": "0.8.1",
                    "runtimeHint": "uvx",
                    "transport": {"type": "stdio"},
                    "environmentVariables": [
                        {"name": "QDRANT_URL", "description": "Qdrant endpoint URL", "isRequired": True, "isSecret": False},
                        {"name": "QDRANT_API_KEY", "description": "Qdrant API key", "isRequired": True, "isSecret": True},
                        {"name": "COLLECTION_NAME", "description": "Collection name", "default": "code"},
                        {"name": "EMBEDDING_MODEL", "description": "Embedding model", "default": "BAAI/bge-small-en-v1.5"},
                    ],
                }
            ],
        },
        status="active",
        source="local dev server via uvx mcp-server-qdrant",
    )

    print(f"Registered '{version.name}' version {version.version}")

async def discover_tools():
    server_version: Any = mlflow.genai.refresh_mcp_server_version_tools(
        name="io.github.pavanjava/postgresql-server",
        version="0.1.0",
    )
    for tool in server_version.tools:
        print(tool.name)

async def list_endpoints():
    # List all endpoints for a server
    endpoints = mlflow.genai.search_mcp_access_endpoints(
        server_name="io.github.pavanjava/postgresql-server",
    )

    for ep in endpoints:
        resolved = ep.resolved_version.version if ep.resolved_version else None
        print(f"  {ep.url} ({ep.transport_type}) → version {resolved}")

if __name__ == "__main__":
    # asyncio.run(register_mcp())
    asyncio.run(register_qdrant_mcp_server())
    # asyncio.run(discover_tools())
    # asyncio.run(list_endpoints())
