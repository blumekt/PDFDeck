# Project Instructions for Claude Code

> **Template:** Copy this file to your project root as `CLAUDE.md` and customize it for your project.

---

## 📋 Project Overview

**Project Name:** [Your Project Name]

**Description:** [Brief 2-3 sentence description of what this project does]

**Tech Stack:**
- **Language:** [Python / JavaScript / TypeScript / Rust / Go]
- **Framework:** [Django / FastAPI / React / Next.js / Vue / Svelte]
- **Database:** [PostgreSQL / MySQL / SQLite / MongoDB / Redis]
- **Other Key Tech:** [PyQt6 / Tailwind / Docker / etc.]

**Project Type:** [Web App / Desktop App / Mobile App / CLI Tool / Library / API]

---

## 🌐 Communication Language

**Always respond to the user in Polish (po polsku).**

---

## 🚀 Development Workflow

### Quick Start

```bash
# Clone and setup
git clone [repository-url]
cd [project-name]

# Install dependencies
[e.g., pip install -e ".[dev]" / npm install / cargo build]

# Run development
[e.g., python -m myapp / npm run dev / cargo run]

# Run tests
[e.g., pytest / npm test / cargo test]
```

### Build Commands

```bash
# Lint
[e.g., ruff check src/ / npm run lint / cargo clippy]

# Format
[e.g., ruff format src/ / npm run format / cargo fmt]

# Type check
[e.g., mypy src/ / npx tsc --noEmit / cargo check]

# Build production
[e.g., pyinstaller / npm run build / cargo build --release]
```

### Quality Checklist

Before completing any task:

- [ ] **Linting:** Code passes linter checks
- [ ] **Type checking:** No type errors
- [ ] **Tests:** Critical paths have coverage
- [ ] **Manual testing:** Feature works as expected
- [ ] **Documentation:** Updated if needed

---

## 🤖 AI Agent Framework Integration

This project uses a comprehensive AI agent framework located in `.claude/`.

### Quick Reference

- **📖 Full Guide:** See [.claude/README.md](.claude/README.md)
- **🏗️ Architecture:** See [.claude/ARCHITECTURE.md](.claude/ARCHITECTURE.md)
- **⚙️ Main Config:** See [.claude/CLAUDE.md](.claude/CLAUDE.md)

### Available Resources

- **19 Specialist Agents** in `.claude/agents/`
- **36 Skills** (domain knowledge) in `.claude/skills/`
- **Master Scripts** (validation) in `.claude/scripts/`

### Recommended Agents for This Project

> **Tip:** List 3-5 most relevant agents based on your tech stack

**For [Tech Stack Category]:**
- `[agent-name]` - [when to use, e.g., "API development, backend logic"]
- `[agent-name]` - [when to use, e.g., "React UI, frontend design"]
- `[agent-name]` - [when to use, e.g., "Schema design, queries"]

**Examples:**
- Python projects: `backend-specialist`, `test-engineer`, `debugger`
- React projects: `frontend-specialist`, `test-engineer`, `performance-optimizer`
- Mobile: `mobile-developer`, `test-engineer`, `performance-optimizer`

### Recommended Skills

> **Tip:** List 3-5 most relevant skills

- `[skill-name]` - [e.g., "python-patterns - Python best practices"]
- `[skill-name]` - [e.g., "react-patterns - React hooks, state management"]
- `[skill-name]` - [e.g., "database-design - Schema optimization"]

**Common skills for all projects:**
- `clean-code` - Coding standards (mandatory)
- `testing-patterns` - Test strategies
- `systematic-debugging` - Debug methodology

## 🏗️ Project Architecture

### Structure

```
[project-root]/
├── [config-files]         # e.g., pyproject.toml, package.json
├── [source-dir]/          # e.g., src/, lib/, app/
│   ├── [core-module]/     # Business logic
│   ├── [ui-module]/       # User interface (if applicable)
│   └── [utils-module]/    # Helper functions
├── [tests-dir]/           # Test files
├── [docs-dir]/            # Documentation
└── [resources-dir]/       # Assets, configs, etc.
```

