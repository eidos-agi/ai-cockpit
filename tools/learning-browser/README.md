# Learning Browser

Persistent browser-based research tool for cockpits, powered by [agent-browser](https://github.com/anthropics/agent-browser).

## What This Is

A cockpit tool for conducting web research that persists across sessions and even across days. Uses `agent-browser` with a per-cockpit profile to maintain cookies, sessions, and login state.

## Setup

### 1. Install agent-browser

```bash
npm install -g @anthropic/agent-browser
# or
brew install agent-browser
```

Verify: `which agent-browser` should return a path.

### 2. Create a profile directory

Each cockpit gets its own browser profile so sessions don't cross-contaminate:

```bash
mkdir -p .agent-browser-profile
echo ".agent-browser-profile/" >> .gitignore
```

The profile directory stores cookies, local storage, and session data. **Never commit it** — it contains authentication state.

### 3. Configure in CLAUDE.md

Add to your cockpit's CLAUDE.md:

```markdown
## Browser Research
- Use `agent-browser` for all web research
- Profile: `--profile <cockpit-root>/.agent-browser-profile --headed`
- First call must include `--profile` and `--headed` (daemon remembers after that until `close`)
- Key commands: `open <url>`, `snapshot -i`, `click @ref`, `fill @ref "text"`, `download <sel> <path>`, `wait <sel|ms>`, `screenshot [path]`, `close`
```

## Usage

### Starting a research session

```bash
# Open a page (first call starts the daemon with the profile)
agent-browser --profile .agent-browser-profile --headed open "https://example.com"

# Take a snapshot to see what's on the page
agent-browser snapshot -i

# Interact
agent-browser click @14
agent-browser fill @7 "search query"
```

### Keeping sessions alive across days

The agent-browser daemon persists until explicitly closed. This means:

1. **Don't call `close`** at the end of a session unless you're done with that site
2. **Cookies persist** in the profile directory — logged-in sessions survive restarts
3. **On next session**, just call `agent-browser snapshot -i` to see where you left off
4. If the daemon died (machine restart), re-open with `--profile` and cookies will restore most sessions

### Saving research findings

Store learnings from browser research in the cockpit's learnings system:

```bash
# If the cockpit has a learnings CLI
<cockpit-cli> learnings add "Finding from research" -c pattern -t "browser,research"

# Or use the MCP tool
finance_add_learning(content="...", category="pattern", tags=["browser", "research"])
```

### Screenshots for evidence

```bash
agent-browser screenshot research/screenshot-2026-03-10.png
```

Store screenshots in a `research/` directory (add to .gitignore if they're large).

## Tips

- **Always use `--headed`** so you can see what the browser is doing
- **One profile per cockpit** — don't share profiles between cockpits
- **Log in manually first** if a site needs 2FA — the profile will remember the session
- **Use `snapshot -i`** liberally — it's the cheapest way to see page state
- **Don't trigger alerts/confirms** — they block the browser event loop. Use `console.log` + `read_console_messages` for debugging instead.

## File Structure

```
tools/learning-browser/
├── README.md          ← you are here
└── learnings/         ← store research notes here (optional)
```
