# Learning Browser — Cockpit Plugin

Persistent browser memory for AI agents. The browser gets smarter every time it visits a site.

## How It Works

Three operations, all file-based:

### 1. Query (before acting)

Before navigating any site, check what you already know:

```
Read files in tools/learning-browser/sites/<domain>/
```

If files exist, you've been here before. Read them. Act on what you know instead of fumbling through the UI again.

### 2. Ingest (after success)

When you figure out how to do something on a site, write it down:

```
tools/learning-browser/sites/chase.com/download-statements.md
```

One file per learned action. Contains: what you did, what worked, what to watch out for, when you learned it.

### 3. Consolidate (on /land or periodically)

Review site learnings. Merge redundant ones. Flag stale ones (sites change). Generate cross-site insights ("all bank portals require dismissing a cookie modal first").

Written to `tools/learning-browser/insights/`.

## File Structure

```
tools/learning-browser/
├── README.md
├── sites/                     # One folder per domain
│   ├── chase.com/
│   │   ├── login.md           # How login works (modals, 2FA flow)
│   │   ├── download-statements.md
│   │   └── check-balance.md
│   ├── wellsfargo.com/
│   │   ├── login.md
│   │   └── download-statements.md
│   └── mercury.com/
│       └── export-transactions.md
├── insights/                  # Cross-site consolidated knowledge
│   ├── bank-portals.md        # "All banks require modal dismissal"
│   └── download-patterns.md   # "PDFs usually behind shadow DOM"
└── .profile/                  # Browser profile (gitignored)
```

## Memory File Format

Each file in `sites/<domain>/` follows this structure:

```markdown
# <Action Name>
**Site:** <domain>
**Last verified:** <date>
**Confidence:** high | medium | low

## Steps
1. <what to do first>
2. <what to do next>
3. ...

## Selectors / Landmarks
- Login button: `@ref` or CSS selector or text content
- Statement link: description of where it lives in the page

## Gotchas
- <thing that tripped you up>
- <thing that changed since last time>

## History
- <date>: Learned initial flow
- <date>: Nav changed, updated step 3
```

## The Loop

This is the discipline. Every browser interaction follows it:

```
QUERY   → ls sites/<domain>/ — do I know this site?
          YES → read the relevant file, follow it
          NO  → explore carefully, take snapshots

ACT     → do the thing using agent-browser

INGEST  → did I learn something new?
          YES → write/update a file in sites/<domain>/
          NO  → move on

(on /land or when idle)
CONSOLIDATE → review recent learnings
              merge duplicates
              flag anything older than 30 days as "needs reverify"
              write cross-site insights
```

## Setup

1. Install agent-browser: `npm i -g @anthropic/agent-browser`
2. Create profile: `mkdir -p tools/learning-browser/.profile`
3. Gitignore the profile: `echo "tools/learning-browser/.profile/" >> .gitignore`
4. Add the CLAUDE.md block below

## CLAUDE.md Addition

```markdown
## Browser Memory
- Before ANY browser navigation: check `tools/learning-browser/sites/<domain>/` for prior knowledge
- After figuring out a site interaction: write the pattern to `sites/<domain>/<action>.md`
- Use `agent-browser` with `--profile tools/learning-browser/.profile --headed`
- On /land: consolidate recent browser learnings if any new ones were written
```

## Why Files

- `git diff` shows exactly what the browser learned
- Move a learning to another cockpit: copy the file
- Delete a bad learning: delete the file
- Review what the browser knows: `ls sites/`
- No database, no embeddings, no infrastructure
- The LLM reads the files directly — it IS the retrieval engine

## Customization

Each cockpit forks this plugin and grows its own site knowledge. A finance cockpit learns bank portals. A security cockpit learns vulnerability databases. A planning cockpit learns vendor sites.

The `sites/` directory is the cockpit's browser muscle memory.
