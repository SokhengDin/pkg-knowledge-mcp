"""Integration tests for the four MCP tools."""

from __future__ import annotations

import pytest
from src.pkg_knowledge.tools import get_docs, get_changelog, get_api_ref, search_docs


@pytest.mark.asyncio
@pytest.mark.integration
async def test_get_docs_httpx():
    result = await get_docs("httpx", ecosystem="python")
    assert isinstance(result, str)
    assert "httpx" in result.lower()
    assert "[pkg-knowledge error]" not in result


@pytest.mark.asyncio
@pytest.mark.integration
async def test_get_docs_with_section():
    result = await get_docs("httpx", ecosystem="python", section="installation")
    assert isinstance(result, str)
    # Should contain install-related content
    assert "install" in result.lower() or "[pkg-knowledge]" in result


@pytest.mark.asyncio
@pytest.mark.integration
async def test_get_docs_js_react():
    result = await get_docs("react", ecosystem="js")
    assert isinstance(result, str)
    assert "[pkg-knowledge error]" not in result


@pytest.mark.asyncio
@pytest.mark.integration
async def test_get_docs_nonexistent_package():
    result = await get_docs("zzz-definitely-not-a-real-package-12345")
    assert isinstance(result, str)
    assert "[pkg-knowledge error]" in result or "[pkg-knowledge]" in result


@pytest.mark.asyncio
@pytest.mark.integration
async def test_get_changelog_httpx():
    result = await get_changelog("httpx", ecosystem="python")
    assert isinstance(result, str)
    # Should not raise, should return something about the changelog
    assert "httpx" in result.lower() or "Changelog" in result


@pytest.mark.asyncio
@pytest.mark.integration
async def test_get_changelog_version_range():
    result = await get_changelog("httpx", ecosystem="python", from_version="0.25.0", to_version="0.27.0")
    assert isinstance(result, str)
    assert "[pkg-knowledge error]" not in result


@pytest.mark.asyncio
@pytest.mark.integration
async def test_get_api_ref_httpx_client():
    result = await get_api_ref("httpx", symbol="Client", ecosystem="python")
    assert isinstance(result, str)
    assert "[pkg-knowledge error]" not in result


@pytest.mark.asyncio
@pytest.mark.integration
async def test_search_docs_httpx():
    result = await search_docs("httpx", query="async client", ecosystem="python")
    assert isinstance(result, str)
    assert "[pkg-knowledge error]" not in result


@pytest.mark.asyncio
@pytest.mark.integration
async def test_search_docs_no_results():
    result = await search_docs("httpx", query="zzznomatchxyzabc", ecosystem="python")
    assert isinstance(result, str)
    # Should gracefully say no results
    assert "No results" in result or "httpx" in result.lower()
