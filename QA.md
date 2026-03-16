# QA Guide

Step-by-step QA for SkillsHub across three agents: Claude Code, Claude Cowork, and OpenClaw.

## Prerequisites

- A GitHub repo with a `skills/` directory (e.g., `https://github.com/your-org/skills.git`)
- SkillsHub installed (from source: `uv sync` in the skillshub project dir)
- `skillshub init https://github.com/your-org/skills.git` completed

If you haven't created the repo yet:

```bash
gh repo create your-org/skills --private
cd skills
mkdir skills && touch skills/.gitkeep
git add . && git commit -m "Initial commit"
git push --set-upstream origin main
```

## Agent 1: Claude Code

### Setup

1. **Init skillshub:**
   ```bash
   skillshub init https://github.com/your-org/skills.git
   ```

2. **Push a test skill:**
   ```bash
   mkdir -p /tmp/hello-world && cat > /tmp/hello-world/SKILL.md << 'EOF'
   ---
   name: hello-world
   description: A simple test skill that greets the user. Use when asked to say hello.
   ---

   # Hello World

   When activated, greet the user warmly and tell them this skill was loaded from SkillsHub.
   EOF

   skillshub push /tmp/hello-world
   ```

3. **Add MCP server:**
   ```bash
   claude mcp add --transport stdio --scope user skillshub -- uv run --project /path/to/skillshub skillshub mcp
   ```

4. **Add SessionStart hook** to `~/.claude/settings.json`:
   ```json
   {
     "hooks": {
       "SessionStart": [{
         "matcher": "startup|resume",
         "hooks": [{
           "type": "command",
           "command": "uv run --project /path/to/skillshub skillshub sync",
           "timeout": 30
         }]
       }]
     }
   }
   ```

   > **Important:** MCP servers do NOT go in `settings.json` — use `claude mcp add` instead.

### Test Cases

Start a **new** Claude Code session for each test.

#### T1: MCP server connected
- Run `/mcp`
- **Expected:** `skillshub · ✔ connected` appears in the list

#### T2: SessionStart hook syncs skills
- Start a new session
- **Expected:** Hook runs `skillshub sync` automatically (may see output briefly)
- Verify: `ls ~/.agents/skills/hello-world/SKILL.md` should exist

#### T3: Native skill activation
- Type `/hello-world`
- **Expected:** Skill activates, Claude follows its instructions

#### T4: Auto-activation by description
- Say "say hello"
- **Expected:** Claude matches the skill description and activates `hello-world`

#### T5: Write-back (update_skill)
- Say "update the hello-world skill to also include the current date and a motivational quote"
- **Expected:**
  - Claude calls `update_skill` MCP tool (not Edit tool)
  - Response shows `"status": "applied"` with a commit SHA
  - Check GitHub repo — commit should appear
  - Run `/hello-world` again — should include the new behavior

#### T6: Write-back (create_skill)
- Say "create a skill called code-review that reviews code for common issues like missing error handling and unclear naming"
- **Expected:**
  - Claude calls `create_skill` MCP tool
  - Response shows `"status": "created"`
  - `skillshub list` shows the new skill
  - Check GitHub repo — new skill directory appears

#### T7: Cross-session persistence
- Start a new session
- Run `/code-review` (the skill created in T6)
- **Expected:** Skill activates (it was synced via the SessionStart hook)

### Known Gotchas
- If Claude edits the file directly instead of calling the MCP tool, the change won't be pushed to GitHub. The agent sometimes prefers direct file edits — phrasing like "update the skill" (not "edit the file") helps steer it toward the MCP tool.

---

## Agent 2: Claude Cowork

### Setup

Cowork runs on your local machine but executes commands in a sandboxed Linux VM. It cannot run `skillshub sync`. It accesses skills entirely through MCP tools.

All setup steps are done from **your terminal**, not Cowork:

1. **Install skillshub:**
   ```bash
   uv tool install /path/to/skillshub
   # or: pip install git+https://github.com/bernabe9/skillshub.git
   ```

2. **Init skillshub:**
   ```bash
   skillshub init https://github.com/your-org/skills.git
   ```

3. **Add MCP server** to `~/Library/Application Support/Claude/claude_desktop_config.json`:
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
   > **Important:** Use full absolute paths (`which uv` to find yours). Desktop apps don't inherit your shell's PATH.

4. **Restart Claude Desktop** to pick up the MCP config.

### Test Cases

#### T1: MCP server connected
- Open Cowork settings or start a conversation
- **Expected:** No "MCP skillshub: Server disconnected" error. If you see this error, the path to `uv` is wrong — use `which uv` to get the full path.

