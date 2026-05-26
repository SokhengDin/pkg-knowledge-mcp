"""PyPI resolver: package name -> version + GitHub repo URL."""

from __future__ import annotations

import re
import httpx

_GITHUB_RE = re.compile(r"github\.com/([^/\s\"'>]+/[^/\s\"'>]+?)(?:\.git)?(?:[/#\s\"'>]|$)")

_SOURCE_KEYS = {"source", "source code", "repository", "code", "github", "homepage", "home"}


def _extract_github(urls: dict[str, str] | None, home_page: str | None) -> str | None:
    """Parse a GitHub owner/repo slug from PyPI project metadata."""
    candidates: list[str] = []

    if urls:
        for key, url in urls.items():
            if key.lower() in _SOURCE_KEYS:
                candidates.insert(0, url)  # source-like keys go first
            else:
                candidates.append(url)

    if home_page:
        candidates.append(home_page)

    for url in candidates:
        m = _GITHUB_RE.search(url)
        if m:
            slug = m.group(1).rstrip("./")
            parts = slug.split("/")
            if len(parts) >= 2:
                return f"{parts[0]}/{parts[1]}"

    return None


async def resolve_pypi(package: str, version: str | None = None) -> dict:
    """
    Resolve a PyPI package to its version and GitHub repo.

    Returns:
        {
            "name"       : str,
            "version"    : str,
            "github_repo": str | None,
            "home_page"  : str | None,
            "docs_url"   : str | None,
        }
    """
    url = f"https://pypi.org/pypi/{package}/{version}/json" if version else f"https://pypi.org/pypi/{package}/json"

    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.get(url, follow_redirects=True)
        resp.raise_for_status()

    data = resp.json()
    info = data["info"]
    github_repo = _extract_github(info.get("project_urls"), info.get("home_page"))

    return {
        "name"       : info["name"],
        "version"    : info["version"],
        "github_repo": github_repo,
        "home_page"  : info.get("home_page"),
        "docs_url"   : info.get("docs_url"),
    }
