# /takeoff — Cockpit Boot Sequence

## When to Use
Start of every session. This is the first thing you run.

## What It Does
Shows the ASCII art header, status bar, and drift detection. Composes `/pre-flight` (as a subagent) to produce the full situational briefing. Then generates persistent artifacts — `takeoff.md` and `cockpit.html` — so the briefing lives beyond the terminal. Waits for orders.

## Execution Steps

### 0. Fleet Sync (opt-in — runs before everything else)

**Skip this step entirely** if `state.json` has no `cockpit.org` and no `cockpit.repos_dir`. Fleet sync is for multi-repo organizations. Single-repo cockpits skip straight to Step 1.

Sync the entire org fleet so takeoff has full situational awareness across all repos.

**A. Discover repos** — run `gh repo list <org> --json name --limit 50` (where `<org>` comes from `state.json → cockpit.org`)
- This is the authoritative source of what repos exist
- **Fallback** (if `gh` is unavailable or offline): use the `fleet` map from `state.json` keys + scan `repos_dir` for local directories
- Merge discovered repos with the `fleet` map — any repo found via `gh` that isn't in `fleet` gets added with `display_name` derived from the repo name

**B. For each locally-cloned repo** (path derived from `repos_dir + "/" + repo_name`):
1. `git fetch --all --quiet` — get latest remote state
2. `git pull --ff-only --quiet` — pull if fast-forward possible (won't create merge commits)
3. Capture: current branch, dirty file count, ahead/behind counts, last 5 commit authors (via `git log --format='%an' -5`), count of new-from-remote commits (via `git rev-list HEAD..@{u} --count` or similar)
4. If pull fails (diverged history, etc.): **warn and continue** — never abort takeoff for a fleet sync issue

**C. Build pilot activity map** (only if `state.json → pilots` exists):
- Scan `git log --all --since='7 days ago' --format='%an'` across all repos
- Match each author name to pilots using `git_names` arrays in `state.json → pilots`
- Unknown authors (not matching any pilot's `git_names`) get flagged

**D. Output fleet summary to terminal**:
```
  FLEET     <N> repos synced | <N> new commits pulled | <N> unpushed
```

Then a compact repo table:
```
  REPO           BRANCH     STATUS       NEW    UNPUSHED
  project-a      main       clean        3      0
  project-b      main       2 dirty      0      1
  project-c      main       clean        0      0
```

Then pilot activity (if pilots configured):
```
  PILOTS    alice: project-a (3), project-b (1)
            bob: project-b (5), project-c (2)
            unknown "bot-ci": project-c (1)
```

**E. Repos not cloned locally** — report as "remote only" in the table. Do NOT auto-clone.

**F. Fallback rules**:
- `gh` unavailable → scan local dirs under `repos_dir` + fleet map keys
- `git fetch` fails → warn, skip that repo, continue
- `git pull` fails → warn (report as "diverged" in status), do not abort
- Network offline → use whatever local state exists, note "offline — using cached state"
- **Never abort takeoff for fleet sync issues** — degrade gracefully

### 1. Gather Core State (cheap, in main context)

**A. state.json** — from the cockpit root
- Get `cockpit.name` (for the ASCII art header)
- Get `theme` (for HTML generation)
- Get `watermarks.last_land` (when was the last session?)
- Get `counters.sessions` (how many sessions total?)
- If `last_land` is null, this is the first session ever

**B. Latest bookmark** — scan `~/.claude/bookmarks/` for the most recently modified `*-bookmark.json` whose `project.path` matches the current working directory
- If found: read it for `lifecycle_state`, `context.summary`, `next_actions`, `blockers`, `confidence`
- If not found: note "No previous bookmark for this cockpit"

**C. Git state** — if fleet sync ran (Step 0), use its data. Otherwise, use the `gitStatus` block injected at session start.
- Current branch, dirty files, recent commits are **already in context**
- **Do NOT re-run** `git status`, `git branch`, or `git log` unless fleet sync didn't cover this repo

**D. Pilot identity** — run `git config user.name` to get the name of who is taking off

### 1.5. Phone Home (template update check)

**If `bin/update-from-template` exists** in the cockpit root, run:

```bash
./bin/update-from-template --check 2>/dev/null
```

- If it reports an update is available, capture the version info (e.g., `v1.2.1 → v1.3.0`)
- Surface it in the status bar as:
  ```
  TEMPLATE  update available: v1.2.1 → v1.3.0 (run ./bin/update-from-template)
  ```
- If already up to date or the script doesn't exist or fails: skip silently. Never block takeoff for this.
- This is informational only — never auto-apply updates during takeoff.

### 2. Output ASCII Art Header

**Line 1: Cockpit name** — Generate the `cockpit.name` from state.json as bold Unicode block letters (same style as TAKEOFF below). This is dynamic per cockpit.

**Line 2: TAKEOFF** — Always this exact text:

```
  ████████╗ █████╗ ██╗  ██╗███████╗ ██████╗ ███████╗███████╗
  ╚══██╔══╝██╔══██╗██║ ██╔╝██╔════╝██╔═══██╗██╔════╝██╔════╝
     ██║   ███████║█████╔╝ █████╗  ██║   ██║█████╗  █████╗
     ██║   ██╔══██║██╔═██╗ ██╔══╝  ██║   ██║██╔══╝  ██╔══╝
     ██║   ██║  ██║██║  ██╗███████╗╚██████╔╝██║     ██║
     ╚═╝   ╚═╝  ╚═╝╚═╝  ╚═╝╚══════╝ ╚═════╝ ╚═╝     ╚═╝
```

**Block letter reference** — use this character set for generating the cockpit name:
```
█ ═ ╗ ╔ ╚ ╝ ║ ╠ ╣ ╦ ╩ ╬ ▀ ▄
```
Match the exact same visual weight and style as the TAKEOFF text above. Each letter should be 6-7 chars wide and 6 lines tall.

**Then the status bar:**
```
  BRANCH    <branch>          DIRTY  <yes (N) | clean>
  SESSION   #<N+1>            LAST   <time since last land>
```

If a template update was detected in Step 1.5:
```
  TEMPLATE  update available: <old> → <new> (run ./bin/update-from-template)
```

If drift was detected (compare git state to bookmark's `workspace_state`):
```
  DRIFT     <branch changed / N new commits / N files modified outside session>
```

### 3. Compose /pre-flight

Launch the `/pre-flight` skill as a **subagent** (Task tool, `subagent_type: "Explore"`) to scan the workspace and produce the four-part briefing.

Pass the subagent:
- The current working directory
- Bookmark context (summary, next_actions, blockers, lifecycle_state)
- Fleet report data from Step 0 (repo table, pilot activity map, sync warnings, new-from-remote commits with authors/summaries) — **only if fleet sync ran**
- Instructions to read the `/pre-flight` skill at `.claude/skills/pre-flight/skill.md` and follow it

**Output the subagent's result directly below the status bar.**

The result should be the four-part briefing:
```
WHERE WE WERE
  ...

WHERE WE ARE
  ...

WHERE WE'RE GOING
  1. ...
  2. ...
  3. ...

BLOCKERS
  ...
```

### 4. Generate takeoff.md

Write a markdown file at the cockpit root: `takeoff.md`

This is the persistent, git-friendly version of the takeoff briefing. It should contain everything shown in the terminal — status bar, drift alerts, resume context, and the full four-part briefing — in clean markdown.

Format:

```markdown
# <Cockpit Name> — Takeoff #N

**Pilot** <name> &nbsp;|&nbsp; **Date** Feb 25, 2026 &nbsp;|&nbsp; **Time** 9:45 PM

**Session** #N &nbsp;|&nbsp; **Branch** `main` &nbsp;|&nbsp; **Working tree** clean &nbsp;|&nbsp; **Last landing** never / 2h ago / etc.

> **Resume:** <bookmark summary, if any>

> **Drift:** <drift details, if any>

---

## Fleet Status

| Repo | Branch | Status | New | Unpushed |
|------|--------|--------|-----|----------|
| project-a | main | clean | 3 | 0 |
| project-b | main | 2 dirty | 0 | 1 |
| ... | ... | ... | ... | ... |

## Pilot Activity (7d)

- **alice**: project-a (3 commits), project-b (1 commit)
- **bob**: project-b (5 commits), project-c (2 commits)
- **unknown "bot-ci"**: project-c (1 commit)

---

## Where We Were

<briefing content — full paragraphs, not abbreviated>

## Where We Are

<briefing content>

## Where We're Going

1. <priority — with WHY it matters>
2. <priority>
3. <priority>

## Blockers

<blocker details with who, what, how long>

---

*Generated <ISO timestamp> by /takeoff*
```

**If fleet sync didn't run** (single-repo cockpit), omit the Fleet Status and Pilot Activity sections entirely.

**The markdown version can be MORE detailed than the terminal output.** The terminal is for quick orientation. The markdown is the full briefing document. Add context, connections between items, and implications that would be too verbose for the terminal.

### 5. Generate cockpit.html

Read the HTML template at `.claude/skills/takeoff/cockpit-template.html`.

Replace all `{{PLACEHOLDER}}` tokens with actual values:

| Placeholder | Source |
|---|---|
| `{{COCKPIT_NAME}}` | `state.json → cockpit.name` |
| `{{PRIMARY}}` | `state.json → theme.primary` |
| `{{DANGER}}` | `state.json → theme.danger` |
| `{{WARNING}}` | `state.json → theme.warning` |
| `{{BG}}` | `state.json → theme.bg` |
| `{{SURFACE}}` | `state.json → theme.surface` |
| `{{TEXT}}` | `state.json → theme.text` |
| `{{MUTED}}` | `state.json → theme.muted` |
| `{{PILOT}}` | `git config user.name` |
| `{{DATE}}` | Human-readable date (e.g., "Feb 25, 2026") |
| `{{TIME}}` | Human-readable time (e.g., "9:45 PM") |
| `{{TAKEOFF_NUMBER}}` | `counters.takeoffs + 1` |
| `{{SESSION_NUMBER}}` | `counters.sessions + 1` |
| `{{BRANCH}}` | Current git branch |
| `{{DIRTY_CLASS}}` | `clean` or `dirty` (CSS class) |
| `{{DIRTY_VALUE}}` | `Clean` or `N files modified` |
| `{{LAST_CLASS}}` | `never` if null, else empty |
| `{{LAST_LANDING}}` | Human-readable time since last land |
| `{{DRIFT_SECTION}}` | Full `<div class="drift">` block, or empty string if no drift |
| `{{RESUME_SECTION}}` | Full `<div class="resume">` block, or empty string if no bookmark |
| `{{FLEET_SECTION}}` | Full `<div class="fleet">` block with repo table + pilot activity cards (from Step 0 data). Empty string if fleet sync didn't run or failed entirely |
| `{{WHERE_WE_WERE}}` | Briefing content wrapped in `<p>` tags |
| `{{WHERE_WE_ARE}}` | Briefing content wrapped in `<p>` tags |
| `{{WHERE_WERE_GOING}}` | Briefing content as `<ol><li>` items |
| `{{BLOCKERS}}` | Briefing content wrapped in `<p>` tags |
| `{{TIMESTAMP}}` | Human-readable date/time (e.g., "Feb 25, 2026 at 4:15 PM") |

Write the result to `cockpit.html` at the cockpit root.

**Content in the HTML should match takeoff.md** — same level of detail, same structure. The HTML is just the styled presentation layer.

After writing, output:
```
  COCKPIT   takeoff.md + cockpit.html written → open cockpit.html in browser
```

### 6. Update State

Write to `state.json`:
- Set `watermarks.last_takeoff` to current ISO timestamp
- Increment `counters.sessions` by 1
- Increment `counters.takeoffs` by 1

### 7. STOP

Do NOT proceed with any work. Output:

```
Ready for orders.
```

And wait for the user to tell you what to do.

## Rules
- If fleet sync ran (Step 0), use its git data. Otherwise, reuse gitStatus from session context. Never re-fetch what's already gathered.
- The subagent (pre-flight) does the heavy scanning. Main context stays lean.
- Never ask questions during takeoff. Just show state.
- If no bookmark exists and no state.json exists, this is a fresh cockpit — say "First flight. Cockpit initialized." and create state.json. Still run pre-flight.
- If bookmark file is corrupted or unreadable, note "Bookmark corrupted — starting fresh" and continue.
- If `theme` is missing from state.json, use these defaults: primary `#3fb950`, danger `#f85149`, warning `#d29922`, bg `#0d1117`, surface `#161b22`, text `#e6edf3`, muted `#8b949e`.
- `takeoff.md` and `cockpit.html` are overwritten on every takeoff. They always reflect the current session's starting position.
- Both files should be committed to git (they're useful artifacts, not build output).
- **Fleet sync is opt-in**: only runs if `cockpit.org` or `cockpit.repos_dir` is set in state.json. Single-repo cockpits skip it entirely.
- **Fleet sync fallback**: if `gh` is unavailable, scan `repos_dir` for local directories + fleet map keys. If `git fetch` or `git pull` fails for a repo, warn and continue — never abort takeoff.
- **Repo paths are derived by convention**: `repos_dir + "/" + repo_name`. The `fleet` map does NOT contain paths — they are computed at runtime from `cockpit.repos_dir` and the map key.
- **No auto-clone**: repos discovered via `gh` that are not cloned locally are reported as "remote only" in the fleet table.
- **Phone home is silent**: if `bin/update-from-template` doesn't exist or fails, skip without comment. Never block takeoff for update checks.
