"""Official docs site scraper"""

from __future__ import annotations

import os
import httpx
from bs4 import BeautifulSoup
import markdownify

_TIMEOUT = float(os.getenv("REQUEST_TIMEOUT", "15"))

# Tags that typically contain main documentation content
_CONTENT_SELECTORS = [
    "article",
    "main",
    '[role="main"]',
    ".content",
    ".documentation",
    ".docs-content",
    "#content",
    "#main-content",
    ".markdown-body",   # GitHub rendered pages
    ".rst-content",     # ReadTheDocs
    ".theme-doc-markdown",  # Docusaurus
    ".md-content",      # MkDocs Material
]


async def fetch_docs_page(url: str) -> str | None:
    """
    Fetch an official docs page and convert it to clean Markdown.

    Tries common content selectors to extract the main documentation body.
    Falls back to the full <body> if none match.

    Args:
        url: Full URL of the docs page to scrape.

    Returns:
        Markdown string of the page content, or None if fetch fails.
    """
    headers = {
        "User-Agent": (
            "pkg-knowledge-mcp/0.1 "
            "(Claude Code documentation fetcher; "
            "https://github.com/sokhengdin/pkg-knowledge-mcp)"
        )
    }

    async with httpx.AsyncClient(timeout=_TIMEOUT, headers=headers, follow_redirects=True) as client:
        try:
            resp = await client.get(url)
            resp.raise_for_status()
        except (httpx.HTTPStatusError, httpx.RequestError):
            return None

    soup = BeautifulSoup(resp.text, "html.parser")

    # Remove noise elements
    for tag in soup.select("nav, header, footer, script, style, .sidebar, .toc, #sidebar"):
        tag.decompose()

    # Try content selectors in priority order
    content_el = None
    for selector in _CONTENT_SELECTORS:
        el = soup.select_one(selector)
        if el:
            content_el = el
            break

    if content_el is None:
        content_el = soup.body or soup

    raw_md = markdownify.markdownify(
        str(content_el),
        heading_style="ATX",
        bullets="-",
        strip=["img"],
    )

    # Clean up excessive blank lines
    lines = raw_md.splitlines()
    cleaned: list[str] = []
    blank_count = 0
    for line in lines:
        if line.strip() == "":
            blank_count += 1
            if blank_count <= 2:
                cleaned.append(line)
        else:
            blank_count = 0
            cleaned.append(line)

    return "\n".join(cleaned).strip()
