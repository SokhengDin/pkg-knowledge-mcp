"""get_changelog tool: fetch what changed between two versions."""

from __future__ import annotations

from typing import Literal

import httpx

from ..resolvers.pypi import resolve_pypi
from ..resolvers.npm import resolve_npm
from ..fetchers.github import fetch_changelog, fetch_releases
from ..processors.compress import filter_changelog_versions, truncate_to_tokens


def _releases_to_markdown(releases: list[dict]) -> str:
    """Convert GitHub Releases API response to a markdown changelog."""
    parts: list[str] = []
    for r in releases:
        tag = r.get("tag_name", "unknown")
        name = r.get("name") or tag
        date = r.get("published_at", "")[:10]  # YYYY-MM-DD
        body = (r.get("body") or "").strip()

        heading = f"## {name}"
        if date:
            heading += f" ({date})"
        parts.append(heading)
        if body:
            parts.append(body)
        parts.append("")  # blank line between entries

    return "\n".join(parts).strip()


async def get_changelog(
    package: str,
    ecosystem: Literal["python", "js"] = "python",
    from_version: str | None = None,
    to_version: str | None = None,
) -> str:
    """
    Fetch the changelog between two versions of a package.

    Critical for migration tasks — shows exactly what broke, what's new,
    and what was deprecated between your current version and the target.

    Args:
        package:      Package name (e.g. "langchain", "fastmcp").
        ecosystem:    "python" or "js".
        from_version: Starting version (inclusive). None = one version before latest.
        to_version:   Ending version (inclusive). None = latest stable.

    Returns:
        Markdown string of relevant changelog entries.
    """
    try:
        # 1. Resolve metadata
        if ecosystem == "python":
            meta = await resolve_pypi(package, to_version)
        else:
            meta = await resolve_npm(package, to_version)

        resolved_to = meta["version"]
        github_repo = meta.get("github_repo")

        header = (
            f"# {meta['name']} Changelog\n\n"
            f"Versions: {from_version or 'earliest'} -> {resolved_to}\n\n"
        )

        if not github_repo:
            return (
                header
                + f"[pkg-knowledge] No GitHub repo found for '{package}'. "
                "Cannot fetch changelog."
            )

        # 2. Try CHANGELOG.md first
        raw_changelog: str | None = await fetch_changelog(github_repo)
        changelog_source = "CHANGELOG.md"

        # 3. Fallback: GitHub Releases API
        if not raw_changelog:
            releases = await fetch_releases(github_repo, max_releases=50)
            if releases:
                raw_changelog = _releases_to_markdown(releases)
                changelog_source = "GitHub Releases"

        if not raw_changelog:
            return (
                header
                + f"[pkg-knowledge] No changelog found for '{package}'. "
                "The package may not maintain a CHANGELOG.md or GitHub Releases."
            )

        # 4. Filter to version range
        filtered = filter_changelog_versions(
            raw_changelog,
            from_version=from_version,
            to_version=resolved_to,
        )

        # 5. Truncate
        filtered = truncate_to_tokens(filtered)

        return header + f"*Source: {changelog_source}*\n\n" + filtered

    except httpx.HTTPStatusError as e:
        return (
            f"[pkg-knowledge error] HTTP {e.response.status_code} "
            f"fetching changelog for '{package}': {e.request.url}"
        )
    except httpx.TimeoutException:
        return f"[pkg-knowledge error] Request timed out fetching changelog for '{package}'"
    except Exception as e:
        return f"[pkg-knowledge error] Unexpected error fetching changelog for '{package}': {type(e).__name__}: {e}"
