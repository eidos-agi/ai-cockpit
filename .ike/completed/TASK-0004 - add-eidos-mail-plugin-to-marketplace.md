---
id: TASK-0004
title: Add eidos-mail plugin to marketplace
status: Done
created: '2026-04-01'
priority: medium
tags:
  - marketplace
  - eidos-mail
definition-of-done:
  - eidos-mail has pyproject.toml with MCP entry point
  - eidos-marketplace has plugins/eidos-mail/ with plugin.json + .mcp.json
  - claude plugins install eidos-mail works
updated: '2026-04-02'
---
Security audit passed. Needs: pyproject.toml with MCP entry point in eidos-mail, then plugin.json + .mcp.json in eidos-marketplace.

**Completion notes:** eidos-mail v0.1.0 on PyPI. Plugin added to eidos-marketplace. claude plugins install eidos-mail works via uvx.
