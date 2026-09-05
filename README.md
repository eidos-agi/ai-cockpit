# AI Cockpit Template

Universal session lifecycle primitives for Claude Code workspaces.

**Hop in. Fly. Land.**

## What This Is

A cockpit is a Claude Code workspace with a rhythm:

1. **`/takeoff`** — Boot sequence. Reads your last bookmark, checks what changed, shows priorities.
2. **Work** — Use your domain-specific skills. The cockpit tracks state.
3. **`/touch-and-go`** — Mid-session checkpoint. Saves state, compacts context, keeps flying.
4. **`/can-i-close`** — Pre-close audit. Checks 3 contracts (workspace, session, conversation).
5. **`/land`** — Park sequence. Gated by can-i-close. Commits, pushes, bookmarks.

This template provides the universal primitives that every cockpit needs. Fork it, add your domain-specific skills, and you have a cockpit.

## Installation

```bash
pip install ai-cockpit
```

Or install from source:

```bash
gh repo clone eidos-agi/ai-cockpit-template
cd ai-cockpit-template
pip install -e .
```

Then tell cockpit where your workspaces live:

```bash
cockpit config --add-scan-dir ~/my-cockpits
cockpit scan
```

### Claude Code Plugins

The cockpit pairs well with Eidos plugins for Claude Code:

```bash
cockpit marketplace
```

Or install the marketplace directly:

```bash
claude plugins marketplace add eidos-agi/eidos-marketplace
claude plugins install resume-resume
claude plugins install ike
claude plugins install visionlog
```

## Quick Start

```bash
# Create a new cockpit
cockpit new ~/repos/my-ops-cockpit

# Launch it
cockpit my-ops-cockpit
# > /takeoff
# > ... do your work ...
# > /touch-and-go  (mid-session checkpoint)
# > ... more work ...
# > /can-i-close   (pre-close check)
# > /land
```

Or from a GitHub template:

```bash
gh repo create my-cockpit --template eidos-agi/ai-cockpit-template --public
cd my-cockpit
cockpit add .
```

## CLI Commands

The `cockpit` command manages your fleet of cockpits:

| Command | What |
|---------|------|
| `cockpit` | Interactive TUI selector |
| `cockpit <name>` | Launch a cockpit in Claude Code (default harness) |
| `cockpit <name> --harness deepseek` | Launch DeepSeek through Paseo provider `dsh` (alias: `dsh`) |
| `cockpit new <path>` | Scaffold a new cockpit from the template |
| `cockpit can-i-close` | Check all cockpits for uncommitted work (alias: `cic`) |
| `cockpit touch-and-go` | Commit & push all dirty cockpits (alias: `tag`) |
| `cockpit scan` | Auto-discover cockpits in scan directories |
| `cockpit status` | Show schema version & capabilities |
| `cockpit upgrade <name>` | Upgrade cockpit to latest schema |
| `cockpit config` | Manage scan directories |
| `cockpit marketplace` | Discover Claude Code plugins |
| `cockpit doctor` | Check environment (git, gh, claude, python) |
| `cockpit version` | Show version |

Every command supports `--help`.

### Harnesses

`cockpit <name>` defaults to Claude Code. Pass `--harness` (or `-H`) to launch a different coding agent in that cockpit directory:

| Harness | Aliases | How it launches |
|---------|---------|-----------------|
| `claude-code` | `claude` | `claude` (existing settings / `-a` / `-y`) |
| `grok` | | `grok` on PATH |
| `codex` | | `codex` on PATH |
| `cursor-agent` | `cursor` | `cursor-agent` on PATH |
| `eidos-harness` | `eidos` | `eidos-harness` on PATH |
| `hermes` | | `hermes` on PATH |
| `deepseek` | `dsh` | **Paseo** — `paseo run --provider dsh --cwd <cockpit>` then `paseo attach <agentId>` |
| `none` | | Print the path; do not start an agent |

DeepSeek is not launched as a raw `dsh` binary or the old `http://127.0.0.1:3080` web UI. If `paseo` or the `dsh` provider is missing, cockpit prints a clear install hint:

```bash
npm install dsh-acp-paseo
~/.local/lib/dsh-acp-paseo/node_modules/.bin/dsh-acp-paseo-install-provider
```

The interactive TUI asks for a harness after you pick a cockpit. `COCKPIT_HARNESS` can set the default for `cockpit <name>` when `--harness` is omitted.

## What's Included

### Skills (Universal Primitives)

| Skill | Trigger | What It Does |
|-------|---------|-------------|
| `/takeoff` | Start of session | Boot: bookmark resume, drift detection, priorities |
| `/touch-and-go` | Mid-session | Checkpoint: commit, push, bookmark, context compaction |
| `/can-i-close` | Before closing | Audit 3 contracts: workspace, session, conversation (20 checks) |
| `/land` | End of session | Park sequence — gated by can-i-close |
| `/pre-flight` | Called by takeoff | Situational scan: where we were / are / going / blockers |
| `/cockpit-status` | Anytime | Active workstreams, blockers, ages, ownership |
| `/cockpit-repair` | When things break | Validate state files, find corruption, offer fixes |
| `/clean-sweep` | Workspace behind | Commit, push, build, test all repos in one sweep |

