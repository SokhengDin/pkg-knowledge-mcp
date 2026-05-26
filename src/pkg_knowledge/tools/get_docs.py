"""get_docs tool: fetch the latest README / docs for a package."""

from __future__ import annotations

from typing import Literal

import httpx

from ..resolvers.pypi import resolve_pypi
from ..resolvers.npm import resolve_npm
from ..fetchers.github import fetch_readme
from ..fetchers.docs_site import fetch_docs_page
from ..processors.compress import extract_section, truncate_to_tokens
from ..skills.loader import get_skill


async def get_docs(
    package: str,
    ecosystem: Literal["python", "js"] = "python",
    version: str | None = None,
    section: str | None = None,
) -> str:
    """
    Fetch the latest README / docs for a package.

    Call this first before writing any code that uses a new or unfamiliar
    package version. Checks curated skills first, then falls back to live
    fetch from PyPI/npm and GitHub.

    Args:
        package:   Package name (e.g. "langchain", "fastmcp", "react").
        ecosystem: "python" (PyPI) or "js" (npm).
        version:   Specific version string. If None, fetches latest.
        section:   Optional section keyword to extract (e.g. "agents",
                   "installation", "quickstart"). If None, returns the full
                   README (may be large).

    Returns:
        Markdown string of the documentation content.
    """
    try:
        # 1. Check local skill first — faster and more focused than live fetch
        if not version:
            skill = get_skill(package)
            if skill:
                if section:
                    skill = extract_section(skill, section)
                return truncate_to_tokens(skill)

        # 2. Resolve version + GitHub repo from registry
        if ecosystem == "python":
            meta = await resolve_pypi(package, version)
        else:
            meta = await resolve_npm(package, version)

        resolved_version = meta["version"]
        github_repo = meta.get("github_repo")
        header = f"# {meta['name']} v{resolved_version}\n\n"

        # 3. Fetch README from GitHub raw
        content: str | None = None
        if github_repo:
            content = await fetch_readme(github_repo)

        # 4. Fallback: scrape official docs site
        if not content:
            docs_url = meta.get("docs_url") or meta.get("home_page")
            if docs_url:
                content = await fetch_docs_page(docs_url)

        if not content:
            return (
                header
                + f"[pkg-knowledge] Could not fetch documentation for '{package}' v{resolved_version}. "
                + (f"GitHub repo: {github_repo}. " if github_repo else "No GitHub repo found. ")
                + "Try supplying the docs URL manually."
            )

        # 5. Extract section if requested
        if section:
            content = extract_section(content, section)

        return header + truncate_to_tokens(content)

    except httpx.HTTPStatusError as e:
        return f"[pkg-knowledge error] HTTP {e.response.status_code} fetching docs for '{package}': {e.request.url}"
    except httpx.TimeoutException:
        return f"[pkg-knowledge error] Request timed out fetching docs for '{package}'"
    except Exception as e:
        return f"[pkg-knowledge error] Unexpected error fetching docs for '{package}': {type(e).__name__}: {e}"
