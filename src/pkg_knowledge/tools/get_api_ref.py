"""get_api_ref tool: fetch API reference for a specific class or function."""

from __future__ import annotations

from typing import Literal

import httpx

from ..resolvers.pypi import resolve_pypi
from ..resolvers.npm import resolve_npm
from ..fetchers.github import fetch_docs_dir, fetch_raw_file
from ..fetchers.docs_site import fetch_docs_page
from ..processors.compress import extract_section, truncate_to_tokens

# Known official API-reference doc URLs per ecosystem  (fallback)
_KNOWN_API_SITES: dict[str, str] = {
    "langchain": "https://api.python.langchain.com/en/latest/",
    "langchain-core": "https://api.python.langchain.com/en/latest/",
}


async def _search_docs_dir_for_symbol(
    github_repo: str,
    symbol: str,
    docs_path: str = "docs",
) -> str | None:
    """
    Walk the docs/ directory in the GitHub repo and look for .md files
    that mention the symbol name. Returns the first matching section.
    """
    try:
        entries = await fetch_docs_dir(github_repo, docs_path)
    except Exception:
        return None

    symbol_lower = symbol.lower()

    for entry in entries:
        if entry.get("type") == "dir":
            # Recurse one level into subdirectories
            sub_entries = await fetch_docs_dir(github_repo, entry["path"])
            entries.extend(sub_entries)
            continue

        download_url = entry.get("download_url")
        if not download_url:
            continue

        # Fetch the file and search for the symbol
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(download_url, follow_redirects=True)
                if resp.status_code != 200:
                    continue
                content = resp.text
        except Exception:
            continue

        if symbol_lower in content.lower():
            section = extract_section(content, symbol)
            if section and symbol_lower in section.lower():
                file_annotation = f"\n\n*Source: `{entry['path']}`*"
                return section + file_annotation

    return None


async def get_api_ref(
    package: str,
    symbol: str,
    ecosystem: Literal["python", "js"] = "python",
    version: str | None = None,
) -> str:
    """
    Fetch API reference for a specific class or function.

    Use this after get_docs() when you need precise signature, parameter,
    and return-type information for a specific symbol.

    Args:
        package:   Package name (e.g. "langchain", "fastmcp").
        symbol:    Class or function name to look up (e.g. "ChatOpenAI",
                   "RunnableSequence", "tool").
        ecosystem: "python" or "js".
        version:   Specific version. None = latest.

    Returns:
        Markdown string with the symbol's docstring, signature, and parameters.
    """
    try:
        # 1. Resolve metadata
        if ecosystem == "python":
            meta = await resolve_pypi(package, version)
        else:
            meta = await resolve_npm(package, version)

        resolved_version = meta["version"]
        github_repo = meta.get("github_repo")

        header = (
            f"# `{symbol}` — {meta['name']} v{resolved_version}\n\n"
        )

        content: str | None = None

        # 2. Search GitHub docs/ directory
        if github_repo:
            content = await _search_docs_dir_for_symbol(github_repo, symbol)

        # 3. Fallback: search README
        if not content and github_repo:
            from ..fetchers.github import fetch_readme
            readme = await fetch_readme(github_repo)
            if readme and symbol.lower() in readme.lower():
                content = extract_section(readme, symbol)

        # 4. Fallback: known API reference sites
        if not content:
            api_site = _KNOWN_API_SITES.get(package.lower())
            if api_site:
                # Construct a candidate URL for the symbol
                symbol_url = api_site + symbol.lower().replace(".", "/") + ".html"
                content = await fetch_docs_page(symbol_url)

        # 5. Fallback: official docs/home page with symbol search
        if not content:
            docs_url = meta.get("docs_url") or meta.get("home_page")
            if docs_url:
                page_content = await fetch_docs_page(docs_url)
                if page_content and symbol.lower() in page_content.lower():
                    content = extract_section(page_content, symbol)

        if not content:
            return (
                header
                + f"[pkg-knowledge] Could not find API reference for `{symbol}` "
                f"in '{package}' v{resolved_version}. "
                "Try get_docs() for the full README, or check the official docs site."
            )

        return header + truncate_to_tokens(content)

    except httpx.HTTPStatusError as e:
        return (
            f"[pkg-knowledge error] HTTP {e.response.status_code} "
            f"fetching API ref for '{package}.{symbol}': {e.request.url}"
        )
    except httpx.TimeoutException:
        return f"[pkg-knowledge error] Request timed out fetching API ref for '{package}.{symbol}'"
    except Exception as e:
        return f"[pkg-knowledge error] Unexpected error: {type(e).__name__}: {e}"
