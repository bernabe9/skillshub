# SkillsHub

Centralized skills directory for AI agent teams. Sync, update, and create [agentskills.io](https://agentskills.io/specification) skills across all your agents.

## How It Works

1. Your team's skills live in a **GitHub repo** (single source of truth)
2. `skillshub sync` pulls them to `~/.agents/skills/` where all agents find them natively
3. Agents can **update and create skills** from conversations via the MCP server
4. Changes are committed and pushed — teammates get them on their next sync

## Quick Start

**Requirements:** Python 3.11+, Git, and access to your team's skills GitHub repo.

### Install

```bash
pip install git+https://github.com/bernabe9/skillshub.git
```

### Connect to your team's skills repo

```bash
skillshub init https://github.com/your-org/skills.git
```

This clones the repo and syncs all skills to your local agent directories.

### Configure your agent

**Claude Code** (one command):
```bash
skillshub setup claude-code
```

For other agents (OpenClaw, Cowork, etc.), see [Agent Setup Details](#agent-setup-details) below.

---

## Setting Up a New Skills Repo

If you're starting from scratch for your team:

### 1. Create the repo

```bash
gh repo create your-org/skills --private
cd skills
mkdir skills && touch skills/.gitkeep
git add . && git commit -m "Initial commit"
git push --set-upstream origin main
```

### 2. Organize by team (optional)

For larger orgs, organize skills into folders:

```
your-org/skills/
├── engineering/
│   └── skills/
│       ├── deploy-staging/SKILL.md
│       └── code-review/SKILL.md
├── sales/
│   └── skills/
│       └── call-prep/SKILL.md
└── company-wide/
    └── skills/
        └── security-questionnaire/SKILL.md
```

Teammates subscribe to the folders they need:

```bash
# Engineering
skillshub init https://github.com/org/skills.git --path engineering/skills --path company-wide/skills

# Sales
skillshub init https://github.com/org/skills.git --path sales/skills --path company-wide/skills

# Everything
skillshub init https://github.com/org/skills.git
```

### 3. Add your first skill

```bash
skillshub create my-first-skill
# Edit ~/.skillshub/repo/skills/my-first-skill/SKILL.md
skillshub push ~/.skillshub/repo/skills/my-first-skill
```

Or ask your agent: *"create a skill called my-first-skill that does X"*

---

## Agent Setup Details

### Claude Code

```bash
skillshub setup claude-code
```

This adds the MCP server and SessionStart hook automatically. Start a new session, run `/mcp` — should show `skillshub · ✔ connected`.

**How it works:** Skills sync to `~/.agents/skills/` on session start. Claude activates them natively (slash commands, auto-activation). Write-back goes through the MCP `update_skill`/`create_skill` tools.

### OpenClaw

OpenClaw runs remotely — all setup is done through chat.

1. Tell it: *"Install skillshub: `pip install git+https://github.com/bernabe9/skillshub.git`"*
2. Tell it: *"Run `skillshub init https://github.com/your-org/skills.git`"*
3. Tell it: *"Add an MCP server: name `skillshub`, command `skillshub`, args `["mcp"]`, transport `stdio`"*
4. Optionally: *"Run `skillshub sync` every 5 minutes to keep skills fresh"*

**How it works:** Skills sync to the host filesystem. OpenClaw picks them up natively. Write-back goes through MCP.

### Claude Cowork

Cowork runs in a sandboxed VM — it can't run CLI commands on your machine. It accesses skills entirely through MCP.

**From your terminal:**
```bash
pip install git+https://github.com/bernabe9/skillshub.git
skillshub init https://github.com/your-org/skills.git
```

**Add to** `~/Library/Application Support/Claude/claude_desktop_config.json`:
```json
{
  "mcpServers": {
    "skillshub": {
      "command": "skillshub",
      "args": ["mcp"]
    }
  }
}
```

> If `skillshub` isn't found, use the full path from `which skillshub`.

**Restart Claude Desktop.**

**How it works:** Cowork uses MCP tools (`list_skills`, `get_skill`) to discover and read skills. Write-back goes through `update_skill`/`create_skill`. No filesystem sync needed — MCP reads directly from the repo.

### Other Agents (Cursor, Copilot, Gemini CLI, etc.)

Most agents scan `~/.agents/skills/` natively. Just run `skillshub sync` and skills appear. For write-back, configure the MCP server using your agent's MCP config format.

---

## Usage

### Sync latest skills
```bash
skillshub sync
```
Automatic in Claude Code (SessionStart hook). Manual for other agents.

### Update a skill from a conversation
Tell your agent: *"update the deploy skill to also run smoke tests"* — calls `update_skill` MCP tool, commits to GitHub.

### Create a skill from a conversation
Tell your agent: *"create a skill called lint-check that runs our linting pipeline"* — calls `create_skill` MCP tool.

### Push a skill from the CLI
```bash
skillshub push ./my-skill
```

### View history
```bash
skillshub list                     # List all skills
skillshub log                      # Recent changes
skillshub log my-skill             # History for one skill
skillshub diff my-skill            # Latest change
skillshub rollback my-skill HEAD~1 # Revert
```

---

## Requirements

- **Python 3.11+**
- **Git** (for repo operations)
- **GitHub access** to your team's skills repo (HTTPS or SSH)

## CLI Reference

| Command | Description |
|---------|-------------|
| `skillshub init <url>` | Clone repo and configure. Use `--path` to subscribe to specific folders |
| `skillshub sync` | Pull latest and distribute to agent directories |
| `skillshub push <dir>` | Push a local skill to the repo |
| `skillshub list` | List all skills |
| `skillshub log [skill]` | Show version history |
| `skillshub diff <skill>` | Show changes between versions |
| `skillshub rollback <skill> <ref>` | Restore a previous version |
| `skillshub create <name>` | Scaffold a new skill |
| `skillshub mcp` | Start the MCP server (stdio) |

## Development

For contributors working on skillshub itself:

```bash
git clone https://github.com/bernabe9/skillshub.git
cd skillshub
uv sync              # Install dependencies
uv run skillshub     # Run from source
```

See [VISION.md](VISION.md) for the full product vision and architecture.
