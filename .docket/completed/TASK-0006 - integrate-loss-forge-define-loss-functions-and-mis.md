---
id: TASK-0006
title: Integrate loss-forge — define loss functions and mission scores for ai-cockpit
status: Done
created: '2026-04-01'
priority: high
tags:
  - quality
  - loss-forge
  - ci
definition-of-done:
  - loss-forge /loss-init run on ai-cockpit-template
  - Loss module written with 5+ loss functions and 5+ mission scores
  - cockpit grade CLI command runs the loss check
  - Baseline snapshot committed
  - CI runs /loss-check and fails on regression
updated: '2026-04-02'
---
Use eidos-agi/loss-forge to define measurable loss functions and mission scores for the cockpit CLI. Run /loss-init to generate the loss module, then /loss-check gates PRs.

Candidate mission scores:
- M1: Install-to-first-cockpit (pip install → cockpit new → /takeoff works)
- M2: Command coverage (every CLI command has --help + test)
- M3: Fleet health (cockpit cic returns CLEAR on clean fleet)
- M4: Scaffold completeness (cockpit new produces working cockpit with all skills)
- M5: PyPI freshness (git HEAD matches published version)

Candidate loss functions:
- L1: Untested commands (commands without pytest coverage)
- L2: Stale help text (commands whose help doesn't match actual behavior)
- L3: Hardcoded paths (grep for absolute paths that aren't config-based)
- L4: Template drift (bundled template skills out of sync with repo skills)
- L5: Missing --help (commands that run instead of showing help on --help)
- L6: CLI complexity (total LOC in cli.py — should shrink or hold, not grow unbounded)

This makes every release provably better, not just bigger.

**Completion notes:** Loss module live. cockpit grade runs 6 missions (all 100%) + 6 losses (composite 1.28). Baseline committed. Next release must beat or match.
