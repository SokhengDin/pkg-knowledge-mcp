"""npm resolver: package name -> version + GitHub repo URL."""

from __future__ import annotations

import re
import httpx

_GITHUB_RE = re.compile(r"github\.com/([^/\s\"'>]+/[^/\s\"'>]+?)(?:\.git)?(?:[/#\s\"'>]|$)")


def _extract_github(data: dict) -> str | None:
    """Parse a GitHub owner/repo slug from npm registry metadata."""
    repo = data.get("repository")
    if isinstance(repo, dict):
        url = repo.get("url", "")
        m = _GITHUB_RE.search(url)
        if m:
            slug = m.group(1).rstrip("./")
            parts = slug.split("/")
            if len(parts) >= 2:
                return f"{parts[0]}/{parts[1]}"
    elif isinstance(repo, str):
        if repo.startswith("github:"):
            repo = repo[7:]  # strip "github:" shorthand prefix
        if "/" in repo and not repo.startswith("http"):
            parts = repo.split("/")
            if len(parts) == 2:
                return repo

    homepage = data.get("homepage", "")
    if homepage:
        m = _GITHUB_RE.search(homepage)
        if m:
            slug = m.group(1).rstrip("./")
            parts = slug.split("/")
            if len(parts) >= 2:
                return f"{parts[0]}/{parts[1]}"

    bugs = data.get("bugs")
    if isinstance(bugs, dict):
        url = bugs.get("url", "")
        m = _GITHUB_RE.search(url)
        if m:
            slug = m.group(1).rstrip("./")
            parts = slug.split("/")
            if len(parts) >= 2:
                return f"{parts[0]}/{parts[1]}"

    return None


async def resolve_npm(package: str, version: str | None = None) -> dict:
    """
    Resolve an npm package to its version and GitHub repo.

    Returns:
        {
            "name"       : str,
            "version"    : str,
            "github_repo": str | None,
            "home_page"  : str | None,
            "docs_url"   : None,
        }
    """
    encoded = package.replace("@", "%40").replace("/", "%2F")  # encode scoped packages
    url = f"https://registry.npmjs.org/{encoded}"

    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.get(url, follow_redirects=True)
        resp.raise_for_status()

    data = resp.json()

    if version:
        resolved_version = version
        version_data = data.get("versions", {}).get(version, {})
    else:
        resolved_version = data.get("dist-tags", {}).get("latest", "")
        version_data = data.get("versions", {}).get(resolved_version, {})

    merged = {**data, **version_data}  # version-level metadata wins
    github_repo = _extract_github(merged)
    homepage = version_data.get("homepage") or data.get("homepage")

    return {
        "name"       : data.get("name", package),
        "version"    : resolved_version,
        "github_repo": github_repo,
        "home_page"  : homepage,
        "docs_url"   : None,
    }
