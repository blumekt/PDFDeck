---
name: lint-and-validate
description: Linting, type-checking and static analysis procedures per ecosystem. Use after modifying code and when the user asks to lint, format, type-check or validate code.
allowed-tools: Read, Glob, Grep, Bash
---

# Lint and Validate Skill

> Run the ecosystem's validation tools after each code change, and do not commit or report a task as done until they pass - errors left for later break the next build.

### Procedures by Ecosystem

#### Node.js / TypeScript
1. **Lint/Fix:** `npm run lint` or `npx eslint "path" --fix`
2. **Types:** `npx tsc --noEmit`
3. **Security:** `npm audit --audit-level=high`

#### Python
1. **Linter (Ruff):** `ruff check "path" --fix` (Fast & Modern)
2. **Security (Bandit):** `bandit -r "path" -ll`
3. **Types (MyPy):** `mypy "path"`

## The Quality Loop
1. **Write/Edit Code**
2. **Run Audit:** `npm run lint && npx tsc --noEmit`
3. **Analyze Report:** Read the lint and type-check output (for `scripts/lint_runner.py`: its `SUMMARY` section).
4. **Fix & Repeat:** Fix every reported error and re-run until the checks pass.

## Error Handling
- If `lint` fails: Fix the style or syntax issues immediately.
- If `tsc` fails: Correct type mismatches before proceeding.
- If no tool is configured: Check the project root for `.eslintrc`, `tsconfig.json`, `pyproject.toml` and suggest creating one.


---

## Scripts

| Script | Purpose | Command |
|--------|---------|---------|
| `scripts/lint_runner.py` | Unified lint check | `python scripts/lint_runner.py <project_path>` |
| `scripts/type_coverage.py` | Type coverage analysis | `python scripts/type_coverage.py <project_path>` |

