---
id: TASK-0003
title: Add shell completions (bash/zsh)
status: Done
created: '2026-04-01'
priority: medium
tags:
  - cli
  - ux
definition-of-done:
  - cockpit <tab> completes command names
  - cockpit <name><tab> completes registered cockpit slugs
  - Install instructions in README
updated: '2026-04-02'
---
Tab completion for cockpit commands and cockpit names. Generates completions from the registry so cockpit <tab> shows registered cockpit slugs.

**Completion notes:** Bash and zsh completions for all commands + registered cockpit names. cockpit completions bash/zsh with install instructions in --help.
