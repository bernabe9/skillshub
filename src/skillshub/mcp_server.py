"""Local MCP server for SkillsHub — read and write shared agent skills."""

from __future__ import annotations

import json
import time
from pathlib import Path

from mcp.server.fastmcp import FastMCP

from .config import get_skills_dir
from .repo import commit_and_push, list_skills as repo_list_skills, pull
from .sync_engine import sync_single_skill
from .validation import validate_skill_name

mcp = FastMCP(
    "skillshub",
    instructions=(
        "SkillsHub manages your organization's shared AI agent skills. "
        "If you have native skill support (e.g. ~/.agents/skills/ or ~/.claude/skills/), "
        "prefer using skills from the filesystem — they are already synced there. "
        "Use list_skills and get_skill only if you cannot access skills from the filesystem directly. "
        "Use update_skill to improve existing skills based on what you learned in this conversation. "
        "Use create_skill to add new skills to the shared directory. "
        "Changes are automatically committed and pushed to the team's GitHub repository."
    ),
)

_last_pull_time = 0.0
_PULL_COOLDOWN_SECONDS = 30.0


def _safe_pull() -> None:
    """Pull if we haven't pulled recently. Tolerates network failures."""
    global _last_pull_time
    if time.monotonic() - _last_pull_time < _PULL_COOLDOWN_SECONDS:
        return
    try:
        pull()
        _last_pull_time = time.monotonic()
    except RuntimeError:
        pass


def _validate_file_path(skill_dir: Path, file_path_str: str) -> Path | None:
    """Validate that a file path stays within the skill directory. Returns resolved path or None."""
    file_path = (skill_dir / file_path_str).resolve()
    if not file_path.is_relative_to(skill_dir.resolve()):
        return None
    return file_path


def _write_files_and_publish(
    skill_name: str,
    skill_dir: Path,
    files: list[dict],
    commit_msg: str,
) -> dict:
    """Write files to skill dir, commit, push, and sync locally. Returns result dict."""
    # Validate and write files
    for file_entry in files:
        file_path = _validate_file_path(skill_dir, file_entry["path"])
        if file_path is None:
            return {
                "status": "error",
                "message": f"Invalid path '{file_entry['path']}' — must stay within skill directory.",
            }
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(file_entry["content"])

    # Commit and push
    try:
        sha = commit_and_push([f"skills/{skill_name}"], commit_msg)
    except RuntimeError as e:
        return {"status": "error", "message": str(e)}

    # Sync to local agent directories immediately
    sync_single_skill(skill_name)
    return {"status": "applied", "commit": sha}


@mcp.tool()
def list_skills(search: str = "") -> str:
    """List all available skills in the organization's shared directory.

    Returns skill names and descriptions. Use this to discover what skills
    are available before loading one with get_skill.

    Args:
        search: Optional search term to filter skills by name or description.

    Returns:
        JSON array of skills with name and description.
    """
    _safe_pull()

    skills = repo_list_skills()
    if search:
        term = search.lower()
        skills = [
            s
            for s in skills
            if term in s["name"].lower() or term in s["description"].lower()
        ]

    return json.dumps(
        [{"name": s["name"], "description": s["description"]} for s in skills],
        indent=2,
    )


@mcp.tool()
def get_skill(skill_name: str) -> str:
    """Load the full instructions for a skill.

    Returns the complete SKILL.md content plus a list of available resource
    files (scripts, references, assets) within the skill directory.

    Args:
        skill_name: Name of the skill to load.

    Returns:
        JSON with the skill content and list of resource file paths.
    """
    skill_dir = get_skills_dir() / skill_name
    if not skill_dir.exists():
        return json.dumps(
            {
                "status": "error",
                "message": f"Skill '{skill_name}' not found. Use list_skills to see available skills.",
            }
        )

    skill_md = skill_dir / "SKILL.md"
    if not skill_md.exists():
        return json.dumps(
            {"status": "error", "message": f"No SKILL.md in '{skill_name}'."}
        )

    resources = [
        str(f.relative_to(skill_dir))
        for f in sorted(skill_dir.rglob("*"))
        if f.is_file() and f.name not in ("SKILL.md", ".skillshub")
    ]

    return json.dumps(
        {
            "name": skill_name,
            "content": skill_md.read_text(),
            "resources": resources,
        }
    )


@mcp.tool()
def update_skill(
    skill_name: str,
    files: list[dict],
    rationale: str,
) -> str:
    """Update an existing skill in the organization's shared skills directory.

    Use when you've identified improvements to a skill during this conversation.

    Args:
        skill_name: Name of the skill to update
        files: List of files to create/update. Each item has 'path' (relative to skill dir,
               e.g. 'SKILL.md', 'scripts/deploy.sh') and 'content' (new file content).
        rationale: Why this change was made (used as git commit message)

    Returns:
        JSON with status and commit SHA
    """
    skill_dir = get_skills_dir() / skill_name
    if not skill_dir.exists():
        return json.dumps(
            {
                "status": "error",
                "message": f"Skill '{skill_name}' not found. Use create_skill to create a new skill.",
            }
        )

    _safe_pull()

    result = _write_files_and_publish(
        skill_name,
        skill_dir,
        files,
        f"Update {skill_name}: {rationale}",
    )
    if result["status"] == "applied":
        result["message"] = (
            f"Updated '{skill_name}' and synced to local agent directories."
        )
    return json.dumps(result)


@mcp.tool()
def create_skill(
    name: str,
    description: str,
    files: list[dict],
) -> str:
    """Create a new skill in the organization's shared skills directory.

    The skill must follow the agentskills.io specification.

    Args:
        name: Skill name (lowercase letters, numbers, hyphens; max 64 chars)
        description: What the skill does and when to use it (max 1024 chars)
        files: List of files for the skill. Must include SKILL.md. Each item has
               'path' and 'content'. Example paths: 'SKILL.md', 'scripts/build.sh',
               'references/guide.md'.

    Returns:
        JSON with status and skill name
    """
    error = validate_skill_name(name)
    if error:
        return json.dumps({"status": "error", "message": f"Invalid name: {error}"})

    file_paths = {f["path"] for f in files}
    if "SKILL.md" not in file_paths:
        return json.dumps(
            {"status": "error", "message": "files must include a 'SKILL.md' entry."}
        )

    _safe_pull()

    # Check existence after pull to avoid TOCTOU
    skill_dir = get_skills_dir() / name
    if skill_dir.exists():
        return json.dumps(
            {
                "status": "error",
                "message": f"Skill '{name}' already exists. Use update_skill to modify it.",
            }
        )

    skill_dir.mkdir(parents=True)
    result = _write_files_and_publish(name, skill_dir, files, f"Create skill: {name}")
    if result["status"] == "applied":
        result["status"] = "created"
        result["skill_name"] = name
        result["message"] = f"Created '{name}' and synced to local agent directories."
    return json.dumps(result)


def run_mcp_server() -> None:
    """Run the MCP server on stdio transport."""
    mcp.run(transport="stdio")
