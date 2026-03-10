# /pre-flight — Situational Awareness Scan

## When to Use
- Called automatically by `/takeoff` (composed)
- Can also be called independently mid-session for a status refresh

## What It Does
Scans the cockpit workspace and produces a four-part **strategic** briefing. This is not a data dump — it's a human-readable situation report that helps the pilot decide what to do next.

When called by `/takeoff`, this runs as a subagent (Explore type) to keep the main context lean. When called independently, it runs inline.

## Tone & Voice

**Write like a sharp chief of staff briefing an executive.** Not like a database query result.

- Use plain language, not task IDs or technical jargon
- Say what *happened*, not what the bookmark JSON says
- Say what *matters*, not what exists in the file system
- If you don't have enough context to say something meaningful, say that — don't pad with noise

## Execution Steps

### 1. Scan What Exists (skip what doesn't)

**A. Bookmark context** (passed from takeoff, or read fresh if called independently)
- Last session summary, next actions, blockers, lifecycle state

**B. Recent git commits** — look at the last 5-10 commit messages on the current branch
- These tell you what *actually happened* recently, even if the bookmark is sparse

**C. Backlog** (if `backlog/tasks/` exists)
- Scan for the big picture: what initiatives are active, what's blocked, what's waiting on people
- Do NOT list task IDs or subtask numbers — synthesize into plain English

**D. Projects** (if `projects/` exists)
- List active project folders
- For each: what's the status? Is it moving or stale?

**E. CLAUDE.md** — pull the "What's Active" and "What's Blocked" sections
- These are the human-written status lines — they're the most reliable signal

**F. state.json custom fields**
- Read `custom` key for domain-specific state
- Translate numbers into meaning (e.g., "6 vendors researched" → "6 of 15 vendor systems researched — under half")

**G. Fleet status** (passed from takeoff's Step 0, or gathered fresh if called independently)
- **Skip if no fleet data is available** (single-repo cockpits won't have this)
- Repo health: which repos are clean, dirty, ahead/behind, diverged, or remote-only
- New remote commits: what arrived from other pilots or CI since last session — note authors and one-line summaries
- Unpushed work: which repos have local commits not yet on the remote
- Failed syncs: any repos where fetch/pull failed and why
- **Standalone mode**: when called independently (not from takeoff), run `git fetch --all` (without pulling) on each fleet repo to observe current state without modifying it. Derive repo paths from `state.json → cockpit.repos_dir` and `fleet` map.

**H. Pilot activity** (passed from takeoff's Step 0, or gathered fresh if called independently)
- **Skip if no pilot data is available** (cockpits without `state.json → pilots` won't have this)
- Who committed where in the last 7 days, matched via `state.json → pilots → git_names`
- Unknown authors (not matching any pilot) flagged for attention
- Cross-repo activity patterns — who is active where, and is anyone spread too thin?

### 2. Compose the Briefing

Output EXACTLY this format. Each section should be **3-8 lines** — long enough to deliver real intel, short enough to scan. Write like you're briefing a busy person who needs to make decisions, not just skim headlines.

```
WHERE WE WERE
  <What got done recently — in plain English. Synthesize from commits,
   bookmark, and project state. Focus on outcomes, not process.>
  <What did we learn or prove? What moved the needle?>
  <What got started but didn't finish? What's dangling?>
  <What arrived from remote since last session? (e.g., "Alice pushed 5 commits
   to project-b — added compression and new lifecycle tests")>
  <If first session: "First session — fresh start.">
  <If auto-closed with no bookmark context: "Last session ended without
   a debrief. Reconstructing from commits and project state.">

WHERE WE ARE
  <Big picture: what phase is the engagement/project in?>
  <Fleet health: N repos synced, any dirty/diverged/unpushed state worth noting>
  <What's moving? What momentum do we have? What's the trajectory?>
  <What's stalled or drifting? Why?>
  <What's waiting on someone else? Who, and how long?>
  <Any recent wins, risks, or shifts in direction worth noting?>

WHERE WE'RE GOING
  1. <Most impactful thing to do next — plain English, and WHY it matters>
  2. <Second priority — what it unlocks>
  3. <Third priority — what it unlocks>
  <If repos have unpushed work, suggest pushing as an action item.>
  <If something external unblocks, note what reprioritizes.>
  <These should be actionable session goals, not backlog items.>

BLOCKERS
  <Who owes us what? How long have they owed it? Is it getting stale?>
  <What can't move until something external happens?>
  <Any failed fleet syncs or diverged repos that need manual resolution?>
  <Any workarounds available, or are we truly stuck?>
  <Distinguish "waiting on a person" from "waiting on information"
   from "genuinely stuck with no path forward".>
  <Or "None" if clear skies.>
```

### Quality Checklist (before returning)

Before you return the briefing, check:
- [ ] Does WHERE WE WERE describe *outcomes*, not "session auto-closed"?
- [ ] Does WHERE WE WERE mention what arrived from remote (other pilots' work), if fleet data exists?
- [ ] Does WHERE WE ARE give the *big picture*, not task counts?
- [ ] Does WHERE WE ARE include fleet health where relevant (unpushed, dirty, diverged)?
- [ ] Does WHERE WE'RE GOING suggest *session goals*, not backlog subtask IDs?
- [ ] Does WHERE WE'RE GOING suggest pushing unpushed work if applicable?
- [ ] Does BLOCKERS flag any failed fleet syncs or diverged repos needing resolution?
- [ ] Are unknown git authors flagged if any were detected?
- [ ] Would a non-technical stakeholder understand every line?
- [ ] Is every line earning its place? Delete anything that doesn't help the pilot decide what to do.

### 3. Return

If called as a subagent (by `/takeoff`): return the formatted briefing text.
If called independently: output the briefing directly to the user.

## Rules
- Read-only. Never modify files.
- **No task IDs in the briefing.** Say "expand HubSpot API access", not "TASK-1.12".
- **No jargon without context.** If you mention "PAK", say "private app key" or just "API credentials".
- Skip sections that have no data. Don't show empty sections.
- If the cockpit is bare (no backlog, no projects, no CLAUDE.md state sections), return: "Fresh cockpit. No projects or tasks tracked yet."
- Prioritize recency. The most recently touched work goes first.
- Flag staleness. Anything untouched for 7+ days gets a "(stale)" marker.
- Adapt to what exists. Every cockpit is different — work with whatever is there.
- **Fleet data is optional**: single-repo cockpits won't have fleet or pilot data. Skip G/H gracefully — never error on missing fleet config.
- **Standalone mode**: when called independently (not from takeoff), run `git fetch --all` (no pull) on fleet repos to observe state without modifying it. Derive repo paths from `state.json → cockpit.repos_dir` and `fleet` map.
- **Pilot identity resolution**: if `state.json → pilots` exists, use `git_names` to map git authors to pilot names. Don't hardcode author-to-pilot mappings.
