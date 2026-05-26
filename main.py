"""pkg-knowledge-mcp: FastMCP server entrypoint."""

from __future__ import annotations

from dotenv import load_dotenv
from fastmcp import FastMCP
from src.pkg_knowledge.tools import get_docs, get_changelog, get_api_ref, search_docs
from src.pkg_knowledge.skills.loader import get_skill, list_skills

load_dotenv()

mcp = FastMCP(
    name="pkg-knowledge",
    instructions=(
        "Provides up-to-date documentation, changelogs, and API references "
        "for Python and JavaScript packages. Use get_docs() first for a general "
        "overview, then get_api_ref() for specific symbols, or get_changelog() "
        "when migrating between versions. Skills are checked first before live fetch."
    ),
    version="0.1.0",
)

mcp.add_tool(get_docs)
mcp.add_tool(get_changelog)
mcp.add_tool(get_api_ref)
mcp.add_tool(search_docs)


@mcp.resource("skill://{package}")
def skill_resource(package: str) -> str:
    """Load a curated skill .md for a package if one exists."""
    return get_skill(package) or f"[no skill for '{package}' — use get_docs() instead]"


@mcp.resource("skill://index")
def skill_index() -> str:
    """List all available curated skills."""
    skills = list_skills()
    if not skills:
        return "No skills available."
    return "Available skills:\n" + "\n".join(f"- {s}" for s in skills)


if __name__ == "__main__":
    mcp.run()