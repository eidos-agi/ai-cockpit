# CLAUDE.md — AI Cockpit Template

> **Fork this file.** Replace the placeholder sections with your role context, domain rules, and project structure.

## Role Context

<!-- WHO: Replace with your role, org, and mission -->
This is a Claude Code cockpit for **[YOUR ROLE]** at **[YOUR ORG]**.

## Cockpit Primitives

This workspace uses the AI Cockpit Template. These skills are always available:

| Skill | When | What |
|-------|------|------|
| `/takeoff` | Start of session | Boot sequence: bookmark → drift check → priorities → wait |
| `/touch-and-go` | Mid-session | Checkpoint: commit, push, bookmark, context compaction — keep flying |
| `/can-i-close` | Before closing | Audit 3 contracts (workspace, session, conversation) — 20 checks |
| `/land` | End of session | Park sequence — gated by `/can-i-close`. Commits, pushes, bookmarks. |
| `/cockpit-status` | Anytime | Active workstreams, blockers, ages, ownership |

## Session Protocol

1. Every session starts with `/takeoff`
2. Work using domain-specific skills and tools
3. Use `/touch-and-go` for mid-session checkpoints (saves state, compacts context)
4. When ready to stop: `/can-i-close` → fix any BLOCKs → `/land`
5. If a session crashes without `/land`, the next `/takeoff` will detect drift and flag it

**IMPORTANT:** Do NOT suggest `/land` unprompted. For mid-session saves, use `/touch-and-go`. Only `/land` when the pilot says they're done.

## Forge Ecosystem

This cockpit participates in the [Eidos forge ecosystem](https://github.com/eidos-agi/forge-forge). Forges are reusable agent knowledge that can be applied to any project.

**Discovery:** Use the forge-forge MCP server to find forges:
- `forge_find("test my code")` — find the right forge for a task
- `forge_how("loss-forge")` — how to use a specific forge
- `forge_for_project(path=".")` — what forges are recommended for this project

**Provenance:** Check `.forge/installed.yaml` (if it exists) to see which forges have already been applied to this project. Don't re-initialize a forge that's already installed — use its artifacts instead.

## State Files

- **`state.json`** — Watermarks and counters. Skills read/write this. Committed to git.
- **Bookmarks** — Written to `~/.claude/bookmarks/<session-id>-bookmark.json` by `/land`. Not in git.

## Domain Skills

<!-- LIST: Add your domain-specific skills here -->
| Skill | What It Does |
|-------|-------------|
| `/example-skill` | Placeholder — replace with your skills |

## Project Structure

<!-- STRUCTURE: Replace with your actual directory layout -->
```
your-cockpit/
├── CLAUDE.md          ← you are here
├── state.json         ← session state & watermarks
└── ...                ← your domain structure
```

## Rules

<!-- RULES: Add your domain-specific rules -->
- Soft deletes only — never hard-delete records
- No secrets in repos — use environment variables or a secrets manager
- Commit messages explain why, not just what

<!-- BACKLOG.MD MCP GUIDELINES START -->
<!-- If you use Backlog.md MCP, paste the guidelines block here -->
<!-- BACKLOG.MD MCP GUIDELINES END -->
