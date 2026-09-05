# Changelog

## Unreleased

### Harnesses
- **`--harness` / `-H`** — launch a cockpit with claude-code, grok, codex, cursor-agent, eidos-harness, hermes, deepseek, or none
- **DeepSeek via Paseo** — `cockpit <name> --harness deepseek` (alias `dsh`) runs `paseo run --provider dsh --cwd <cockpit>` then `paseo attach <agentId>`. Clear errors when paseo or the `dsh` provider is missing, with the `dsh-acp-paseo` install hint. DeepSeek is not a raw `dsh` binary and no longer uses the localhost:3080 web UI
- **Hang-safe Paseo readiness** — `check_paseo_dsh_ready` uses PATH + `~/.paseo/config.json` `agents.providers.dsh`, then a timed `paseo provider ls` (5s). It never calls `paseo provider diagnostic dsh` (hangs on 0.7.0-beta.1 when STATUS=loading). `paseo run` also has a hard timeout. A probe hang is non-fatal when config already lists `dsh`
- **TUI harness menu** — after picking a cockpit, choose the harness before launch
- **`cockpit doctor`** — reports paseo + DeepSeek/Paseo provider readiness

### Fixes
- Removed hardcoded `/Users/dshanklin/...` conduit path; search is home-relative (`~/repos-personal/conduit/...`) plus `PATH`
- Mux chat tmux description no longer uses a nested same-quote f-string (SyntaxError on Python 3.10)

## v0.5.0 — 2026-06-26

Plan 2+3 flight deck — thin remote launch via conduit.

### Flight deck
- **`launch.py`** — hat × substrate × instrument router; conduit doctor → git pull → interactive attach
- **Remote TUI section** — Greenmark · Cyprus · Grok when `launch_targets` exist (or greenmark-cockpit slug default)
- **Local unchanged** — org-grouped list, one-click Claude launch
- **`cockpit doctor`** — registry hygiene (phantom/disabled paths), conduit + Cyprus doctor status

### Registry
- Optional `launch_targets[]` per cockpit entry (substrate, machine_id, remote_path, runtime_default, label)
- Greenmark v1 targets baked in for `greenmark-cockpit` slug

## v0.4.0 — 2026-04-03

Release pipeline standardization and forge ecosystem integration.

### Release Pipeline (ADR-001)
- **Single source of truth for version** — `importlib.metadata.version()` replaces hardcoded `__version__`. pyproject.toml is the only version source.
- **CI guardrails** — publish.yml validates tag matches pyproject.toml version and CHANGELOG has an entry before publishing.
- **Forge ecosystem** — CLAUDE.md templates reference forge-forge MCP for discovery, `.forge/installed.yaml` for provenance.
- **cockpit grade** — loss-forge instrument panel (6 missions, 6 losses). Baseline: Loss 1.28 | Mission 1.00.
- **Shell completions** — `cockpit completions bash/zsh` with cockpit name completion.
- **cockpit doctor** — environment check (git, gh, claude, python, textual).
- **PROJECT-GUIDE.md** — comprehensive agent handoff documentation.

### Skills
- **`/can-i-close`** — 3-contract pre-close audit (workspace, session, conversation).
- **`/touch-and-go`** — mid-flight checkpoint + context compaction.
- **`/land` updated** — gated by `/can-i-close`. `--force` to override.

### Repo
- Renamed from `ai-cockpit-template` to `ai-cockpit`.
- `.forge/installed.yaml` — retroactive provenance for loss-forge, foss-forge, ship-forge.

## v0.3.0 — 2026-04-03

Forge ecosystem integration (superseded by v0.4.0 — released same day).

## v0.2.0 — 2026-04-01

The "real software" release. Cockpit is now a pip-installable CLI with lifecycle commands.

### CLI — `pip install ai-cockpit`
- **`cockpit new <path>`** — Scaffold a new cockpit from the bundled template. Interactive wizard with 8 skills, git init, auto-register.
- **`cockpit can-i-close`** (alias: `cic`) — Workspace contract checks across all registered cockpits. Fleet-wide.
- **`cockpit touch-and-go`** (alias: `tag`) — Commit and push all dirty cockpits. Fleet-wide checkpoint.
- **`cockpit config`** — Manage scan directories. No more hardcoded paths.
- **`cockpit marketplace`** — Discover and install Eidos plugins for Claude Code.
- **`cockpit doctor`** — Check environment: git, gh, claude, python, textual, config state.
- **`cockpit version`** — Show installed version.
- All commands support `--help`.

### Skills — Session Lifecycle Redesign
- **`/touch-and-go`** — Mid-flight checkpoint + context compaction point.
- **`/can-i-close`** — 3-contract pre-close audit (20 checks): workspace, session, conversation.
- **`/land` updated** — Gated by `/can-i-close`. BLOCKs prevent landing. `--force` to override.

