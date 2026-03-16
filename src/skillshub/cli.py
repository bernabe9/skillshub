"""SkillsHub CLI — centralized skills directory for AI agent teams."""

from __future__ import annotations

import shutil
from pathlib import Path

import click

from . import __version__
from .config import (
    get_repo_path,
    get_repo_url,
    get_sync_targets,
    save_config,
    load_config,
)
from .repo import (
    clone_repo,
    commit_and_push,
    find_skill_dir,
    get_default_skills_dir,
    get_skill_diff,
    get_skill_log,
    list_skills,
    open_repo,
    pull,
    rollback_skill,
)
from .sync_engine import sync_single_skill, sync_skills
from .validation import validate_skill_dir, validate_skill_name


@click.group()
@click.version_option(__version__)
def cli() -> None:
    """SkillsHub — centralized skills for AI agent teams."""
    pass


@cli.command()
@click.argument("github_url")
@click.option(
    "--path",
    "skills_path",
    multiple=True,
    help="Skills path within the repo (e.g. engineering/skills). Can specify multiple. If omitted, auto-discovers all skills/ directories.",
)
@click.option(
    "--clone-path",
    type=click.Path(),
    default=None,
    help="Local path for the repo clone (default: ~/.skillshub/repo)",
)
@click.option(
    "--sync-target",
    multiple=True,
    help="Directories to sync skills to (can specify multiple)",
)
def init(
    github_url: str,
    skills_path: tuple[str, ...],
    clone_path: str | None,
    sync_target: tuple[str, ...],
) -> None:
    """Initialize SkillsHub with a GitHub repository.

    Clones the repo and configures sync targets. Optionally specify which
    skills/ paths to subscribe to:

      skillshub init https://github.com/org/skills.git --path engineering/skills --path company-wide/skills
    """
    repo_path = Path(clone_path).expanduser() if clone_path else get_repo_path()

    if repo_path.exists() and any(repo_path.iterdir()):
        click.echo(f"Directory {repo_path} already exists. Pulling latest...")
        pull(open_repo(repo_path))
    else:
        click.echo(f"Cloning {github_url}...")
        clone_repo(github_url, repo_path)

    config = load_config()
    config["repo_url"] = github_url
    config["repo_path"] = str(repo_path)
    if skills_path:
        config["skills_paths"] = list(skills_path)
    if sync_target:
        config["sync_targets"] = list(sync_target)
    elif "sync_targets" not in config:
        config["sync_targets"] = get_sync_targets()
    save_config(config)

    click.echo(f"Initialized. Repo: {repo_path}")
    if skills_path:
        click.echo(f"Skills paths: {', '.join(skills_path)}")
    else:
        click.echo("Skills paths: auto-discover")
    click.echo(f"Sync targets: {', '.join(config['sync_targets'])}")

    # Auto-sync after init
    result = sync_skills()
    _print_sync_summary(result)


@cli.command()
def sync() -> None:
    """Pull latest skills and distribute to agent directories."""
    url = get_repo_url()
    if not url:
        click.echo(
            "Not initialized. Run 'skillshub init <github-url>' first.", err=True
        )
        raise SystemExit(1)

    repo_path = get_repo_path()
    if not repo_path.exists():
        click.echo(f"Repo not found at {repo_path}. Re-run 'skillshub init'.", err=True)
        raise SystemExit(1)

    click.echo("Pulling latest...")
    pull()

    result = sync_skills()
    _print_sync_summary(result)


@cli.command()
@click.argument("skill_dir", type=click.Path(exists=True))
def push(skill_dir: str) -> None:
    """Push a local skill directory to the shared repo.

    Copies the skill into the repo, validates, commits, and pushes.
    """
    src = Path(skill_dir).resolve()

    # Validate
    errors = validate_skill_dir(src)
    if errors:
        click.echo("Validation errors:", err=True)
        for e in errors:
            click.echo(f"  - {e}", err=True)
        raise SystemExit(1)

    # Copy to the first (default) skills dir
    dst = get_default_skills_dir() / src.name
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(src, dst)

    # Commit and push
    repo_path = str(dst.relative_to(get_repo_path()))
    sha = commit_and_push(
        [repo_path],
        f"Push skill: {src.name}",
    )

    if sha == "no-changes":
        click.echo(f"Skill '{src.name}' is already up to date.")
    else:
        click.echo(f"Pushed '{src.name}' (commit {sha[:8]})")

    # Sync to local agent dirs
    sync_single_skill(src.name)


@cli.command("list")
@click.option("--refresh", is_flag=True, help="Pull latest from remote before listing")
def list_cmd(refresh: bool) -> None:
    """List all skills in the shared repo."""
    if refresh:
        try:
            pull()
        except RuntimeError:
            pass

    skills = list_skills()
    if not skills:
        click.echo("No skills found. Push one with 'skillshub push <dir>'.")
        return

    for skill in skills:
        click.echo(f"  {skill['name']:<30} {skill['description']}")


