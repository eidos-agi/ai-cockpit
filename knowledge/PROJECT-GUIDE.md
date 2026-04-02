# AI Cockpit — Project Guide for New Agents

> Last updated: 2026-04-02. Read this before touching anything.

## What This Is

`ai-cockpit` is a CLI tool + workspace template for managing "cockpits" — Claude Code workspaces with session lifecycle skills. It's published to PyPI as `ai-cockpit` and lives at `eidos-agi/ai-cockpit-template` on GitHub.

**Two things in one repo:**
1. **The CLI** (`pip install ai-cockpit`) — a Python CLI with a Textual TUI that manages a fleet of cockpits. Entry point: `src/ai_cockpit/cli.py` → `cockpit` command.
2. **The template** — skills, CLAUDE.md, state.json that get copied into new cockpits via `cockpit new`.

## Architecture

```
ai-cockpit-template/
├── src/ai_cockpit/
│   ├── __init__.py          # Version string (keep in sync with pyproject.toml)
│   ├── __main__.py          # python -m ai_cockpit.cli support
│   ├── cli.py               # THE CLI — ~1700 lines, single file by design
│   ├── loss.py              # Loss functions + mission scores (loss-forge)
│   └── template/            # Bundled in the pip wheel — copied by `cockpit new`
│       ├── .claude/skills/  # 8 skills shipped with every new cockpit
│       ├── CLAUDE.md        # Template CLAUDE.md with placeholders
│       ├── state.json       # Template state.json
│       └── tools/           # Learning browser plugin
├── .claude/skills/          # The CANONICAL skills (template/ copies from here)
│   ├── takeoff/
│   ├── land/
│   ├── touch-and-go/        # NEW — mid-flight checkpoint
│   ├── can-i-close/         # NEW — 3-contract pre-close audit
│   ├── cockpit-status/
│   ├── cockpit-repair/
│   ├── pre-flight/
│   └── clean-sweep/
├── .ike/                    # Task tracking (ike.md)
├── .github/workflows/
│   ├── ci.yml               # pytest on ubuntu+macos, py3.10/3.12/3.13
│   └── publish.yml          # Tag-push → PyPI (trusted publisher, not yet configured)
├── tests/test_cli.py        # 23 tests
├── pyproject.toml           # Hatchling build, ai-cockpit package
├── CHANGELOG.md
├── CONTRIBUTING.md
├── LOSS-BASELINE.md         # Loss 1.28 | Mission 1.00 as of 2026-04-02
├── LICENSE                  # MIT, Eidos AGI
└── knowledge/               # Devlogs and this guide
```

## Key Design Decisions

### Single-file CLI
`cli.py` is one file (~1700 lines). This is intentional — not a smell. The CLI is the product. Splitting it into modules adds import complexity with no benefit for a tool this size. The loss function L6 tracks line count and will flag if it grows past 2000.

### Template bundling
The `.claude/skills/` at repo root are the canonical versions. `src/ai_cockpit/template/.claude/skills/` are copies bundled in the pip wheel. **These must stay in sync.** The loss function L2 (template drift) checks SHA256 hashes and flags any drift.

When you change a skill:
1. Edit it in `.claude/skills/<name>/skill.md`
2. Copy it to `src/ai_cockpit/template/.claude/skills/<name>/skill.md`
3. L2 will catch if you forget

### Config, not hardcodes
All user-specific paths are in `~/.cockpit/config.json`. The CLI has zero hardcoded paths. L3 checks for this.

### Three persistence locations
- `~/.cockpit/config.json` — user config (scan dirs)
- `~/.cockpit/registry.json` — registered cockpits (name, slug, path, org)
- `~/.cockpit/cockpit-cockpit.log` — crash log

## The 4-Primitive Lifecycle

This is the core conceptual model. Everything flows from this.

```
/takeoff → work → /touch-and-go → work → /can-i-close → /land
```

| Primitive | CLI command | Skill | Purpose |
|-----------|------------|-------|---------|
| takeoff | (launches claude) | `/takeoff` | Boot session, drift check, priorities |
| touch-and-go | `cockpit tag` | `/touch-and-go` | Mid-flight checkpoint. Commit, push, bookmark. Context compaction point. |
| can-i-close | `cockpit cic` | `/can-i-close` | 3-contract audit before closing |
| land | (none — skill only) | `/land` | Park session. Gated by can-i-close. |