#### T2: Skill discovery via MCP
- Say "what skills are available in skillshub?"
- **Expected:** Cowork calls `list_skills` MCP tool, shows skill names and descriptions

#### T3: Load a skill via MCP
- Say "load the hello-world skill from skillshub and follow its instructions"
- **Expected:** Cowork calls `get_skill` MCP tool, reads the SKILL.md content, follows the instructions

#### T4: Write-back (update_skill)
- Say "update the hello-world skill to also include a fun fact"
- **Expected:** Cowork calls `update_skill` MCP tool, commit appears on GitHub

#### T5: Write-back (create_skill)
- Say "create a skill called meeting-notes that summarizes meeting transcripts"
- **Expected:** Cowork calls `create_skill` MCP tool, skill appears on GitHub

#### T6: Cross-agent verify
- After creating/updating a skill from Cowork, run `skillshub sync` in your terminal
- Start a new Claude Code session
- **Expected:** The skill created from Cowork is available natively in Claude Code

### Known Gotchas
- **Cowork cannot run CLI commands** on your host — it runs in a sandboxed Linux VM. All reads go through MCP tools (`list_skills`, `get_skill`), not filesystem.
- **Use full absolute paths** in `claude_desktop_config.json` — `uv`, `skillshub`, and project paths must all be absolute. Desktop apps don't inherit shell PATH.
- **Restart required** — Claude Desktop must be restarted after changing `claude_desktop_config.json`.
- **No auto-sync needed** — Cowork reads from the repo via MCP (which does `git pull`), so it always gets the latest version without manual sync.

---

## Agent 3: OpenClaw

### Setup

OpenClaw runs remotely. All setup is done by talking to it in chat.

**Step 1 — Install skillshub.** Tell OpenClaw:
> "Install skillshub: `pip install git+https://github.com/bernabe9/skillshub.git`"

**Step 2 — Connect to repo.** Tell OpenClaw:
> "Run `skillshub init https://github.com/your-org/skills.git`"

**Step 3 — Add MCP server for write-back.** Tell OpenClaw:
> "Add an MCP server to your config: name `skillshub`, command `skillshub`, args `["mcp"]`, transport `stdio`. Then restart to pick it up."

**Step 4 — Keep skills fresh.** Tell OpenClaw:
> "Run `skillshub sync` every 5 minutes to keep skills fresh"

Or run `skillshub sync` manually whenever you want the latest: "sync my skills" / "run `skillshub sync`"

### Test Cases

#### T1: Skills synced after init
- After init, OpenClaw should report which skills were synced
- **Expected:** Shows `hello-world` (or whatever skills are in the repo)

#### T2: Native skill activation
- Say "say hello"
- **Expected:** OpenClaw activates the hello-world skill

#### T3: File access works
- Use a skill that references scripts (e.g., "deploy to staging")
- **Expected:** OpenClaw reads `scripts/deploy.sh` from the skill directory using normal file access

#### T4: Write-back (update_skill)
- Say "update the hello-world skill to also include a fun fact"
- **Expected:** OpenClaw calls `update_skill` MCP tool, commit appears on GitHub

#### T5: Write-back (create_skill)
- Say "create a skill called daily-standup that generates standup summaries"
- **Expected:** OpenClaw calls `create_skill` MCP tool, skill appears on GitHub

#### T6: Cross-agent sync
- Update a skill from OpenClaw
- Switch to Claude Code, start new session (hook syncs)
- **Expected:** The updated skill is available in Claude Code

#### T7: Freshness
- Push a skill update from Claude Code
- Tell OpenClaw "run `skillshub sync`" (or wait for the periodic sync)
- **Expected:** OpenClaw picks up the updated skill

### Known Gotchas
- OpenClaw runs remotely — `skillshub` must be installed on the host machine, not your local machine.
- OpenClaw watches skill directories via chokidar — after `skillshub sync`, changes should be picked up without restart.
- Git auth: the host machine needs GitHub access for push to work. For public repos, read-only sync works without auth. For write-back (push), the host needs a GitHub token or SSH key.
- No auto-sync hook: unlike Claude Code, OpenClaw doesn't have a SessionStart hook. Use periodic sync ("run skillshub sync every 5 minutes") or manual sync.

---

## Cross-Agent Test

The most important test — verifying skills stay in sync across agents:

1. **Create** a skill from Claude Code → verify it appears on GitHub
2. **Sync** from OpenClaw (`skillshub sync`) → verify the skill is available
3. **Update** the skill from OpenClaw → verify the commit on GitHub
4. **Start new Claude Code session** → SessionStart hook syncs → verify the update is there
5. **Sync** from Cowork → verify the update is there

**Expected:** One skill, one source of truth, all agents see the same version.
