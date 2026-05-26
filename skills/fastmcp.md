---
package: fastmcp
version_tested: 3.x
ecosystem: python
source: https://gofastmcp.com/docs
updated: 2025-05-26
---

# FastMCP v3 — What Claude Code Needs to Know

## Installation

```bash
pip install fastmcp        # or: uv add fastmcp
```

## Core Primitives

FastMCP v3 has three registerable primitives: **tools**, **resources**, and **prompts**.

### Tools — callable by the LLM

```python
from fastmcp import FastMCP

mcp = FastMCP(name="my-server")

@mcp.tool()
def add(a: int, b: int) -> int:
    """Add two numbers."""
    return a + b

@mcp.tool()
async def fetch_data(url: str) -> str:
    """Fetch data from a URL."""
    import httpx
    async with httpx.AsyncClient() as client:
        resp = await client.get(url)
        return resp.text
```

### Resources — data the LLM can read

```python
@mcp.resource("data://config")
def get_config() -> str:
    """Return server configuration."""
    return "key=value"

# Parameterised resource (URI template)
@mcp.resource("user://{user_id}/profile")
def get_user(user_id: str) -> str:
    return f"Profile for {user_id}"
```

### Prompts — reusable message templates

```python
from fastmcp.prompts import Message

@mcp.prompt()
def code_review_prompt(code: str, language: str = "python") -> list[Message]:
    return [
        Message(role="user", content=f"Review this {language} code:\n\n{code}")
    ]
```

## Running the Server

```python
# main.py
mcp = FastMCP(name="my-server")
# ... register tools/resources/prompts ...

if __name__ == "__main__":
    mcp.run()  # defaults to STDIO transport
```

```bash
fastmcp run main.py          # STDIO (for Claude Code)
fastmcp dev main.py          # dev mode with MCP Inspector UI
fastmcp install claude-code main.py  # install into Claude Code
```

## add_tool() vs @mcp.tool()

Both are equivalent — use `add_tool()` when the function is defined elsewhere:

```python
# Defined in a separate module
async def get_docs(package: str) -> str:
    ...

mcp.add_tool(get_docs)       # registers it as a tool
mcp.add_tool(get_docs, name="fetch_docs")  # override name
```

## Tool Return Types

Tools can return:
- `str` — rendered as text content (most common)
- `dict` / `list` — serialised as JSON
- `Image` — binary image content
- `None` — empty response

Always return `str` for MCP tools that feed LLM context.

## FastMCP v3 vs v2 Differences

| v2 | v3 |
|---|---|
| `@mcp.tool` (no parens) | `@mcp.tool()` (with parens) |
| `server.run()` | `mcp.run()` |
| Manual transport config | `mcp.run(transport="sse")` |
| `Context` injection | `from fastmcp import Context` in tool params |

## Context Injection

```python
from fastmcp import Context

@mcp.tool()
async def tool_with_context(query: str, ctx: Context) -> str:
    await ctx.info(f"Processing: {query}")  # send log message to client
    return "done"
```

## fastmcp.json Config

```json
{
  "$schema": "https://gofastmcp.com/public/schemas/fastmcp.json/v1.json",
  "source": {
    "path": "main.py",
    "entrypoint": "mcp"
  },
  "environment": {
    "dependencies": ["httpx", "beautifulsoup4"]
  }
}
```

## Key Gotchas

- The `mcp` object must be importable from `main.py` as the entrypoint
- Tool docstrings become the MCP tool description — write them for the LLM, not for humans
- Use `async def` for tools that do I/O; FastMCP handles the event loop
- `fastmcp install claude-code main.py` reads `fastmcp.json` for dependencies
- Resources are read-only; use tools for anything that has side effects