**Critical rule:** Never suggest `/land` unprompted. Use `/touch-and-go` for saves. Only `/land` when the user explicitly says they're done.

### The Three Contracts (can-i-close)

| Contract | What it checks | CLI can check? |
|----------|---------------|----------------|
| **Workspace** | Git dirty, unpushed, conflicts, secrets staged | Yes — `cockpit cic` |
| **Session** | Bookmark written, devlog updated, tasks resolved | Partially |
| **Conversation** | Promises kept, decisions recorded, knowledge captured | No — AI only |

The CLI (`cockpit cic`) handles the workspace contract across the whole fleet. The skill (`/can-i-close`) does all three but only for the current cockpit.

## CLI Commands

| Command | Aliases | What |
|---------|---------|------|
| `cockpit` | | Interactive TUI (Textual app) |
| `cockpit <name>` | | Launch cockpit in Claude Code |
| `cockpit <name> -a` | `--auto` | Launch in auto permission mode |
| `cockpit <name> -y` | `--yolo` | Launch with --dangerously-skip-permissions |
| `cockpit new <path>` | | Scaffold new cockpit from template |
| `cockpit can-i-close` | `cic` | Workspace contract check, fleet-wide |
| `cockpit touch-and-go` | `tag` | Commit + push all dirty cockpits |
| `cockpit scan` | | Auto-discover cockpits in scan dirs |
| `cockpit status` | | Schema version + capabilities per cockpit |
| `cockpit list` | | Non-interactive cockpit list |
| `cockpit upgrade <name>` | | Upgrade cockpit to latest schema (v0→v3) |
| `cockpit add <path>` | | Manually register a cockpit |
| `cockpit remove <name>` | | Unregister a cockpit |
| `cockpit config` | | Show/edit scan directories |
| `cockpit marketplace` | | Show Eidos plugin marketplace info |
| `cockpit grade` | | Loss-forge instrument panel |
| `cockpit grade --json` | | Machine-readable loss/mission output |
| `cockpit doctor` | | Check environment (git, gh, claude, python, textual) |
| `cockpit completions bash/zsh` | | Generate shell completions |
| `cockpit version` | | Show version |
| `cockpit help` | `-h`, `--help` | Show usage |

All sub-commands support `--help`. This was a bug that was fixed — without it, `cockpit touch-and-go --help` was accidentally committing and pushing all dirty repos.

## Schema Versions

Cockpits have a schema version detected from their file structure:

| Version | Requirements |
|---------|-------------|
| v0 | Has `state.json` only |
| v1 | Has `cockpit-cockpit/cockpit-settings.yaml` + `state.json` |
| v2 | Has lifecycle skills (≥3) + `.visionlog/` + settings |
| v3 | Has full trilogy (`.visionlog/` + `.research/` + `.ike/`) + all 5 core skills + settings |

`cockpit upgrade <name>` plans and applies upgrades. `--apply` to execute (dry-run by default).

## The TUI

The interactive `cockpit` command (no args) launches a Textual TUI with:
- Left pane: cockpit list grouped by org, with number-key navigation
- Right pane: preview showing settings, state, activity, launch command
- 11 custom themes (eidos, eidos-light, cockpit-dark, midnight, ocean, ember, forest, mono, daylight, paper, sand)
- Keybindings: Enter (open), a (auto mode), y (bypass), t (cycle theme), s (scan), q (quit)
- Dirty repo counts shown per org group

The TUI imports `textual` — this is the only heavy dependency.

## Loss-Forge Integration

`cockpit grade` runs 6 mission scores and 6 loss functions:

**Missions (higher is better, max 1.0):**
- M1: Zero-to-flying (can a new user scaffold and launch?)
- M2: Fleet awareness (TUI, list, status, fleet-wide cic/tag)
- M3: Safe close (can-i-close + gated land)
- M4: Lifecycle completeness (all 4 primitives functional)
- M5: Plugin discovery (marketplace command, README)
- M6: Self-documenting (help, docs, changelog, contributing)

**Losses (lower is better, 0.0 = perfect):**
- L1: Untested commands (commands without pytest coverage)
- L2: Template drift (bundled skills out of sync with repo skills)
- L3: Hardcoded paths (absolute paths in cli.py)
- L4: Missing help (commands without --help handling)
- L5: Stale PyPI (local version != published version)
- L6: Code mass (cli.py line count vs 1500 threshold)

Baseline as of 2026-04-02: **Loss 1.28 | Mission 1.00**

