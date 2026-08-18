from fastmcp import FastMCP

mcp = FastMCP("My MCP Server")

@mcp.tool(
    name="Greeting",
    description="Greets the incoming message",
    title="Greeting",
)
def greet(name: str) -> str:
    return f"Hello, {name}!"

@mcp.tool(
    name="Sendoff",
    description="Sendoff the incoming message",
    title="Sendoff",
)
def bye(name: str) -> str:
    return f"Bye, {name}!"


if __name__ == "__main__":
    mcp.run(transport="http", port=8000)