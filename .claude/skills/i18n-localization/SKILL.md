---
name: i18n-localization
description: Internationalization and localization patterns. Detecting hardcoded strings, managing translations, locale files, RTL support.
allowed-tools: Read, Glob, Grep
---

# i18n & Localization

> Internationalization (i18n) and Localization (L10n) checks.

## Script

| Script | Purpose | Command |
|--------|---------|---------|
| `scripts/i18n_checker.py` | Detect hardcoded strings & missing translations (React, Vue, Python) | `python scripts/i18n_checker.py <project_path>` |