The loss tells you exactly what to work on next. L1 (untested commands) is the biggest contributor.

## PyPI State

| Package | Version | What |
|---------|---------|------|
| `ai-cockpit` | 0.2.0 | The CLI. `pip install ai-cockpit` |
| `eidos-mail` | 0.1.0 | Email MCP server (also in marketplace) |

The PyPI token is in eidos-vault at `services/pypi/api-token`. It's org-scoped.

Trusted publisher (GitHub Actions auto-publish on tag) is NOT yet configured. TASK-0002 is blocked waiting for manual config at pypi.org.

## Marketplace Integration

`cockpit marketplace` promotes the Eidos Marketplace for Claude Code. The marketplace is at `eidos-agi/eidos-marketplace`.

After `cockpit scan`, if the user hasn't seen the marketplace, a one-line hint is shown.

Plugins available:
- resume-resume, ike, visionlog, railguey, clawdflare, eidos-mail, research-md, forge-forge, probe-forge

## Fleet Sync

Two mechanisms for pushing skill updates to downstream cockpits:

1. **Pull-based** (recommended): `./bin/update-from-template` in each cockpit
2. **Push-based**: `./bin/sync-skills` from the template repo (reads `bin/cockpit-registry.txt`)

The registry file was renamed to `.example` to remove personal paths. For Daniel's machine, the registry lives at `~/.cockpit/registry.json` (managed by the CLI).

A manual sync was done on 2026-04-02 that pushed can-i-close, touch-and-go, and updated land to all 10 registered cockpits.

## Task Backlog (.ike/)

The project uses ike.md for task tracking. Project GUID: `4d7317fa-8f68-4b17-9ee8-912596fa4c53`.

As of 2026-04-02:
- TASK-0001: Done — Publish v0.2.0 to PyPI
- TASK-0002: Blocked — Trusted publisher config (manual PyPI step)
- TASK-0003: Done — Shell completions
- TASK-0004: Done — eidos-mail marketplace plugin
- TASK-0005: Done — Sync skills to fleet
- TASK-0006: Done — loss-forge integration

## What to Work On Next

Run `cockpit grade` to see current loss. The loss function tells you what matters:

1. **L1 (untested commands)** — Add tests for list, doctor, upgrade, status, grade, completions
2. **L4 (missing help)** — The detection in loss.py is slightly imprecise; `new` and `config` DO handle help but via different patterns
3. **L6 (code mass)** — cli.py is at ~1700 lines. If adding features, consider if any logic can be extracted without premature abstraction
4. **TASK-0002** — Have the user configure trusted publisher on pypi.org

## Common Gotchas

- **Version must be updated in TWO places**: `pyproject.toml` and `src/ai_cockpit/__init__.py`
- **Template skills must be copied in TWO places**: `.claude/skills/` (canonical) and `src/ai_cockpit/template/.claude/skills/` (bundled)
- **`cockpit tag` (touch-and-go) commits with `git add -A`** — this can accidentally stage things. The workspace contract checks for secrets but isn't exhaustive.
- **The TUI requires `textual>=0.40.0`** — older versions will crash
- **`cockpit new` uses `input()` for interactive prompts** — won't work in non-interactive contexts
- **The crash log at `~/.cockpit/cockpit-cockpit.log` captures all unhandled exceptions** — check here first when debugging user reports

## Ecosystem Context

ai-cockpit is one tool in the Eidos AGI ecosystem:

- **loss-forge** (`eidos-agi/loss-forge`) — where the loss function pattern comes from
- **eidos-marketplace** (`eidos-agi/eidos-marketplace`) — plugin registry for Claude Code
- **ike.md** — task management MCP used for this project's backlog
- **visionlog** — vision/goals/guardrails MCP
- **research.md** — evidence-graded decision MCP

The "trilogy" pattern (research.md → visionlog → ike.md) is referenced in the schema versioning — v3 cockpits have all three.

## User Preferences (from memory)

- **Never suggest /land unprompted.** Use /touch-and-go for checkpoints.
- **Don't over-read files.** Read once, write, test, commit. Ship fast.
- **Knowledge lives in the repo where the change was made.** Cross-repo sessions devlog to each repo touched.
- **Use loss-forge for self-improvement.** Every release must score equal or better.
- **NEVER use the Anthropic SDK directly.** Use `claude -p` for LLM queries.
- **NEVER use taskr or skillflow_execute.** Use ike.md + cockpit files for task tracking.
