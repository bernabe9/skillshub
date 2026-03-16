# SkillsHub: Product Vision

## Core Belief

Every organization runs on processes — deploying code, answering security questionnaires, reviewing PRs, onboarding new hires, preparing sales calls. Today these processes live in people's heads, scattered docs, or tribal knowledge. When someone describes a process well enough that an agent can execute it, that description becomes a **durable organizational asset** — one that is agent-agnostic, human-agnostic, and continuously improvable.

A skill is not tied to a specific agent or a specific person. It's a portable package of instructions, scripts, and assets that any agent (or human) can follow to accomplish a task. The value compounds: every time someone runs a skill and improves it, the improvement is available to everyone — across every agent, every team member, every future hire.

## Problem Statement

AI agent skills — portable packages following the [agentskills.io](https://agentskills.io/specification) specification — are the emerging standard for encoding these processes. Adopted by 30+ agents (Claude Code, Cursor, Copilot, Gemini CLI, OpenClaw, Goose, Roo Code, Windsurf, and others), skills are directories containing a `SKILL.md` file with optional scripts, references, and assets.

**The problem is distribution.** Today, teams face three compounding issues:

### 1. Skills distribution is manual and fragmented

Teams copy skill directories into each agent's expected path — `.claude/skills/`, `.cursor/skills/`, `.codex/skills/`, `.opencode/skill/` — creating N copies of the same skill. In practice, we've observed projects with byte-for-byte identical `SKILL.md` files duplicated across 4+ agent directories. Tools like `npx skills add` (Vercel) help install from GitHub repos, but each developer must run the install independently, and the CLI has no sync mechanism from its lock file (GitHub issue #283, still open).

### 2. Skills go stale

Once installed, skills are snapshots. There is no push mechanism — developers must manually `git pull` or `npx skills update` to get changes. In fast-moving teams, skills drift from the latest version within days. Claude Enterprise can admin-provision skills that auto-appear for org users, but this is Claude-only and doesn't extend to other agents.

### 3. Skills can't be improved where they're used

The most valuable skill improvements happen during use — when a developer discovers a missing step, an outdated command, or a better approach. Today, this feedback loop is broken: the developer must exit their conversation, find the skill file, edit it manually, commit, push, and hope teammates notice. No tool supports proposing skill improvements from within an agent conversation.

## Market Landscape

After researching 20+ tools in the agent skills ecosystem, here is the current state:

| Product | Centralized | Always Fresh | Write-Back | Multi-Agent | Org Management |
|---------|:-----------:|:------------:|:----------:|:-----------:|:--------------:|
| **skills.sh** (Vercel) | GitHub-backed | Pull-based | No | 40+ agents | No |
| **SkillReg.dev** | Private registry | Pull-based | No | Multiple | Yes |
| **Claude Enterprise** | Admin console | Auto-provision | No | Claude only | Yes |
| **skillshare** (runkids) | Git + symlinks | Manual pull | No | 50+ agents | No |
| **Skillport** | Local MCP | N/A (local) | No | MCP clients | No |
| **ClawHub** | Public registry | Pull-based | No | OpenClaw | No |
| **skills.sh CLI** | GitHub repos | `npx skills update` | No | 40+ agents | No |
| **SkillsHub** (this) | GitHub repo | Hook-triggered sync | **Yes** | All agents | GitHub-native |

**The gap:** No product connects the full loop — centralized storage + always-fresh distribution + write-back from agent conversations + multi-agent support.

## Solution

SkillsHub is a CLI tool and local MCP server that turns a GitHub repository into a centralized, always-fresh, writable skills directory for organizations.

### Architecture

```
GitHub Repo (source of truth)
    ↕ git pull / push
~/.skillshub/repo/ (local clone)
    ↓ copy on sync
~/.agents/skills/ (agent-accessible)
    ← all agents scan natively
    → write-back via MCP → git commit → git push
```

**Three components:**
1. **GitHub repo** — single source of truth. Every skill change is a git commit (version history, diffs, rollback, audit trail — all free).
2. **CLI** (`skillshub`) — `sync` pulls latest skills and distributes to agent directories. Triggered automatically via agent SessionStart hooks.
3. **Local MCP server** (`skillshub mcp`) — 2 tools (`update_skill`, `create_skill`) that let agents propose improvements from conversations, commit, and push to GitHub.

### Key Design Principles

**Native activation over MCP tools.** Skills are synced to the filesystem (`~/.agents/skills/`) so every agent activates them using its built-in skill system — progressive disclosure, slash commands, file access all work natively. MCP is only used for the write path.

**Git as the database.** No PostgreSQL, no SQLite, no custom server. Git provides versioning (`git log`), diffs (`git diff`), rollback (`git revert`), auth (GitHub tokens/SSH), collaboration (PRs), and a web UI (GitHub). Zero infrastructure to deploy.

**Full skill directories, not just markdown.** Skills can contain `SKILL.md`, `scripts/`, `references/`, `assets/`. The sync copies entire directories. Agents access scripts and assets with their normal file tools.

**Hook-driven freshness.** Agent SessionStart hooks (supported by Claude Code, OpenClaw, and others) run `skillshub sync` automatically at the start of every session. No manual intervention needed.

## Target Users

Any knowledge worker who uses AI agents to automate operations — engineering, sales, security, legal, HR, finance, support. If you have a repeatable process that you can describe, SkillsHub turns it into a shared, always-fresh skill that any teammate can run from any agent.

## Key Differentiators

1. **Processes as assets** — Skills turn tribal knowledge into portable, versioned, continuously improving organizational assets. They're agent-agnostic (any agent can run them) and human-agnostic (any team member can use them).
2. **Write-back from conversations** — The only tool that lets agents propose skill improvements during use. Every time someone runs a process and finds a better way, the improvement flows back to the whole org.
3. **Native skill activation** — Skills work through each agent's built-in system (slash commands, auto-activation, progressive disclosure), not through a separate MCP tool layer
4. **Zero infrastructure** — GitHub is the backend. No server to deploy, no database to manage
5. **Universal** — Works with any agent that scans `.agents/skills/` (30+ agents) or supports MCP (virtually all modern agents)
6. **Git-native versioning** — Every change is a commit with a rationale. Full history, diffs, rollback, and audit trail come free.

## Success Metrics

- Time from skill update to team-wide availability (target: < 30 seconds via hook-triggered sync)
- Number of skill improvements proposed from agent conversations (target: measurable increase over zero, which is today's baseline)
- Skill duplication eliminated (target: 1 copy per skill, not N copies across agent directories)
- Developer setup time (target: `skillshub init <url>` + one config line per agent)
