---
id: TASK-0005
title: Sync new skills to existing cockpits
status: Done
created: '2026-04-01'
priority: medium
tags:
  - skills
  - fleet
definition-of-done:
  - All active cockpits have touch-and-go and can-i-close skills
  - Updated /land skill deployed to all cockpits
updated: '2026-04-02'
---
touch-and-go and can-i-close skills exist in the template but haven't been pushed to downstream cockpits (cockpit-eidos, cockpit-daniel, etc). Run bin/sync-skills or update-from-template.

**Completion notes:** Synced can-i-close, touch-and-go, and updated land to all 10 registered cockpits. 8 committed, 5 pushed. cockpit-eidos and aic-ciso had pre-commit hook issues, 3 had no remote configured.
