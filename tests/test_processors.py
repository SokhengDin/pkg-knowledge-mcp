"""Tests for compress processors."""

from __future__ import annotations

import pytest
from src.pkg_knowledge.processors.compress import (
    extract_section,
    truncate_to_tokens,
    filter_changelog_versions,
)

SAMPLE_MD = """\
# My Package

Some intro text.

## Installation

Run `pip install mypackage`.

## Quickstart

Here is how to get started:

```python
from mypackage import Client
client = Client()
```

## API Reference

### Client

The main client class.

#### Client.connect

Connect to the server.

## Contributing

See CONTRIBUTING.md.
"""

SAMPLE_CHANGELOG = """\
# Changelog

## 2.0.0 (2024-01-15)

### Breaking Changes
- Removed deprecated `old_method()`

### New Features
- Added async support

## 1.5.0 (2023-11-01)

### New Features
- Added streaming

## 1.0.0 (2023-06-01)

Initial release.
"""


class TestExtractSection:
    def test_exact_heading_match(self):
        result = extract_section(SAMPLE_MD, "Installation")
        assert "pip install" in result
        assert "Quickstart" not in result  # should not bleed into next section

    def test_case_insensitive(self):
        result = extract_section(SAMPLE_MD, "installation")
        assert "pip install" in result

    def test_nested_heading(self):
        result = extract_section(SAMPLE_MD, "Client")
        assert "main client class" in result.lower() or "Client" in result

    def test_no_match_returns_paragraphs_or_full(self):
        result = extract_section(SAMPLE_MD, "zzznomatch")
        # Should return something (full content fallback)
        assert len(result) > 0

    def test_quickstart_section(self):
        result = extract_section(SAMPLE_MD, "quickstart")
        assert "Client()" in result


class TestTruncateToTokens:
    def test_short_content_unchanged(self):
        text = "Hello world"
        assert truncate_to_tokens(text, max_tokens=1000) == text

    def test_long_content_truncated(self):
        text = "a" * 20000  # ~5000 tokens
        result = truncate_to_tokens(text, max_tokens=1000)
        assert len(result) < len(text)
        assert "truncated" in result

    def test_exact_limit_unchanged(self):
        text = "a" * 4000  # exactly 1000 tokens
        assert truncate_to_tokens(text, max_tokens=1000) == text

    def test_truncation_note_appended(self):
        text = "x " * 10000
        result = truncate_to_tokens(text, max_tokens=100)
        assert "[Content truncated" in result


class TestFilterChangelogVersions:
    def test_filter_to_range(self):
        result = filter_changelog_versions(SAMPLE_CHANGELOG, "1.5.0", "2.0.0")
        assert "2.0.0" in result
        assert "1.5.0" in result
        assert "1.0.0" not in result

    def test_upper_bound_only(self):
        result = filter_changelog_versions(SAMPLE_CHANGELOG, None, "1.5.0")
        assert "1.5.0" in result
        assert "1.0.0" in result
        assert "2.0.0" not in result

    def test_lower_bound_only(self):
        result = filter_changelog_versions(SAMPLE_CHANGELOG, "1.5.0", None)
        assert "2.0.0" in result
        assert "1.5.0" in result

    def test_no_results_in_range(self):
        result = filter_changelog_versions(SAMPLE_CHANGELOG, "3.0.0", "4.0.0")
        assert "No changelog entries found" in result

    def test_no_bounds_returns_content(self):
        result = filter_changelog_versions(SAMPLE_CHANGELOG)
        # Should return all versions
        assert "2.0.0" in result
        assert "1.0.0" in result
