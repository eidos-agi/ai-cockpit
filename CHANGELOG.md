# Changelog

## v1.3.0 — 2026-03-10

Fleet sync, phone-home updates, and learning browser — backported from production cockpit usage.

### Takeoff
- **Fleet Sync (opt-in)** — Step 0 discovers repos via `gh repo list`, fetches/pulls all fleet repos, builds pilot activity maps from git author aliases, and surfaces fleet health in terminal, takeoff.md, and cockpit.html. Only runs if `cockpit.org` or `cockpit.repos_dir` is set in state.json — single-repo cockpits skip it entirely.
- **Phone Home (Step 1.5)** — Runs `./bin/update-from-template --check` silently during boot. If an update is available, surfaces it in the status bar. Never blocks takeoff.
- **Template update line** in status bar: `TEMPLATE  update available: v1.2.1 → v1.3.0`

### Pre-flight
- **Steps G & H** — Fleet status and pilot activity now feed into the briefing when fleet data is available
- Fleet health woven into WHERE WE ARE (dirty/diverged/unpushed repos)
- Remote arrivals woven into WHERE WE WERE (what other pilots pushed)
- Unpushed work flagged in WHERE WE'RE GOING as an action item
- Failed syncs flagged in BLOCKERS
- **Standalone mode** — when called independently (not from takeoff), runs `git fetch --all` without pulling
- Quality checklist expanded with fleet-aware items

### Cockpit HTML Template
- Added fleet dashboard CSS (repo tables, pilot activity cards, status colors)
- Added `{{FLEET_SECTION}}` placeholder — empty string when fleet sync doesn't run

### New Skill
- `/clean-sweep` — Workspace-wide commit, push, build, and test sweep. Discovers all repos, commits dirty work, pushes everything, runs builds/tests in parallel, produces a sweep report saved to `sweeps/`.

### New: Learning Browser
- Added `tools/learning-browser/` with agent-browser instructions for persistent research sessions
- Cockpits can store learnings and maintain browser sessions across days

### State
- state.json template now documents optional fleet fields (`org`, `repos_dir`, `fleet`, `pilots`)
- Added `cockpit.template` and `cockpit.template_version` fields for phone-home support

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
