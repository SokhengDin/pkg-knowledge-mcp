"""Tests for GitHub fetcher and docs site scraper."""

from __future__ import annotations

import pytest
from src.pkg_knowledge.fetchers.github import (
    fetch_readme,
    fetch_changelog,
    fetch_releases,
    fetch_docs_dir,
    fetch_raw_file,
)


@pytest.mark.asyncio
@pytest.mark.integration
async def test_fetch_readme_httpx():
    content = await fetch_readme("encode/httpx")
    assert content is not None
    assert len(content) > 100
    assert "httpx" in content.lower()


@pytest.mark.asyncio
@pytest.mark.integration
async def test_fetch_readme_missing_repo():
    content = await fetch_readme("this-does-not-exist/definitely-not-real-12345")
    assert content is None


@pytest.mark.asyncio
@pytest.mark.integration
async def test_fetch_changelog_httpx():
    # httpx keeps a CHANGELOG.md
    content = await fetch_changelog("encode/httpx")
    assert content is not None
    assert len(content) > 50


@pytest.mark.asyncio
@pytest.mark.integration
async def test_fetch_releases_httpx():
    releases = await fetch_releases("encode/httpx", max_releases=5)
    assert isinstance(releases, list)
    assert len(releases) > 0
    first = releases[0]
    assert "tag_name" in first
    assert "body" in first


@pytest.mark.asyncio
@pytest.mark.integration
async def test_fetch_docs_dir_fastmcp():
    # FastMCP may have a docs/ directory
    entries = await fetch_docs_dir("jlowin/fastmcp", "docs")
    # May be empty if no docs/ dir — just verify it doesn't raise
    assert isinstance(entries, list)


@pytest.mark.asyncio
@pytest.mark.integration
async def test_fetch_raw_file():
    content = await fetch_raw_file("encode/httpx", "README.md")
    assert content is not None
    assert "httpx" in content.lower()
