"""GitHub fetcher: raw .md files and API endpoints."""

from __future__ import annotations

import os
import httpx

_GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
_AUTH_HEADERS = {"Authorization": f"token {_GITHUB_TOKEN}"} if _GITHUB_TOKEN else {}
_TIMEOUT = float(os.getenv("REQUEST_TIMEOUT", "15"))

# Common branch names to try when fetching raw files
_BRANCHES = ["main", "master", "develop", "dev"]

# Common README filenames
_README_NAMES = ["README.md", "readme.md", "Readme.md", "README.rst", "README.txt"]

# Common changelog filenames
_CHANGELOG_NAMES = [
    "CHANGELOG.md",
    "changelog.md",
    "CHANGES.md",
    "changes.md",
    "HISTORY.md",
    "history.md",
    "RELEASES.md",
    "releases.md",
]


async def fetch_raw_file(repo: str, path: str, ref: str | None = None) -> str | None:
    """
    Fetch a single raw file from GitHub.

    Args:
        repo: "owner/repo" slug.
        path: File path within the repo (e.g. "README.md", "docs/guide.md").
        ref:  Branch/tag/commit. If None, tries _BRANCHES in order.

    Returns:
        File content as a string, or None if not found.
    """
    refs_to_try = [ref] if ref else _BRANCHES

    async with httpx.AsyncClient(timeout=_TIMEOUT, headers=_AUTH_HEADERS) as client:
        for branch in refs_to_try:
            url = f"https://raw.githubusercontent.com/{repo}/refs/heads/{branch}/{path}"
            resp = await client.get(url, follow_redirects=True)
            if resp.status_code == 200:
                return resp.text

    return None


async def fetch_readme(repo: str, ref: str | None = None) -> str | None:
    """
    Fetch the README from a GitHub repo, trying common filenames and branches.

    Returns:
        README content as a string, or None if not found.
    """
    # First try the GitHub API to get the canonical README (respects any branch config)
    branches = [ref] if ref else _BRANCHES

    async with httpx.AsyncClient(timeout=_TIMEOUT, headers=_AUTH_HEADERS) as client:
        for branch in branches:
            # Try raw URLs for each README filename variant
            for name in _README_NAMES:
                url = f"https://raw.githubusercontent.com/{repo}/refs/heads/{branch}/{name}"
                resp = await client.get(url, follow_redirects=True)
                if resp.status_code == 200:
                    return resp.text

    return None


async def fetch_changelog(repo: str, ref: str | None = None) -> str | None:
    """
    Fetch CHANGELOG.md (or common variants) from a GitHub repo.

    Returns:
        Changelog content as a string, or None if not found.
    """
    branches = [ref] if ref else _BRANCHES

    async with httpx.AsyncClient(timeout=_TIMEOUT, headers=_AUTH_HEADERS) as client:
        for branch in branches:
            for name in _CHANGELOG_NAMES:
                url = f"https://raw.githubusercontent.com/{repo}/refs/heads/{branch}/{name}"
                resp = await client.get(url, follow_redirects=True)
                if resp.status_code == 200:
                    return resp.text

    return None


async def fetch_releases(repo: str, max_releases: int = 20) -> list[dict]:
    """
    Fetch GitHub Releases via the API.

    Args:
        repo: "owner/repo" slug.
        max_releases: Max number of releases to fetch.

    Returns:
        List of release dicts: [{"tag_name": str, "name": str, "body": str, "published_at": str}]
    """
    url = f"https://api.github.com/repos/{repo}/releases"
    headers = {**_AUTH_HEADERS, "Accept": "application/vnd.github+json"}

    async with httpx.AsyncClient(timeout=_TIMEOUT, headers=headers) as client:
        resp = await client.get(url, params={"per_page": max_releases}, follow_redirects=True)
        resp.raise_for_status()

    releases = resp.json()
    return [
        {
            "tag_name": r.get("tag_name", ""),
            "name": r.get("name", ""),
            "body": r.get("body", ""),
            "published_at": r.get("published_at", ""),
        }
        for r in releases
        if isinstance(r, dict)
    ]


async def fetch_docs_dir(repo: str, path: str = "docs", ref: str | None = None) -> list[dict]:
    """
    List files in a GitHub repo directory via the Contents API.

    Args:
        repo: "owner/repo" slug.
        path: Directory path (default "docs").
        ref:  Branch/tag. If None, uses GitHub's default branch.

    Returns:
        List of file dicts: [{"name": str, "path": str, "download_url": str}]
        Only includes files with a .md or .mdx extension.
    """
    url = f"https://api.github.com/repos/{repo}/contents/{path}"
    headers = {**_AUTH_HEADERS, "Accept": "application/vnd.github+json"}
    params = {"ref": ref} if ref else {}

    async with httpx.AsyncClient(timeout=_TIMEOUT, headers=headers) as client:
        resp = await client.get(url, params=params, follow_redirects=True)
        if resp.status_code == 404:
            return []
        resp.raise_for_status()

    items = resp.json()
    if not isinstance(items, list):
        return []

    results = []
    for item in items:
        if not isinstance(item, dict):
            continue
        name = item.get("name", "")
        if item.get("type") == "file" and (name.endswith(".md") or name.endswith(".mdx")):
            results.append(
                {
                    "name": name,
                    "path": item.get("path", ""),
                    "download_url": item.get("download_url", ""),
                }
            )
        elif item.get("type") == "dir":
            # Include dir entries so callers can recurse if desired
            results.append(
                {
                    "name": name,
                    "path": item.get("path", ""),
                    "download_url": None,
                    "type": "dir",
                }
            )

    return results
