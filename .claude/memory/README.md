# Session Context Store - Persistent Memory System

> **Innovation:** Cross-session memory for AI agents. Decisions, patterns, and outcomes persist between conversations.

---

## Overview

The Session Context Store provides persistent memory across Claude Code sessions. Unlike traditional stateless AI interactions, this system remembers:

- **Decisions made** and their outcomes
- **Project patterns** learned over time
- **Agent performance** metrics
- **Session summaries** for context continuity

---

## Architecture

```
.claude/memory/
├── README.md                    # This file
├── decisions.jsonl              # Append-only decision log
├── project-patterns.json        # Learned project conventions
├── agent-performance.json       # Agent success metrics
└── session-summaries/           # Per-session context snapshots
    └── {session-id}.json
```

---

## File Specifications

### decisions.jsonl

**Format:** JSON Lines (append-only log)

```jsonl
{"id":"d001","timestamp":"2026-01-24T10:00:00Z","agent":"frontend-specialist","decision":"Use Zustand for state","context":"State management choice","outcome":null,"tags":["architecture","state"]}
{"id":"d002","timestamp":"2026-01-24T10:05:00Z","agent":"backend-specialist","decision":"SQLite with FTS5","context":"Search functionality","outcome":"success","tags":["database","search"]}
```

**Fields:**
| Field | Type | Description |
|-------|------|-------------|
| `id` | string | Unique decision ID (d001, d002, ...) |
| `timestamp` | ISO 8601 | When decision was made |
| `agent` | string | Which agent made the decision |
| `decision` | string | The decision taken |
| `context` | string | Why this decision was needed |
| `outcome` | null/success/failure | Result after implementation |
| `tags` | string[] | Categorization for search |

**Rules:**
- Never modify existing lines (append-only)
- Update `outcome` by appending a new line with same `id`
- Use `memory_manager.py` for all operations

---

### project-patterns.json

**Purpose:** Learned conventions from the codebase

```json
{
  "schema_version": "1.0",
  "last_updated": "2026-01-24T10:00:00Z",
  "code_style": {
    "naming": "camelCase",
    "imports": "named",
    "prefer_immutability": true,
    "string_quotes": "single"
  },
  "architecture": {
    "state_management": null,
    "api_pattern": null,
    "testing_framework": null,
    "styling": null
  },
  "preferences": {
    "communication_style": "concise",
    "risk_tolerance": "balanced",
    "documentation_level": "minimal"
  },
  "detected_stack": [],
  "custom_patterns": {}
}
```

**Auto-Learning:**
- `code_style`: Analyzed from existing code
- `architecture`: Detected from dependencies
- `preferences`: Inferred from user feedback

---

### agent-performance.json

**Purpose:** Track agent effectiveness for intelligent routing

```json
{
  "schema_version": "1.0",
  "last_updated": "2026-01-24T10:00:00Z",
  "agents": {
    "frontend-specialist": {
      "total_tasks": 0,
      "successful": 0,
      "failed": 0,
      "accuracy": 0.0,
      "avg_response_quality": 0.0,
      "specializations": [],
      "last_used": null
    }
  },
  "routing_preferences": {},
  "skill_gaps": []
}
```

**Metrics:**
- `accuracy`: successful / total_tasks
- `avg_response_quality`: User satisfaction (0-1)
- `specializations`: Domains where agent excels

---

### session-summaries/{session-id}.json

**Purpose:** Context snapshot for session continuity

```json
{
  "session_id": "abc123",
  "started_at": "2026-01-24T10:00:00Z",
  "ended_at": "2026-01-24T11:30:00Z",
  "summary": "Implemented user authentication with JWT tokens",
  "decisions_made": ["d001", "d002"],
  "files_modified": ["src/auth.ts", "src/middleware.ts"],
  "agents_used": ["backend-specialist", "security-auditor"],
  "open_tasks": [],
  "next_session_context": "Continue with password reset flow"
}
```

---

## Usage

### For Agents

```python
from .claude.core.memory_manager import MemoryManager

memory = MemoryManager()

# Log a decision
memory.log_decision(
    agent="frontend-specialist",
    decision="Use React Query for data fetching",
    context="Need caching and automatic refetching",
    tags=["architecture", "data-fetching"]
)

# Get relevant context for a task
context = memory.get_relevant_context(
    task="implement user search",
    tags=["search", "api"]
)

# Update outcome
memory.update_outcome(decision_id="d001", outcome="success")

# Get agent performance
perf = memory.get_agent_performance("frontend-specialist")
```

### For Orchestrator

```python
# Before assigning task
best_agent = memory.get_best_agent_for(
    task_type="database-migration",
    required_skills=["sql", "schema-design"]
)

# After task completion
memory.record_task_result(
    agent="database-architect",
    task="migrate users table",
    success=True,
    quality_score=0.9
)
```

---

## Integration Points

### 1. Session Start
- Load `project-patterns.json`
- Read recent `decisions.jsonl` entries
- Check for `next_session_context` in latest session summary

### 2. During Session
- Log decisions as they're made
- Update agent performance after each task
- Track files modified

### 3. Session End
- Generate session summary
- Update `project-patterns.json` if new patterns detected
- Set `next_session_context` for continuity

---

## Privacy & Security

- **Local only:** All data stored in `.claude/memory/`
- **Git-optional:** Add to `.gitignore` if sensitive
- **No external sync:** Data never leaves the machine
- **User control:** Delete any file to reset that memory type

---

## Best Practices

1. **Decision Logging:**
   - Log architectural decisions (not trivial changes)
   - Include enough context for future understanding
   - Use consistent tags for searchability

2. **Pattern Learning:**
   - Let the system learn (don't manually edit)
   - Review periodically for accuracy
   - Reset if project conventions change significantly

3. **Performance Tracking:**
   - Be honest about outcomes
   - Use for routing, not punishment
   - Identify skill gaps for improvement

---

## Troubleshooting

**Q: Memory files are getting too large**
A: Run `memory_manager.py --compact` to archive old entries

**Q: Incorrect patterns learned**
A: Delete `project-patterns.json` to reset (will re-learn)

**Q: Agent performance seems wrong**
A: Check `decisions.jsonl` for incorrectly logged outcomes

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-01-24 | Initial implementation |
