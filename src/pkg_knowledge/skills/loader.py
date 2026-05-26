"""Skills loader: scan skills/ folder, load by package name."""

from __future__ import annotations

from pathlib import Path

SKILLS_DIR = Path(__file__).parent.parent.parent.parent / "skills"
CUSTOM_SKILLS_DIR = SKILLS_DIR / "custom"


def _normalize(package: str) -> str:
    """Normalize package name to a skill filename stem."""
    return package.lower().replace("@", "").replace("/", "-")  # "@scope/pkg" -> "scope-pkg"


def get_skill(package: str) -> str | None:
    """
    Return the curated skill .md for a package, or None if not found.

    Checks custom/ first so user overrides win over bundled skills.
    """
    normalized = _normalize(package)

    for directory in (CUSTOM_SKILLS_DIR, SKILLS_DIR):
        path = directory / f"{normalized}.md"
        if path.exists():
            return path.read_text(encoding="utf-8")

    return None


def list_skills() -> list[str]:
    """Return sorted list of package names that have a skill file."""
    if not SKILLS_DIR.exists():
        return []

    seen: set[str] = set()
    for directory in (CUSTOM_SKILLS_DIR, SKILLS_DIR):
        if directory.exists():
            for p in directory.glob("*.md"):
                seen.add(p.stem)

    return sorted(seen)
