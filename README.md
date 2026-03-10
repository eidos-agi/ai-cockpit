# AI Cockpit Template

Universal session lifecycle primitives for Claude Code workspaces.

**Hop in. Fly. Land.**

## What This Is

A cockpit is a Claude Code workspace with a rhythm:

1. **`/takeoff`** — Boot sequence. Reads your last bookmark, checks what changed, shows priorities. Waits for orders.
2. **Work** — Use your domain-specific skills. The cockpit tracks state.
3. **`/land`** — Park sequence. Captures what got done, what's next, writes a bookmark for next session.

This template provides the universal primitives that every cockpit needs. Fork it, add your domain-specific skills, and you have a cockpit.

## Quick Start

```bash
# Clone the template
gh repo create my-cockpit --template rhea-impact/ai-cockpit-template --public
cd my-cockpit

# Customize CLAUDE.md with your role context
# Add domain-specific skills to .claude/skills/

# Start working
claude
# > /takeoff
# > ... do your work ...
# > /land
```

## What's Included

### Skills (Universal Primitives)

| Skill | Trigger | What It Does |
|-------|---------|-------------|
| `/takeoff` | Start of session | ASCII header, drift detection, composes `/pre-flight` for full briefing |
| `/pre-flight` | Called by takeoff (or standalone) | Subagent scan: where we were / are / going / blockers |
| `/land` | End of session | Capture outcomes, blockers, next actions, write bookmark |
| `/cockpit-status` | Anytime | Show active workstreams, blockers, ages, who owes what |
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
2. **Session contracts** — Every session has a lifecycle: boot → work → land. Bookmarks are the contract between sessions.
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

MIT. Built by [Rhea Impact](https://rheaimpact.com) — free software for coding agents.
