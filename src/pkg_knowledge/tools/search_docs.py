"""search_docs tool: keyword search across a package's docs."""

from __future__ import annotations

import asyncio
from typing import Literal

import httpx

from ..resolvers.pypi import resolve_pypi
from ..resolvers.npm import resolve_npm
from ..fetchers.github import fetch_docs_dir, fetch_raw_file, fetch_readme
from ..processors.compress import extract_section, truncate_to_tokens


def _score_content(content: str, query_tokens: list[str]) -> float:
    """
    Score a document by token overlap with the query.
    Returns a float between 0 and 1.
    """
    lower = content.lower()
    hits = sum(1 for t in query_tokens if t in lower)
    return hits / len(query_tokens) if query_tokens else 0.0


def _extract_matching_sections(
    content: str,
    query_tokens: list[str],
    file_path: str,
    max_sections: int = 3,
) -> list[dict]:
    """
    Return up to max_sections sections from content that contain query tokens,
    along with the file path.
    """
    import re
    heading_re = re.compile(r"^(#{1,6})\s+(.+)$", re.MULTILINE)
    lines = content.splitlines()
    headings = [(m.start(), m.group(0)) for m in heading_re.finditer(content)]

    results: list[dict] = []

    if headings:
        # Split into sections by heading
        sections: list[tuple[str, str]] = []
        for i, (pos, heading_line) in enumerate(headings):
            # Find the start line index
            char_count = 0
            start_line = 0
            for li, line in enumerate(lines):
                if char_count >= pos:
                    start_line = li
                    break
                char_count += len(line) + 1  # +1 for \n

            end_pos = headings[i + 1][0] if i + 1 < len(headings) else len(content)
            section_text = content[pos:end_pos].strip()
            sections.append((heading_line, section_text))

        for heading_line, section_text in sections:
            score = _score_content(section_text, query_tokens)
            if score > 0:
                results.append(
                    {
                        "file": file_path,
                        "heading": heading_line,
                        "content": section_text,
                        "score": score,
                    }
                )
    else:
        # No headings — treat whole file as one section
        score = _score_content(content, query_tokens)
        if score > 0:
            results.append(
                {
                    "file": file_path,
                    "heading": f"(no heading — {file_path})",
                    "content": content,
                    "score": score,
                }
            )

    # Sort by score descending and return top N
    results.sort(key=lambda x: x["score"], reverse=True)
    return results[:max_sections]


async def _fetch_file_content(download_url: str) -> str | None:
    """Fetch a file from a download URL."""
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(download_url, follow_redirects=True)
            if resp.status_code == 200:
                return resp.text
    except Exception:
        pass
    return None


async def search_docs(
    package: str,
    query: str,
    ecosystem: Literal["python", "js"] = "python",
    version: str | None = None,
    max_results: int = 5,
) -> str:
    """
    Search the docs of a package for a specific concept or keyword.

    Searches across the README and all Markdown files in the docs/ directory.
    Returns the top matching sections with source file annotations.

    Args:
        package:     Package name (e.g. "langchain", "fastmcp").
        query:       Search query (e.g. "streaming callbacks", "tool calling",
                     "async support").
        ecosystem:   "python" or "js".
        version:     Specific version. None = latest.
        max_results: Max number of matching sections to return (default 5).

    Returns:
        Markdown string of matching sections with source file annotations.
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
            f"# Search: \"{query}\" in {meta['name']} v{resolved_version}\n\n"
        )

        if not github_repo:
            return (
                header
                + f"[pkg-knowledge] No GitHub repo found for '{package}'. "
                "Cannot search docs."
            )

        # Tokenise query (simple word split, lowercase, filter short words)
        query_tokens = [t.lower() for t in query.split() if len(t) > 2]

        all_results: list[dict] = []

        # 2. Search README
        readme = await fetch_readme(github_repo)
        if readme:
            matches = _extract_matching_sections(readme, query_tokens, "README.md")
            all_results.extend(matches)

        # 3. Enumerate docs/ directory and search each file
        try:
            entries = await fetch_docs_dir(github_repo, "docs")
        except Exception:
            entries = []

        # Collect all file entries (flatten one sub-level)
        file_entries: list[dict] = []
        dir_entries: list[dict] = []
        for entry in entries:
            if entry.get("type") == "dir":
                dir_entries.append(entry)
            elif entry.get("download_url"):
                file_entries.append(entry)

        # Recurse into subdirectories (one level)
        sub_tasks = [fetch_docs_dir(github_repo, d["path"]) for d in dir_entries]
        if sub_tasks:
            sub_results = await asyncio.gather(*sub_tasks, return_exceptions=True)
            for result in sub_results:
                if isinstance(result, list):
                    for entry in result:
                        if entry.get("download_url"):
                            file_entries.append(entry)

        # Fetch and search each file (cap at 30 files to avoid rate limits)
        fetch_tasks = [
            _fetch_file_content(e["download_url"])
            for e in file_entries[:30]
        ]
        if fetch_tasks:
            file_contents = await asyncio.gather(*fetch_tasks, return_exceptions=True)
            for entry, content in zip(file_entries[:30], file_contents):
                if isinstance(content, str) and content:
                    matches = _extract_matching_sections(
                        content,
                        query_tokens,
                        entry.get("path", entry.get("name", "unknown")),
                    )
                    all_results.extend(matches)

        # 4. Rank globally and return top max_results
        all_results.sort(key=lambda x: x["score"], reverse=True)
        top_results = all_results[:max_results]

        if not top_results:
            return (
                header
                + f"[pkg-knowledge] No results found for query \"{query}\" "
                f"in {package} v{resolved_version}.\n\n"
                "Try different keywords, or use get_docs() to browse the full README."
            )

        # 5. Format output
        parts: list[str] = []
        for i, r in enumerate(top_results, 1):
            section_md = truncate_to_tokens(r["content"], max_tokens=800)
            parts.append(
                f"## Result {i} — `{r['file']}`\n\n"
                f"{section_md}\n\n"
                f"*Score: {r['score']:.2f} — Source: `{r['file']}`*"
            )

        return header + "\n\n---\n\n".join(parts)

    except httpx.HTTPStatusError as e:
        return (
            f"[pkg-knowledge error] HTTP {e.response.status_code} "
            f"searching docs for '{package}': {e.request.url}"
        )
    except httpx.TimeoutException:
        return f"[pkg-knowledge error] Request timed out searching docs for '{package}'"
    except Exception as e:
        return f"[pkg-knowledge error] Unexpected error: {type(e).__name__}: {e}"
