---
id: TASK-0002
title: Configure PyPI trusted publisher for auto-publish on tag
status: Blocked
created: '2026-04-01'
priority: high
tags:
  - ci
  - pypi
definition-of-done:
  - Trusted publisher configured on pypi.org
  - GitHub environment 'pypi' created
  - Tag push triggers successful PyPI publish
updated: '2026-04-02'
blocked_reason: 'GitHub environment created. Needs manual PyPI config: pypi.org/manage/project/ai-cockpit/settings/publishing/
  → Add publisher (eidos-agi, ai-cockpit-template, publish.yml, pypi environment)'
---
Set up trusted publishing on pypi.org so the publish.yml GitHub Action can push releases without API tokens. Settings > Publishing > Add GitHub publisher: eidos-agi/ai-cockpit-template, workflow publish.yml, environment pypi.
