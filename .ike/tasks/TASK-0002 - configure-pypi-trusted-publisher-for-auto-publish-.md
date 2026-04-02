---
id: TASK-0002
title: Configure PyPI trusted publisher for auto-publish on tag
status: To Do
created: '2026-04-01'
priority: high
tags:
  - ci
  - pypi
definition-of-done:
  - Trusted publisher configured on pypi.org
  - GitHub environment 'pypi' created
  - Tag push triggers successful PyPI publish
---
Set up trusted publishing on pypi.org so the publish.yml GitHub Action can push releases without API tokens. Settings > Publishing > Add GitHub publisher: eidos-agi/ai-cockpit-template, workflow publish.yml, environment pypi.