### State Management

- **`state.json`** — Watermarks, counters, last-run timestamps. Skills read/write this to enable incremental operations.
- **Bookmarks** — Written to `~/.claude/bookmarks/` by `/land`. Read by `/takeoff` on next session. This is the bridge between sessions.

## Cockpit Architecture

```
your-cockpit/
├── .claude/
│   └── skills/
│       ├── takeoff/              # Boot sequence (from template)
│       ├── land/                 # Park sequence (from template)
│       ├── cockpit-status/       # Instrument panel (from template)
│       ├── pre-flight/           # Situational scan (from template)
│       ├── cockpit-repair/       # Diagnostics (from template)
│       ├── clean-sweep/          # Workspace sweep (from template)
│       └── your-domain-skill/    # Your additions
├── tools/
│   └── learning-browser/         # Persistent browser research (from template)
├── bin/
│   └── update-from-template      # Pull skill updates from upstream
├── skills_manifest.json           # SHA256 hashes for update tracking
├── state.json                    # Session state & watermarks
├── CLAUDE.md                     # Role context + instructions
└── ...                           # Your domain-specific structure
```

## Fleet Sync (opt-in)

For multi-repo organizations, `/takeoff` can sync your entire fleet before boot. Add these fields to `state.json`:

```json
{
  "cockpit": {
    "org": "your-github-org",
    "repos_dir": "~/repos-your-org"
  },
  "fleet": {
    "project-a": { "display_name": "Project A" },
    "project-b": { "display_name": "Project B" }
  },
  "pilots": {
    "alice": { "git_names": ["Alice Smith", "alice"], "git_emails": ["alice@example.com"] },
    "bob": { "git_names": ["Bob Jones"], "git_emails": ["bob@example.com"] }
  }
}
```

When configured, `/takeoff` will:
1. Discover repos via `gh repo list <org>`
2. Fetch and pull all local fleet repos
3. Build a pilot activity map (who committed where in the last 7 days)
4. Surface fleet health in the terminal, takeoff.md, and cockpit.html

**Single-repo cockpits** (no `org` or `repos_dir`) skip fleet sync entirely — no config needed.

## Design Principles

1. **Cheap boots** — `/takeoff` reads 2 things: state.json and latest bookmark. Git state and CLAUDE.md are already in session context. No redundant I/O.
2. **Session contracts** — Every session has a lifecycle: boot → work → checkpoint → audit → land. Three contracts must pass before closing: workspace (git), session (bookmarks/tasks), conversation (promises/decisions).
3. **Drift detection** — If the branch changed, files were modified, or commits landed since your last bookmark, `/takeoff` tells you.
4. **Domain-agnostic** — The template knows nothing about your project. It only knows about sessions, bookmarks, and state.
5. **Composable** — Add as many domain skills as you want. The primitives stay the same.

## Keeping Cockpits in Sync

### For cockpit owners (pull updates into your cockpit)

```bash
cd your-cockpit
./bin/update-from-template              # pull latest skills from upstream
./bin/update-from-template --dry-run    # preview what would change
./bin/update-from-template --check      # just check if updates are available
```

This is the **recommended** approach. Each cockpit pulls from its upstream template. No central registry needed — the cockpit knows its template from `state.json`.

- Only updates template skills — never touches your domain-specific skills
- Detects local customizations via SHA256 hashing — won't clobber your changes
- Updates `skills_manifest.json` and `state.json` with the new version

Requires: `gh` (GitHub CLI) and `jq`.

### For template maintainers (push updates to known cockpits)

```bash
cd ai-cockpit-template
./bin/sync-skills              # push all skills to all registered cockpits
./bin/sync-skills land         # push just one skill
./bin/sync-skills --dry-run    # preview without changes
```

Reads `bin/cockpit-registry.txt` for local cockpit paths. Useful when you maintain multiple cockpits on one machine.

### Release workflow (for template maintainers)

```bash
# 1. Make your skill changes
# 2. Generate the manifest
./bin/generate-manifest v1.3.0

# 3. Commit and tag
git add skills_manifest.json
git commit -m "release: v1.3.0"
git tag v1.3.0
git push --tags

# 4. Downstream cockpits can now: ./bin/update-from-template
```

## Documentation

| Guide | What It Covers |
|-------|---------------|
| [docs/customization.md](docs/customization.md) | Adding skills, extending state.json, configuring the dashboard |
| [docs/fleet.md](docs/fleet.md) | Managing multiple cockpits from a mothership (roles/, fleet registry) |
| [docs/integrations.md](docs/integrations.md) | Connecting MCP servers (Outlook, GitHub, Wrike, etc.) |
| [CHANGELOG.md](CHANGELOG.md) | Version history |

## In the Wild

Cockpits built from this template:
- **Eidos Cockpit** — Multi-pilot planning & mission control for Eidos AGI
- **AIC Director of AI** — Email-centric command post across 4 sub-roles
- **Greenmark Planning** — Waste management leadership planning hub
- **Reeves Cockpit** — Personal assistant command post
- *(Add yours here)*

## License

MIT. Built by [Eidos AGI](https://github.com/eidos-agi) — free software for coding agents.
