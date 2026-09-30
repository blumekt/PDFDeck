---
name: webapp-testing
description: Web application testing principles. E2E, Playwright, deep audit strategies.
allowed-tools: Read, Write, Edit, Glob, Grep, Bash
---

# Web App Testing

> Browser checks of a running app through the kit's Playwright runner.

## Script

| Script | Purpose | Usage |
|--------|---------|-------|
| `scripts/playwright_runner.py` | Basic browser test | `python scripts/playwright_runner.py <url>` |
| | With screenshot | `python scripts/playwright_runner.py <url> --screenshot` |
| | Accessibility check | `python scripts/playwright_runner.py <url> --a11y` |

**Requires:** `pip install playwright && playwright install chromium`
