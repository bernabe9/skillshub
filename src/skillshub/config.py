"""Configuration management for SkillsHub CLI."""

from __future__ import annotations

import json
from pathlib import Path

CONFIG_DIR = Path.home() / ".skillshub"
CONFIG_FILE = CONFIG_DIR / "config.json"

DEFAULT_SYNC_TARGETS = [
    str(Path.home() / ".agents" / "skills"),
    str(Path.home() / ".claude" / "skills"),
]


def load_config() -> dict:
    if not CONFIG_FILE.exists():
        return {}
    return json.loads(CONFIG_FILE.read_text())


def save_config(config: dict) -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    CONFIG_FILE.write_text(json.dumps(config, indent=2) + "\n")


def get_repo_path() -> Path:
    config = load_config()
    return Path(config.get("repo_path", str(CONFIG_DIR / "repo"))).expanduser()


def get_repo_url() -> str | None:
    return load_config().get("repo_url")


def get_sync_targets() -> list[str]:
    config = load_config()
    return config.get("sync_targets", DEFAULT_SYNC_TARGETS)


def get_skills_paths() -> list[str]:
    """Return the list of paths within the repo to scan.

    If empty or not set, auto-discovers all directories containing SKILL.md.
    """
    config = load_config()
    return config.get("skills_paths", [])


def get_skills_dirs() -> list[Path]:
    """Return resolved paths to all directories containing skills.

    If skills_paths is configured, uses those. Otherwise auto-discovers
    by scanning the repo for any SKILL.md file and deriving grouping directories.
    """
    repo = get_repo_path()
    configured = get_skills_paths()

    if configured:
        return [repo / p for p in configured]

    # Auto-discover: find all SKILL.md files and derive grouping directories
    found = set()
    for skill_md in repo.rglob("SKILL.md"):
        rel = skill_md.relative_to(repo)
        # Skip hidden directories (.git, .github, etc.)
        if any(part.startswith(".") for part in rel.parts):
            continue
        # Need at least <group>/<skill>/SKILL.md or <skill>/SKILL.md
        if len(rel.parts) < 2:
            continue
        # skill_md.parent = skill dir, skill_md.parent.parent = grouping dir
        found.add(skill_md.parent.parent)

    return sorted(found) if found else [repo / "skills"]