### Packaging
- `pyproject.toml` with hatchling build, `cockpit` entry point
- Template files bundled in wheel
- Published to PyPI as `ai-cockpit`
- GitHub Actions CI + trusted publisher for PyPI releases
- CONTRIBUTING.md added

### Fixes
- Copyright: Rhea Impact → Eidos AGI
- README rewritten with CLI commands table, updated lifecycle
- Hardcoded paths replaced with `~/.cockpit/config.json`

## v1.3.0 — 2026-03-10

Lean takeoff, fleet sync, phone-home, and learning browser plugin.

### Takeoff — Rewritten for Speed
- **No more subagent.** Pre-flight runs inline from data already in context (commits, bookmark, CLAUDE.md). Max 3 tool calls for entire boot.
- **Commit messages are the briefing.** Recent Activity section shows last 5-10 commits — the actual truth of what happened.
- **HTML is opt-in.** `cockpit.html` only generated when explicitly requested or `custom.html_dashboard` is true.
- **Phone Home (Step 1.5)** — Runs `./bin/update-from-template --check` silently. Surfaces available updates in status bar. Never blocks.
- **Fleet Sync (opt-in Step 0)** — Only runs if `cockpit.org` or `cockpit.repos_dir` is set. Discovers repos via `gh`, fetches/pulls, builds pilot activity maps. Single-repo cockpits skip entirely.

### Pre-flight — Now Lightweight
- Runs inline (no subagent, no Explore agent)
- Sources: commit messages, bookmark, CLAUDE.md, fleet data (if available)
- Zero extra tool calls — synthesizes from session context only
- Format simplified: RECENT ACTIVITY → RESUME → NEXT → BLOCKERS

### Cockpit HTML Template
- Added fleet dashboard CSS (repo tables, pilot activity cards, status colors)
- Added `{{FLEET_SECTION}}` placeholder
- **Now opt-in** — not generated unless requested

### New Skill
- `/clean-sweep` — Workspace-wide commit, push, build, test sweep

### New Plugin: Learning Browser
- `tools/learning-browser/` — plugin pattern for persistent browser research
- Each cockpit forks and customizes for their domain (finance, security, planning, etc.)
- agent-browser profile per cockpit, session persistence across days

### State
- state.json template documents optional fleet fields (`org`, `repos_dir`, `fleet`, `pilots`)
- Added `cockpit.template` and `cockpit.template_version` for phone-home

## v1.2.1 — 2026-02-26

### Tooling
- `bin/update-from-template` — Pull-based skill sync for downstream cockpits. Compares local skills against upstream manifest via SHA256 hashing, won't clobber local customizations.
- Fixed bash arithmetic bug in `update-from-template` (increment helper for `set -e` compatibility)

### Manifest
- `skills_manifest.json` now generated with `bin/generate-manifest` — SHA256 hashes for all template skills

## v1.2.0 — 2026-02-26

### Tooling
- `bin/sync-skills` — Push template skill updates to all downstream cockpits listed in `bin/cockpit-registry.txt`
- `bin/cockpit-registry.txt` — Registry of local cockpit paths for push-based sync
- `bin/generate-manifest` — Generate `skills_manifest.json` with SHA256 hashes

### Documentation
- Added sync-skills instructions to README
- Updated "In the Wild" section with production cockpits

## v1.1.0 — 2026-02-25

Upstream improvements from production use across AIC Director and Greenmark cockpits.

### Takeoff
- Reuse `gitStatus` from session context instead of re-fetching (faster boot)
- ASCII art header for visual identity
- Handle corrupted bookmark files gracefully ("starting fresh" instead of crashing)

### Land
- Three invocation modes: interactive (`/land`), scripted (`/land <debrief>`), silent (`/land clean`)
- ASCII art header for visual identity
- Max 2 tool calls for faster exit

### New Skills
- `/cockpit-repair` — validate state.json, bookmarks, and skills; offer fixes for corruption

### State
- Added `template` field to `cockpit` section in state.json
- Bumped version to 1.1.0

## v1.0.0 — 2026-02-25

Initial release.

### Skills
- `/takeoff` — Boot sequence with bookmark resume and drift detection
- `/land` — Park sequence with outcome capture and bookmark write
- `/cockpit-status` — Instrument panel for active work, blockers, ages

### State Management
- `state.json` with watermarks, counters, and extensible `custom` key
- Bookmark schema v1.1 written to `~/.claude/bookmarks/`

### Documentation
- README with quick start, architecture, design principles
- Customization guide with examples (meeting-driven, email-driven, code-driven cockpits)
- CLAUDE.md template with placeholder sections
