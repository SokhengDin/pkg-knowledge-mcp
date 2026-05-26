"""Text processors: section extraction, token truncation, changelog filtering."""

from __future__ import annotations

import os
import re
from packaging.version import Version, InvalidVersion

_DEFAULT_MAX_TOKENS = int(os.getenv("DEFAULT_MAX_TOKENS", "4000"))

# Match Markdown headings: # / ## / ### / #### ...
_HEADING_RE = re.compile(r"^(#{1,6})\s+(.+)$", re.MULTILINE)

# Match version-like strings in headings (e.g. "1.2.3", "v1.2.3", "[1.2.3]")
_VERSION_IN_HEADING_RE = re.compile(
    r"v?(\d+\.\d+(?:\.\d+)?(?:[._-]?(?:alpha|beta|rc|pre|dev|post)\d*)?)"
)


# ---------------------------------------------------------------------------
# Section extraction
# ---------------------------------------------------------------------------


def extract_section(markdown: str, section_keyword: str) -> str:
    """
    Find and return the heading + body that best matches *section_keyword*.

    Strategy:
    1. Walk headings in order. Score each by keyword overlap with the heading text.
    2. Return the first heading whose normalised text contains the keyword,
       plus all content until the next heading of the same or higher level.
    3. If no heading matches, fall back to returning paragraphs that contain
       the keyword (up to a reasonable character limit).

    Args:
        markdown:        Full markdown content.
        section_keyword: Keyword(s) to search for (case-insensitive).

    Returns:
        Matched section as a markdown string, or the full markdown if no match.
    """
    keyword = section_keyword.lower().strip()
    lines = markdown.splitlines()

    # Build a list of (line_index, level, heading_text) for all headings
    heading_positions: list[tuple[int, int, str]] = []
    for i, line in enumerate(lines):
        m = _HEADING_RE.match(line)
        if m:
            level = len(m.group(1))
            text = m.group(2).strip()
            heading_positions.append((i, level, text))

    # Find best matching heading
    best_idx: int | None = None
    for pos_idx, (line_i, level, text) in enumerate(heading_positions):
        # Exact keyword match wins
        if keyword in text.lower():
            best_idx = pos_idx
            break
        # Word-level overlap fallback
        kw_words = set(keyword.split())
        heading_words = set(text.lower().split())
        if kw_words & heading_words:
            best_idx = pos_idx
            # Don't break — keep looking for a better (exact) match

    if best_idx is not None:
        start_line, match_level, _ = heading_positions[best_idx]

        # Find the end: next heading of same or higher level
        end_line = len(lines)
        for line_i, level, _ in heading_positions[best_idx + 1 :]:
            if level <= match_level:
                end_line = line_i
                break

        return "\n".join(lines[start_line:end_line]).strip()

    # Fallback: return paragraphs containing the keyword
    paragraphs = re.split(r"\n{2,}", markdown)
    matching = [p for p in paragraphs if keyword in p.lower()]
    if matching:
        return "\n\n".join(matching[:5])  # up to 5 matching paragraphs

    # Nothing matched — return full content (caller should truncate)
    return markdown


# ---------------------------------------------------------------------------
# Token truncation
# ---------------------------------------------------------------------------


def truncate_to_tokens(text: str, max_tokens: int | None = None) -> str:
    """
    Trim *text* to approximately *max_tokens* tokens.

    Uses the rough heuristic: 1 token ≈ 4 characters.
    Trims from the end, but tries to preserve heading structure by not
    cutting in the middle of a heading line.

    Args:
        text:       Input text.
        max_tokens: Max tokens. Defaults to DEFAULT_MAX_TOKENS env var (4000).

    Returns:
        Possibly truncated string.
    """
    if max_tokens is None:
        max_tokens = _DEFAULT_MAX_TOKENS

    max_chars = max_tokens * 4

    if len(text) <= max_chars:
        return text

    # Find a good cut point near max_chars (end of a line)
    cut = text.rfind("\n", 0, max_chars)
    if cut == -1:
        cut = max_chars

    truncated = text[:cut].rstrip()
    return truncated + f"\n\n*[Content truncated at ~{max_tokens} tokens]*"


# ---------------------------------------------------------------------------
# Changelog version filtering
# ---------------------------------------------------------------------------


def _parse_version_safe(v: str) -> Version | None:
    try:
        return Version(v)
    except InvalidVersion:
        return None


def filter_changelog_versions(
    markdown: str,
    from_version: str | None = None,
    to_version: str | None = None,
) -> str:
    """
    Extract changelog sections that fall within [from_version, to_version].

    Sections are identified by headings that contain a version string.
    Both bounds are *inclusive*.

    Args:
        markdown:     Full changelog content.
        from_version: Lower bound (inclusive). None = return from the oldest found.
        to_version:   Upper bound (inclusive). None = return up to the newest found.

    Returns:
        Filtered markdown string, or the original if no version headings found.
    """
    from_ver = _parse_version_safe(from_version) if from_version else None
    to_ver = _parse_version_safe(to_version) if to_version else None

    lines = markdown.splitlines()
    heading_positions: list[tuple[int, int, str, Version | None]] = []

    for i, line in enumerate(lines):
        m = _HEADING_RE.match(line)
        if m:
            level = len(m.group(1))
            text = m.group(2).strip()
            vm = _VERSION_IN_HEADING_RE.search(text)
            ver = _parse_version_safe(vm.group(1)) if vm else None
            heading_positions.append((i, level, text, ver))

    # Filter to headings that have version info and are in range
    version_headings = [h for h in heading_positions if h[3] is not None]

    if not version_headings:
        # No version headings found — return full changelog (truncated)
        return truncate_to_tokens(markdown)

    selected_ranges: list[tuple[int, int]] = []

    for idx, (line_i, level, text, ver) in enumerate(version_headings):
        assert ver is not None  # narrowed above

        # Check bounds
        if from_ver and ver < from_ver:
            continue
        if to_ver and ver > to_ver:
            continue

        # Find end of this section
        end_line = len(lines)
        for next_line_i, next_level, _, _ in version_headings[idx + 1 :]:
            if next_level <= level:
                end_line = next_line_i
                break

        selected_ranges.append((line_i, end_line))

    if not selected_ranges:
        return f"[pkg-knowledge] No changelog entries found between {from_version} and {to_version}."

    # Merge adjacent/overlapping ranges and build result
    selected_ranges.sort()
    merged: list[tuple[int, int]] = []
    for start, end in selected_ranges:
        if merged and start <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(merged[-1][1], end))
        else:
            merged.append((start, end))

    parts = ["\n".join(lines[s:e]).strip() for s, e in merged]
    return "\n\n---\n\n".join(parts)
