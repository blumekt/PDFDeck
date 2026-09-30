---
name: testing-patterns
description: Testing patterns and principles. Unit, integration, mocking strategies.
allowed-tools: Read, Write, Edit, Glob, Grep, Bash
---

# Testing Patterns

> Runs the project's tests through the kit's runner.

## Script

| Script | Purpose | Command |
|--------|---------|---------|
| `scripts/test_runner.py` | Run the test suite (Node.js: npm test / jest / vitest; Python: pytest / unittest) | `python scripts/test_runner.py <project_path> [--coverage]` |
