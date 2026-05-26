"""Tests for the skills loader."""

from __future__ import annotations

from src.pkg_knowledge.skills.loader import get_skill, list_skills, SKILLS_DIR


class TestGetSkill:
    def test_langchain_skill_exists(self):
        skill = get_skill("langchain")
        assert skill is not None
        assert "LangChain" in skill
        assert "import" in skill.lower()

    def test_fastmcp_skill_exists(self):
        skill = get_skill("fastmcp")
        assert skill is not None
        assert "FastMCP" in skill

    def test_pydantic_v2_skill_exists(self):
        skill = get_skill("pydantic-v2")
        assert skill is not None
        assert "Pydantic" in skill

    def test_unknown_package_returns_none(self):
        assert get_skill("zzz-does-not-exist-12345") is None

    def test_scoped_npm_package_normalised(self):
        # "@scope/pkg" normalises to "scope-pkg"
        # We don't have that skill, but normalization should not crash
        result = get_skill("@scope/nonexistent")
        assert result is None

    def test_case_normalised(self):
        # "LangChain" -> "langchain"
        skill = get_skill("LangChain")
        assert skill is not None


class TestListSkills:
    def test_returns_list(self):
        skills = list_skills()
        assert isinstance(skills, list)

    def test_starter_skills_present(self):
        skills = list_skills()
        assert "langchain" in skills
        assert "fastmcp" in skills
        assert "pydantic-v2" in skills

    def test_sorted(self):
        skills = list_skills()
        assert skills == sorted(skills)
