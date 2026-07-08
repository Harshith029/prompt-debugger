"""Skill frontmatter contract: naming rules, reserved words, and the permission profile.

Enforces Claude Code's documented constraints plus this project's corrected permission
model (review F4): analyze/rewrite/pd remove write/execute tools via disallowed-tools;
history is user-invocable only.
"""

from __future__ import annotations

import re
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SKILLS = REPO / "adapters" / "claude-code" / "skills"

RESERVED = ("anthropic", "claude")
NAME_RE = re.compile(r"^[a-z0-9-]{1,64}$")

# The documented permission profile (contract-tested; drift fails CI — S13).
PROFILE = {
    "analyze": {"disallowed": {"Write", "Edit", "NotebookEdit", "Bash"}, "model_invocable": True},
    "rewrite": {"disallowed": {"Write", "Edit", "NotebookEdit", "Bash"}, "model_invocable": True},
    "pd": {"disallowed": {"Write", "Edit", "NotebookEdit", "Bash"}, "model_invocable": True},
    "history": {"disallowed": set(), "model_invocable": False},
}


def _parse_frontmatter(md: Path) -> dict[str, str]:
    text = md.read_text(encoding="utf-8")
    assert text.startswith("---\n"), f"{md}: missing frontmatter"
    end = text.index("\n---", 4)
    block = text[4:end]
    fields: dict[str, str] = {}
    current_key: str | None = None
    for line in block.splitlines():
        if re.match(r"^[a-zA-Z0-9_-]+:", line):
            key, _, val = line.partition(":")
            current_key = key.strip()
            fields[current_key] = val.strip()
        elif current_key and line.strip():
            fields[current_key] += " " + line.strip()
    return fields


def _skill_files() -> list[Path]:
    return sorted(SKILLS.glob("*/SKILL.md"))


def test_skills_present() -> None:
    names = {p.parent.name for p in _skill_files()}
    assert names == set(PROFILE), f"skills present: {names}"


def test_name_rules_and_reserved_words() -> None:
    for md in _skill_files():
        fm = _parse_frontmatter(md)
        name = fm.get("name", md.parent.name)
        assert NAME_RE.match(name), f"{md}: invalid name '{name}'"
        for word in RESERVED:
            assert word not in name.lower(), f"{md}: name contains reserved word '{word}'"


def test_descriptions_present_and_bounded() -> None:
    for md in _skill_files():
        fm = _parse_frontmatter(md)
        desc = fm.get("description", "")
        assert desc, f"{md}: empty description"
        assert len(desc) <= 1024, f"{md}: description exceeds 1024 chars"


def test_permission_profile_matches_documented() -> None:
    for md in _skill_files():
        name = md.parent.name
        fm = _parse_frontmatter(md)
        expected = PROFILE[name]

        disallowed_raw = fm.get("disallowed-tools", "")
        disallowed = {t for t in re.split(r"[ ,]+", disallowed_raw) if t and t != ">"}
        assert disallowed == expected["disallowed"], (
            f"{md}: disallowed-tools {disallowed} != documented {expected['disallowed']}"
        )

        model_invocable = "disable-model-invocation" not in fm or fm[
            "disable-model-invocation"
        ].lower() not in ("true",)
        assert model_invocable == expected["model_invocable"], (
            f"{md}: model-invocable {model_invocable} != documented {expected['model_invocable']}"
        )


def test_skill_bodies_have_no_dynamic_context_injection() -> None:
    # Review S3: v1 skills use no !`cmd` dynamic context injection.
    pattern = re.compile(r"(^|\s)!`")
    for md in _skill_files():
        text = md.read_text(encoding="utf-8")
        assert not pattern.search(text), f"{md}: dynamic context injection is disallowed in v1"