### Architecture Pattern

**Pattern:** [MVC / MVVM / Clean Architecture / Hexagonal / Microservices / etc.]

**Key Components:**
- **[Component 1]:** [Purpose and location]
- **[Component 2]:** [Purpose and location]
- **[Component 3]:** [Purpose and location]

### Key Directories

| Directory | Purpose | Modification Rules |
|-----------|---------|-------------------|
| `[dir/]` | [purpose] | [when/how to modify] |
| `[dir/]` | [purpose] | [when/how to modify] |
| `[dir/]` | [purpose] | [when/how to modify] |

---

## 📝 Coding Standards

### Naming Conventions

- **Variables:** `[snake_case / camelCase]`
- **Functions:** `[snake_case / camelCase]`
- **Classes:** `[PascalCase]`
- **Constants:** `[SCREAMING_SNAKE_CASE / UPPER_CASE]`
- **Files:** `[kebab-case / snake_case / PascalCase]`

### Code Style

- **Indentation:** [2 spaces / 4 spaces / tabs]
- **Max line length:** [80 / 100 / 120]
- **String quotes:** [single / double]
- **Trailing commas:** [yes / no]

### Comments & Documentation

- **Docstrings:** [Google / NumPy / JSDoc style]
- **Inline comments:** [when to use]
- **TODO format:** [e.g., "# TODO(username): description"]

---

## 🧪 Testing Strategy

### Test Framework

**Framework:** [pytest / jest / vitest / cargo test / go test]

**Location:** `[tests/ / __tests__ / test/]`

### Test Types

- **Unit Tests:** `[location]` - Test individual functions/classes
- **Integration Tests:** `[location]` - Test component interactions
- **E2E Tests:** `[location]` - Test full user workflows

### Coverage

- **Target:** [80% / 90% / etc.]
- **Critical paths:** Must have 100% coverage
- **Generate report:** `[command]`

### Running Tests

```bash
# Run all tests
[command]

# Run specific test
[command with pattern]

# Run with coverage
[command with coverage flag]

# Watch mode
[command for watch mode]
```

---

## 🔧 Common Tasks

### Adding a New Feature

1. **Plan:** Break the feature into tasks (skill `plan-writing`)
2. **Design:** Enter Plan Mode (`EnterPlanMode`) for complex features
3. **Implement:**
   - Create/modify files in appropriate locations
   - Follow architecture patterns
   - Add type hints/annotations
4. **Test:** Write tests (TDD recommended)
5. **Quality:** Run lint, type check, tests
6. **Document:** Update docs if needed
7. **Commit:** Clear, descriptive commit message

### Fixing a Bug

1. **Debug:** Find the root cause first (skill `systematic-debugging`)
2. **Reproduce:** Write failing test first
3. **Fix:** Make minimal change to fix issue
4. **Verify:** Test passes, no regressions
5. **Commit:** Include issue number if applicable

### Refactoring

1. **Safety:** Ensure tests exist and pass
2. **Incremental:** Small, focused changes
3. **Test after each change:** Keep tests green
4. **Commit frequently:** Easy to revert if needed

---

## 📦 Dependencies

### Core Dependencies

> **Tip:** List main dependencies and their purpose

| Package | Version | Purpose |
|---------|---------|---------|
| `[package]` | `[version]` | [purpose] |
| `[package]` | `[version]` | [purpose] |
| `[package]` | `[version]` | [purpose] |

### Development Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| `[package]` | `[version]` | [purpose] |
| `[package]` | `[version]` | [purpose] |

### Important Notes

- **Version pinning:** [exact / compatible / latest]
- **Security updates:** [how to handle]
- **Deprecated packages:** [list any known issues]

---

## 🚢 Deployment

### Target Environments

- **Development:** [local / docker / staging server]
- **Staging:** [URL or location]
- **Production:** [URL or location]

### Deployment Method

**Method:** [Docker / Kubernetes / Vercel / PyInstaller / etc.]

**Commands:**

```bash
# Build
[build command]

# Deploy to staging
[deploy staging command]

# Deploy to production
[deploy production command]
```

