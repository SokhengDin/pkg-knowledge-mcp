"""Tests for PyPI and npm resolvers."""

from __future__ import annotations

import pytest
from src.pkg_knowledge.resolvers.pypi import resolve_pypi, _extract_github
from src.pkg_knowledge.resolvers.npm import resolve_npm


# ---------------------------------------------------------------------------
# Unit tests (no network)
# ---------------------------------------------------------------------------


class TestExtractGithubPyPI:
    def test_source_key_wins(self):
        urls = {
            "Source": "https://github.com/owner/repo",
            "Homepage": "https://example.com",
        }
        assert _extract_github(urls, None) == "owner/repo"

    def test_homepage_fallback(self):
        assert _extract_github(None, "https://github.com/owner/mylib") == "owner/mylib"

    def test_git_suffix_stripped(self):
        assert _extract_github(None, "https://github.com/owner/repo.git") == "owner/repo"

    def test_no_github_url(self):
        assert _extract_github({"Homepage": "https://example.com"}, None) is None

    def test_none_inputs(self):
        assert _extract_github(None, None) is None

    def test_url_with_trailing_slash(self):
        assert _extract_github(None, "https://github.com/owner/repo/") == "owner/repo"


# ---------------------------------------------------------------------------
# Integration tests (live network — mark as integration)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.integration
async def test_resolve_pypi_httpx():
    """httpx should resolve to a valid version and GitHub repo."""
    result = await resolve_pypi("httpx")
    assert result["name"].lower() == "httpx"
    assert result["version"]
    assert result["github_repo"]
    assert "encode" in result["github_repo"].lower() or "httpx" in result["github_repo"].lower()


@pytest.mark.asyncio
@pytest.mark.integration
async def test_resolve_pypi_latest_fastmcp():
    result = await resolve_pypi("fastmcp")
    assert result["version"]
    assert result["github_repo"]


@pytest.mark.asyncio
@pytest.mark.integration
async def test_resolve_pypi_specific_version():
    result = await resolve_pypi("httpx", version="0.27.0")
    assert result["version"] == "0.27.0"


@pytest.mark.asyncio
@pytest.mark.integration
async def test_resolve_npm_react():
    result = await resolve_npm("react")
    assert result["name"] == "react"
    assert result["version"]
    assert result["github_repo"]
    assert "facebook" in result["github_repo"].lower() or "react" in result["github_repo"].lower()


@pytest.mark.asyncio
@pytest.mark.integration
async def test_resolve_npm_zod():
    result = await resolve_npm("zod")
    assert result["name"] == "zod"
    assert result["version"]
    assert result["github_repo"]