@cli.command()
@click.argument("skill_name", required=False)
@click.option("-n", "--count", default=20, help="Number of entries to show")
def log(skill_name: str | None, count: int) -> None:
    """Show version history for a skill (or all skills)."""
    if skill_name:
        entries = get_skill_log(skill_name, max_count=count)
        if not entries:
            click.echo(f"No history found for '{skill_name}'.")
            return
        click.echo(f"History for {skill_name}:")
        for entry in entries:
            click.echo(f"  {entry['sha']}  {entry['date'][:10]}  {entry['message']}")
    else:
        # Show recent commits across all skills
        repo = open_repo()
        for commit in repo.iter_commits(max_count=count):
            click.echo(
                f"  {commit.hexsha[:8]}  "
                f"{commit.committed_datetime.strftime('%Y-%m-%d')}  "
                f"{commit.message.strip()}"
            )


@cli.command()
@click.argument("skill_name")
@click.argument("ref1", default="HEAD~1")
@click.argument("ref2", default="HEAD")
def diff(skill_name: str, ref1: str, ref2: str) -> None:
    """Show diff for a skill between two versions."""
    output = get_skill_diff(skill_name, ref1, ref2)
    if output:
        click.echo(output)
    else:
        click.echo(f"No changes for '{skill_name}' between {ref1} and {ref2}.")


@cli.command()
@click.argument("skill_name")
@click.argument("ref")
def rollback(skill_name: str, ref: str) -> None:
    """Restore a skill to a previous version."""
    click.echo(f"Rolling back '{skill_name}' to {ref}...")
    sha = rollback_skill(skill_name, ref)

    if sha == "no-changes":
        click.echo("No changes needed (skill already at that version).")
    else:
        click.echo(f"Rolled back '{skill_name}' (commit {sha[:8]})")

    sync_single_skill(skill_name)


@cli.command()
@click.argument("name")
@click.option(
    "--path",
    "target_path",
    default=None,
    help="Skills path within the repo (e.g. engineering/skills). Defaults to skills/.",
)
def create(name: str, target_path: str | None) -> None:
    """Scaffold a new skill with a SKILL.md template."""
    error = validate_skill_name(name)
    if error:
        click.echo(f"Invalid name: {error}", err=True)
        raise SystemExit(1)

    if find_skill_dir(name) is not None:
        click.echo(f"Skill '{name}' already exists.", err=True)
        raise SystemExit(1)

    if target_path:
        base = get_repo_path() / target_path
    else:
        base = get_repo_path() / "skills"
    base.mkdir(parents=True, exist_ok=True)
    skill_dir = base / name
    skill_dir.mkdir(parents=True, exist_ok=True)
    (skill_dir / "SKILL.md").write_text(
        f"""---
name: {name}
description: TODO — describe what this skill does and when to use it.
---

# {name}

TODO — add instructions for the agent here.
"""
    )

    click.echo(f"Created {skill_dir}/SKILL.md")
    click.echo(f"Edit the SKILL.md, then run: skillshub push {skill_dir}")


@cli.command()
@click.confirmation_option(
    prompt="This will remove the local repo clone and all synced skills. Continue?"
)
def reset() -> None:
    """Remove all skillshub data (repo clone, config, synced skills)."""
    import shutil as sh

    from .config import CONFIG_DIR, CONFIG_FILE, get_sync_targets

    # Remove synced skills (only those with .skillshub marker)
    for target in get_sync_targets():
        target_path = Path(target).expanduser()
        if not target_path.exists():
            continue
        for skill_dir in target_path.iterdir():
            if skill_dir.is_dir() and (skill_dir / ".skillshub").exists():
                sh.rmtree(skill_dir)
                click.echo(f"Removed {skill_dir}")

    # Remove repo clone
    repo_path = get_repo_path()
    if repo_path.exists():
        sh.rmtree(repo_path)
        click.echo(f"Removed {repo_path}")

    # Remove config
    if CONFIG_FILE.exists():
        CONFIG_FILE.unlink()
        click.echo(f"Removed {CONFIG_FILE}")

    # Remove config dir if empty
    if CONFIG_DIR.exists() and not any(CONFIG_DIR.iterdir()):
        CONFIG_DIR.rmdir()

    click.echo("Reset complete.")


@cli.command()
def mcp() -> None:
    """Start the local MCP server (stdio transport)."""
    from .mcp_server import run_mcp_server

    run_mcp_server()


def _print_sync_summary(result: dict) -> None:
    """Print a human-readable sync summary."""
    if result.get("error"):
        click.echo(f"Error: {result['error']}", err=True)
        return

    synced = result.get("synced", [])
    removed = result.get("removed", [])
    unchanged = result.get("unchanged", [])

    total = len(synced) + len(unchanged)
    if synced:
        click.echo(f"Synced {len(synced)} skill(s): {', '.join(synced)}")
    if removed:
        click.echo(f"Removed {len(removed)} skill(s): {', '.join(removed)}")
    if not synced and not removed:
        click.echo(f"All {total} skill(s) up to date.")