### Pre-deployment Checklist

- [ ] All tests pass
- [ ] Version number updated
- [ ] Changelog updated
- [ ] Database migrations ready (if applicable)
- [ ] Environment variables configured
- [ ] Build succeeds
- [ ] Manual testing complete
- [ ] Security scan passed

---

## 🐛 Troubleshooting

### Common Issues

**Issue 1:** [Description]
```
Error message or symptoms
```
**Solution:** [Step-by-step fix]

**Issue 2:** [Description]
```
Error message or symptoms
```
**Solution:** [Step-by-step fix]

### Debug Tools

- **Logging:** [where logs are, how to enable debug mode]
- **Profiler:** [how to profile performance]
- **Debugger:** [how to attach debugger]

---

## 📚 Important Files

### Configuration Files

| File | Purpose | Modify When |
|------|---------|-------------|
| `[config-file]` | [purpose] | [when] |
| `[config-file]` | [purpose] | [when] |

### Entry Points

| File | Purpose |
|------|---------|
| `[entry-file]` | [description] |
| `[entry-file]` | [description] |

### Critical Business Logic

| File | Purpose | Extra Care Needed |
|------|---------|-------------------|
| `[file]` | [purpose] | [why critical] |
| `[file]` | [purpose] | [why critical] |

---

## 🔐 Security & Secrets

### Environment Variables

```bash
# Required variables
[VAR_NAME]=[description]
[VAR_NAME]=[description]

# Optional variables
[VAR_NAME]=[description]
```

**Storage:**
- Development: `[.env / .env.local]`
- Production: `[vault / secrets manager]`

### API Keys

- **[Service Name]:** [how to obtain, where to configure]
- **[Service Name]:** [how to obtain, where to configure]

**⚠️ Never commit secrets to git!**

---

## 📖 Resources

### Documentation

- **Project Docs:** `[docs/ or wiki URL]`
- **API Docs:** `[URL or file]`
- **Design System:** `[URL or file]`

### External Resources

- **Official Docs:** [links to framework/library docs]
- **Tutorials:** [helpful tutorials for this stack]
- **Community:** [Discord / Slack / Forum]

### Issue Tracking

- **Issues:** [GitHub Issues / Jira / etc.]
- **Project Board:** [URL if applicable]

---

## 💡 Notes for Claude

### When to Use Plan Mode

**✅ Use Plan Mode (EnterPlanMode) for:**
- New features affecting multiple files
- Architectural changes
- Complex refactoring
- Database schema changes
- API design

**❌ Don't use Plan Mode for:**
- Simple bug fixes (single file)
- Documentation updates
- Minor style/formatting changes
- Obvious typo fixes

### Project-Specific Quirks

> **Tip:** Document any unusual patterns or decisions in the codebase

- [Quirk 1: e.g., "We use sync code instead of async because..."]
- [Quirk 2: e.g., "The XYZ module is intentionally tightly coupled because..."]
- [Quirk 3: e.g., "Tests for module ABC are in a separate repo because..."]

### Performance Considerations

- [Important performance constraint or optimization]
- [Cache strategy or concern]
- [Known bottlenecks]

---

## ✅ Task Completion Checklist

Before marking any task as complete:

- [ ] **Functionality:** Feature works as specified
- [ ] **Tests:** New tests added, all tests pass
- [ ] **Linting:** No lint errors or warnings
- [ ] **Type checking:** No type errors
- [ ] **Documentation:** Updated if needed
- [ ] **Manual testing:** Verified in development environment
- [ ] **Code review ready:** Clean, readable code

---

## 📝 Changelog & Versioning

**Versioning Scheme:** [SemVer / CalVer / Custom]

**Current Version:** `[x.y.z]`

**Version Update Rules:**
- **Major (x.0.0):** [breaking changes]
- **Minor (x.y.0):** [new features, backward compatible]
- **Patch (x.y.z):** [bug fixes]

**Changelog Location:** `[CHANGELOG.md / releases page]`

---

## 🙏 Credits

