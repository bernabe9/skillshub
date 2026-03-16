# SkillsHub

Centralized skills directory for AI agent teams. Sync, update, and create [agentskills.io](https://agentskills.io/specification) skills across all your agents.

## How It Works

1. Your team's skills live in a **GitHub repo** (single source of truth)
2. `skillshub sync` pulls them to `~/.agents/skills/` where all agents find them natively
3. Agents can **update and create skills** from conversations via the MCP server
4. Changes are committed and pushed — teammates get them on their next sync

## Setup

### 1. Create a GitHub repo for your team's skills

```bash
gh repo create your-org/skills --private
cd skills
mkdir skills && touch skills/.gitkeep
git add . && git commit -m "Initial commit"
git push --set-upstream origin main
cd ~
```

The repo just needs a `skills/` directory. Each skill is a subdirectory with a `SKILL.md` file.

### 2. Install SkillsHub

```bash
# From source (during development)
cd /path/to/skillshub
uv sync

# Or install globally (recommended for teammates)
uv tool install /path/to/skillshub
```

### 3. Connect to your team's repo

```bash
skillshub init https://github.com/your-org/skills.git
```

This clones the repo locally and syncs all skills to `~/.agents/skills/`.

### 4. Configure your agent

#### Claude Code

Two things to configure: a **hook** (auto-sync on session start) and the **MCP server** (write-back).

**Add the MCP server:**

```bash
claude mcp add --transport stdio --scope user skillshub -- uv run --project /path/to/skillshub skillshub mcp
```

**Add the SessionStart hook** to `~/.claude/settings.json`:

```json
{
  "hooks": {
    "SessionStart": [{
      "matcher": "startup|resume",
      "hooks": [{
        "type": "command",
        "command": "skillshub sync",
        "timeout": 30
      }]
    }]
  }
}
```

> If you installed from source (not `uv tool install`), use `uv run --project /path/to/skillshub skillshub sync` instead.

**Verify:** Start a new Claude Code session, then run `/mcp` — you should see `skillshub · ✔ connected`.

#### OpenClaw

OpenClaw runs remotely, so you interact with it through chat. Tell it:

**Step 1 — Install:**
> "Install skillshub: `pip install git+https://github.com/bernabe9/skillshub.git`"

**Step 2 — Connect to repo:**
> "Run `skillshub init https://github.com/your-org/skills.git`"

**Step 3 — Add MCP server for write-back:**
> "Add an MCP server to your config: name `skillshub`, command `skillshub`, args `["mcp"]`, transport `stdio`. Then restart to pick it up."

Or tell it to add this to `openclaw.json`:

```json
{
  "mcp": {
    "servers": {
      "skillshub": {
        "command": "skillshub",
        "args": ["mcp"],
        "transport": "stdio"
      }
    }
  }
}
```

**Step 4 — Keep skills fresh:**
> "Run `skillshub sync` every 5 minutes to keep skills fresh"

Or run `skillshub sync` manually whenever you want the latest skills.

**Verify:** Tell OpenClaw "say hello" — it should activate the skill from the repo.

#### Claude Cowork

Cowork runs on your local machine but executes commands in a sandboxed VM. It **cannot** run CLI commands like `skillshub sync` directly. Instead, it accesses skills entirely through the MCP server's read tools (`list_skills`, `get_skill`).

**Step 1 — Install skillshub** (from your terminal, not Cowork):

```bash
uv tool install /path/to/skillshub
# or: pip install git+https://github.com/bernabe9/skillshub.git
```

**Step 2 — Connect to repo** (from your terminal):

```bash
skillshub init https://github.com/your-org/skills.git
```

**Step 3 — Add MCP server** to `~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "skillshub": {
      "command": "/full/path/to/uv",
      "args": ["run", "--project", "/path/to/skillshub", "skillshub", "mcp"]
    }
  }
}
```

> **Important:** Use full absolute paths — Cowork's desktop process doesn't inherit your shell's PATH. Find your paths with `which uv` and use the full result.

If you installed skillshub globally (`uv tool install` or `pip install`), you can use the simpler config — but still use the full path:

```json
{
  "mcpServers": {
    "skillshub": {
      "command": "/full/path/to/skillshub",
      "args": ["mcp"]
    }
  }
}
```

**Step 4 — Restart Claude Desktop** to pick up the MCP config.

**Step 5 — Verify.** In Cowork, ask "what skills are available in skillshub?" — it should call `list_skills` and show your team's skills.

**How Cowork uses skills:**
- **Discovery:** Cowork calls `list_skills` MCP tool (not filesystem)
- **Reading:** Cowork calls `get_skill` MCP tool to load full instructions
- **Writing:** Cowork calls `update_skill` / `create_skill` to modify or create skills
- **Sync not needed:** Cowork reads directly from the repo via MCP, so it always gets the latest version

#### Other agents (Cursor, Copilot, Gemini CLI, etc.)

Most agents scan `~/.agents/skills/` natively. Just run `skillshub sync` and skills appear. For write-back, configure the MCP server using each agent's MCP config format.

## Usage

### Push an existing skill

```bash
skillshub push ./my-skill
```

The directory must contain a `SKILL.md` with valid frontmatter (`name` and `description` fields).

### Create a new skill

```bash
skillshub create my-skill-name
# Edit the generated SKILL.md, then:
skillshub push ~/.skillshub/repo/skills/my-skill-name
```

Or ask your agent: *"create a skill called my-skill-name that does X"* — it calls the `create_skill` MCP tool.

### Update a skill from a conversation

While using a skill, tell your agent: *"update this skill to also do Y"* — it calls the `update_skill` MCP tool, commits with a rationale, and pushes to GitHub.

### Sync latest skills

```bash
skillshub sync
```

This happens automatically via the SessionStart hook in Claude Code. For other agents, run it manually or set up a similar hook.

### View history

```bash
skillshub list                     # List all skills
skillshub log                      # Recent changes across all skills
skillshub log my-skill             # History for one skill
skillshub diff my-skill            # Diff of latest change
skillshub rollback my-skill HEAD~1 # Revert to previous version
```

## Teammate Onboarding

When a new teammate joins, they run:

```bash
# 1. Install
uv tool install /path/to/skillshub

# 2. Connect
skillshub init https://github.com/your-org/skills.git

# 3. Configure agent (see agent-specific instructions above)
```

That's it — all team skills are immediately available in their agent.

## CLI Reference

| Command | Description |
|---------|-------------|
| `skillshub init <url>` | Clone repo and configure sync targets |
| `skillshub sync` | Pull latest and distribute to agent directories |
| `skillshub push <dir>` | Push a local skill to the repo |
| `skillshub list` | List all skills |
| `skillshub log [skill]` | Show version history |
| `skillshub diff <skill>` | Show changes between versions |
| `skillshub rollback <skill> <ref>` | Restore a previous version |
| `skillshub create <name>` | Scaffold a new skill |
| `skillshub mcp` | Start the MCP server (stdio) |

See [VISION.md](VISION.md) for the full product vision and architecture.
