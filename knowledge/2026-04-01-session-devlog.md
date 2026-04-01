# Session Devlog — 2026-04-01

## What Shipped

### ai-cockpit v0.1.0 on PyPI
- Packaged the cockpit CLI as `pip install ai-cockpit`
- Entry point: `cockpit` command via `ai_cockpit.cli:main`
- Hardcoded SCAN_DIRS replaced with configurable `~/.cockpit/config.json`
- `cockpit config --add-scan-dir` / `--remove-scan-dir` for management
- `cockpit marketplace` command promotes eidos-marketplace plugins
- Copyright/README fixed: Rhea Impact → Eidos AGI, repo URLs corrected
- `cockpit-registry.txt` → `.example` (removed personal paths)
- Tagged v0.1.0, pushed to PyPI with org-scoped token

### `cockpit new` — scaffold from template
- Interactive wizard: name, org, description
- Copies bundled skills (6 total) from package data
- Personalizes CLAUDE.md and state.json
- Initializes git repo, auto-registers in cockpit registry
- Optional `--github` flag for remote repo creation

### Cockpit lifecycle redesign — 4 primitives
Previous: takeoff → land (binary, Claude kept suggesting /land prematurely)

New:
| Primitive | Purpose |
|-----------|---------|
| `/takeoff` | Boot session |
| `/touch-and-go` | Mid-flight checkpoint + context compaction |
| `/can-i-close` | 3-contract audit (workspace, session, conversation) |
| `/land` | Park (gated by can-i-close) |

**Decision:** Touch-and-go is the compaction point for long sessions. After flushing to 4 durable stores (git, bookmark, devlog, memory), conversation context is safe to compress. Proactive suggestion at >50 tool calls without checkpoint.

**Decision:** /land now requires /can-i-close to pass. BLOCK = don't land. --force to override.

### eidos-mail security audit
- Result: SAFE for public marketplace distribution
- No hardcoded secrets, vault-based credential handling, .mcp.json gitignored
- Needs pyproject.toml + MCP entry point before marketplace listing
- Session secret fallback ("dev-secret-change-me") only affects web UI, not MCP

## Bugs / Issues
- None

## Learnings
- The cockpit CLI existed only at `~/.local/bin/cockpit` — invisible to anyone cloning the repo
- `cockpit` name taken on PyPI (email newsletter tool) and npm (Skywriter component) — `ai-cockpit` was available
- Template files add ~64KB to the wheel — negligible cost for offline scaffolding
