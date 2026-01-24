#!/usr/bin/env python3
"""
Memory Manager - Core module for Session Context Store

Provides persistent memory across Claude Code sessions:
- Decision logging with outcome tracking
- Project pattern learning
- Agent performance metrics
- Session summaries for continuity

Usage:
    from memory_manager import MemoryManager
    memory = MemoryManager()
    memory.log_decision(agent="frontend-specialist", decision="...", context="...")
"""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Optional, Any
import uuid


class MemoryManager:
    """Manages persistent memory across Claude Code sessions."""

    def __init__(self, base_path: Optional[Path] = None):
        """Initialize MemoryManager with path to .claude directory."""
        if base_path is None:
            # Auto-detect .claude directory
            script_dir = Path(__file__).parent
            base_path = script_dir.parent  # .claude/

        self.base_path = Path(base_path)
        self.memory_path = self.base_path / "memory"

        # Ensure directories exist
        self.memory_path.mkdir(parents=True, exist_ok=True)
        (self.memory_path / "session-summaries").mkdir(exist_ok=True)

        # File paths
        self.decisions_file = self.memory_path / "decisions.jsonl"
        self.patterns_file = self.memory_path / "project-patterns.json"
        self.performance_file = self.memory_path / "agent-performance.json"

    # =========================================================================
    # DECISION LOGGING
    # =========================================================================

    def log_decision(
        self,
        agent: str,
        decision: str,
        context: str,
        tags: Optional[list[str]] = None,
        decision_id: Optional[str] = None
    ) -> str:
        """
        Log a decision to decisions.jsonl.

        Args:
            agent: Which agent made the decision
            decision: The decision taken
            context: Why this decision was needed
            tags: Optional categorization tags
            decision_id: Optional custom ID (auto-generated if not provided)

        Returns:
            The decision ID
        """
        if decision_id is None:
            decision_id = f"d{uuid.uuid4().hex[:8]}"

        entry = {
            "id": decision_id,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "agent": agent,
            "decision": decision,
            "context": context,
            "outcome": None,
            "tags": tags or []
        }

        with open(self.decisions_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")

        return decision_id

    def update_outcome(
        self,
        decision_id: str,
        outcome: str,
        notes: Optional[str] = None
    ) -> bool:
        """
        Update the outcome of a decision.

        Args:
            decision_id: The decision to update
            outcome: "success", "failure", or "partial"
            notes: Optional notes about the outcome

        Returns:
            True if decision was found and updated
        """
        # Find the original decision
        original = None
        for decision in self.get_all_decisions():
            if decision["id"] == decision_id and decision["outcome"] is None:
                original = decision
                break

        if original is None:
            return False

        # Append outcome update
        update_entry = {
            "id": decision_id,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "outcome": outcome,
            "outcome_notes": notes,
            "_type": "outcome_update"
        }

        with open(self.decisions_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(update_entry, ensure_ascii=False) + "\n")

        # Update agent performance
        if original:
            self._update_agent_stats(original["agent"], outcome == "success")

        return True

    def get_all_decisions(self) -> list[dict]:
        """Get all decisions from the log."""
        if not self.decisions_file.exists():
            return []

        decisions = []
        with open(self.decisions_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        decisions.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue

        return decisions

    def get_relevant_context(
        self,
        task: str,
        tags: Optional[list[str]] = None,
        limit: int = 10
    ) -> list[dict]:
        """
        Get decisions relevant to a task.

        Args:
            task: Description of the current task
            tags: Optional tags to filter by
            limit: Maximum number of decisions to return

        Returns:
            List of relevant decisions, most recent first
        """
        all_decisions = self.get_all_decisions()

        # Filter out outcome updates
        decisions = [d for d in all_decisions if d.get("_type") != "outcome_update"]

        # Apply outcome updates
        outcomes = {d["id"]: d for d in all_decisions if d.get("_type") == "outcome_update"}
        for decision in decisions:
            if decision["id"] in outcomes:
                decision["outcome"] = outcomes[decision["id"]]["outcome"]

        # Filter by tags if provided
        if tags:
            tag_set = set(tags)
            decisions = [
                d for d in decisions
                if tag_set.intersection(set(d.get("tags", [])))
            ]

        # Sort by timestamp (newest first) and limit
        decisions.sort(key=lambda d: d.get("timestamp", ""), reverse=True)
        return decisions[:limit]

    # =========================================================================
    # PROJECT PATTERNS
    # =========================================================================

    def get_patterns(self) -> dict:
        """Get current project patterns."""
        if not self.patterns_file.exists():
            return self._default_patterns()

        try:
            with open(self.patterns_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return self._default_patterns()

    def update_patterns(self, updates: dict) -> None:
        """
        Update project patterns.

        Args:
            updates: Dictionary of pattern updates (will be merged)
        """
        patterns = self.get_patterns()

        # Deep merge
        self._deep_merge(patterns, updates)
        patterns["last_updated"] = datetime.utcnow().isoformat() + "Z"

        with open(self.patterns_file, "w", encoding="utf-8") as f:
            json.dump(patterns, f, indent=2, ensure_ascii=False)

    def learn_patterns_from_code(self, file_path: str, content: str) -> dict:
        """
        Analyze code to learn patterns.

        Args:
            file_path: Path to the file
            content: File content

        Returns:
            Detected patterns
        """
        detected = {}

        # Detect string quotes
        single_quotes = content.count("'")
        double_quotes = content.count('"')
        if single_quotes > double_quotes * 1.5:
            detected["string_quotes"] = "single"
        elif double_quotes > single_quotes * 1.5:
            detected["string_quotes"] = "double"

        # Detect indentation
        lines = content.split("\n")
        two_space = sum(1 for line in lines if line.startswith("  ") and not line.startswith("    "))
        four_space = sum(1 for line in lines if line.startswith("    "))
        tab_indent = sum(1 for line in lines if line.startswith("\t"))

        if tab_indent > two_space and tab_indent > four_space:
            detected["indentation"] = "tabs"
        elif four_space > two_space:
            detected["indentation"] = "4-spaces"
        elif two_space > 0:
            detected["indentation"] = "2-spaces"

        # Detect import style (for JS/TS)
        if file_path.endswith((".js", ".ts", ".jsx", ".tsx")):
            named_imports = content.count("import {")
            default_imports = content.count("import ") - named_imports
            if named_imports > default_imports:
                detected["imports"] = "named"
            elif default_imports > named_imports:
                detected["imports"] = "default"

        return detected

    def _default_patterns(self) -> dict:
        """Return default patterns structure."""
        return {
            "schema_version": "1.0",
            "last_updated": None,
            "code_style": {
                "naming": None,
                "imports": None,
                "prefer_immutability": None,
                "string_quotes": None,
                "indentation": None,
                "max_line_length": None
            },
            "architecture": {
                "state_management": None,
                "api_pattern": None,
                "testing_framework": None,
                "styling": None,
                "bundler": None,
                "package_manager": None
            },
            "preferences": {
                "communication_style": "concise",
                "risk_tolerance": "balanced",
                "documentation_level": "minimal"
            },
            "detected_stack": [],
            "custom_patterns": {}
        }

    def _deep_merge(self, base: dict, updates: dict) -> None:
        """Deep merge updates into base dict."""
        for key, value in updates.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                self._deep_merge(base[key], value)
            else:
                base[key] = value

    # =========================================================================
    # AGENT PERFORMANCE
    # =========================================================================

    def get_agent_performance(self, agent: Optional[str] = None) -> dict:
        """
        Get agent performance metrics.

        Args:
            agent: Specific agent name, or None for all agents

        Returns:
            Performance data
        """
        if not self.performance_file.exists():
            return self._default_performance()

        try:
            with open(self.performance_file, "r", encoding="utf-8") as f:
                data = json.load(f)
        except (json.JSONDecodeError, IOError):
            data = self._default_performance()

        if agent:
            return data.get("agents", {}).get(agent, self._default_agent_stats())
        return data

    def record_task_result(
        self,
        agent: str,
        task: str,
        success: bool,
        quality_score: Optional[float] = None
    ) -> None:
        """
        Record task completion result for an agent.

        Args:
            agent: Agent that performed the task
            task: Task description
            success: Whether task succeeded
            quality_score: Optional quality rating (0.0 - 1.0)
        """
        data = self.get_agent_performance()

        if "agents" not in data:
            data["agents"] = {}

        if agent not in data["agents"]:
            data["agents"][agent] = self._default_agent_stats()

        stats = data["agents"][agent]
        stats["total_tasks"] += 1
        if success:
            stats["successful"] += 1
        else:
            stats["failed"] += 1

        # Recalculate accuracy
        stats["accuracy"] = round(stats["successful"] / stats["total_tasks"], 3)

        # Update quality score (rolling average)
        if quality_score is not None:
            current_quality = stats.get("avg_response_quality", 0.0)
            total = stats["total_tasks"]
            stats["avg_response_quality"] = round(
                (current_quality * (total - 1) + quality_score) / total, 3
            )

        stats["last_used"] = datetime.utcnow().isoformat() + "Z"
        data["last_updated"] = datetime.utcnow().isoformat() + "Z"

        with open(self.performance_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def get_best_agent_for(
        self,
        task_type: str,
        required_skills: Optional[list[str]] = None
    ) -> Optional[str]:
        """
        Get the best agent for a task type based on performance history.

        Args:
            task_type: Type of task (e.g., "database-migration")
            required_skills: Optional required skills

        Returns:
            Best agent name or None if no data
        """
        data = self.get_agent_performance()
        agents = data.get("agents", {})

        if not agents:
            return None

        # Score agents
        scored = []
        for name, stats in agents.items():
            if stats["total_tasks"] < 1:
                continue

            # Check skill match if required
            if required_skills:
                agent_skills = set(stats.get("specializations", []))
                if not set(required_skills).intersection(agent_skills):
                    continue

            score = stats["accuracy"] * 0.6 + stats.get("avg_response_quality", 0.5) * 0.4
            scored.append((name, score))

        if not scored:
            return None

        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[0][0]

    def _update_agent_stats(self, agent: str, success: bool) -> None:
        """Update agent stats from decision outcome."""
        self.record_task_result(agent, "decision", success)

    def _default_performance(self) -> dict:
        """Return default performance structure."""
        return {
            "schema_version": "1.0",
            "last_updated": None,
            "agents": {},
            "routing_preferences": {},
            "skill_gaps": []
        }

    def _default_agent_stats(self) -> dict:
        """Return default agent stats structure."""
        return {
            "total_tasks": 0,
            "successful": 0,
            "failed": 0,
            "accuracy": 0.0,
            "avg_response_quality": 0.0,
            "specializations": [],
            "last_used": None
        }

    # =========================================================================
    # SESSION SUMMARIES
    # =========================================================================

    def create_session_summary(
        self,
        session_id: str,
        summary: str,
        decisions_made: list[str],
        files_modified: list[str],
        agents_used: list[str],
        open_tasks: Optional[list[str]] = None,
        next_session_context: Optional[str] = None
    ) -> None:
        """
        Create a session summary for continuity.

        Args:
            session_id: Unique session identifier
            summary: Brief summary of what was done
            decisions_made: List of decision IDs made this session
            files_modified: List of files modified
            agents_used: List of agents used
            open_tasks: Optional list of unfinished tasks
            next_session_context: Optional context for next session
        """
        summary_data = {
            "session_id": session_id,
            "started_at": None,  # Could be tracked separately
            "ended_at": datetime.utcnow().isoformat() + "Z",
            "summary": summary,
            "decisions_made": decisions_made,
            "files_modified": files_modified,
            "agents_used": agents_used,
            "open_tasks": open_tasks or [],
            "next_session_context": next_session_context
        }

        summary_file = self.memory_path / "session-summaries" / f"{session_id}.json"
        with open(summary_file, "w", encoding="utf-8") as f:
            json.dump(summary_data, f, indent=2, ensure_ascii=False)

    def get_latest_session(self) -> Optional[dict]:
        """Get the most recent session summary."""
        summaries_dir = self.memory_path / "session-summaries"
        if not summaries_dir.exists():
            return None

        files = list(summaries_dir.glob("*.json"))
        if not files:
            return None

        # Sort by modification time
        files.sort(key=lambda f: f.stat().st_mtime, reverse=True)

        try:
            with open(files[0], "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return None

    def get_next_session_context(self) -> Optional[str]:
        """Get the context hint from the previous session."""
        latest = self.get_latest_session()
        if latest:
            return latest.get("next_session_context")
        return None

    # =========================================================================
    # UTILITIES
    # =========================================================================

    def compact(self, keep_days: int = 30) -> dict:
        """
        Compact old entries to reduce file size.

        Args:
            keep_days: Number of days to keep in active log

        Returns:
            Statistics about compaction
        """
        from datetime import timedelta

        cutoff = datetime.utcnow() - timedelta(days=keep_days)
        cutoff_str = cutoff.isoformat() + "Z"

        decisions = self.get_all_decisions()
        kept = []
        archived = []

        for decision in decisions:
            if decision.get("timestamp", "") >= cutoff_str:
                kept.append(decision)
            else:
                archived.append(decision)

        # Rewrite decisions file with only kept entries
        if archived:
            with open(self.decisions_file, "w", encoding="utf-8") as f:
                for decision in kept:
                    f.write(json.dumps(decision, ensure_ascii=False) + "\n")

            # Save archived to separate file
            archive_file = self.memory_path / f"decisions-archive-{datetime.utcnow().strftime('%Y%m%d')}.jsonl"
            with open(archive_file, "a", encoding="utf-8") as f:
                for decision in archived:
                    f.write(json.dumps(decision, ensure_ascii=False) + "\n")

        return {
            "kept": len(kept),
            "archived": len(archived),
            "archive_file": str(archive_file) if archived else None
        }

    def stats(self) -> dict:
        """Get memory system statistics."""
        decisions = self.get_all_decisions()
        performance = self.get_agent_performance()
        patterns = self.get_patterns()

        # Count session summaries
        summaries_dir = self.memory_path / "session-summaries"
        session_count = len(list(summaries_dir.glob("*.json"))) if summaries_dir.exists() else 0

        return {
            "total_decisions": len([d for d in decisions if d.get("_type") != "outcome_update"]),
            "decisions_with_outcomes": len([d for d in decisions if d.get("outcome") is not None]),
            "agents_tracked": len(performance.get("agents", {})),
            "patterns_learned": sum(
                1 for v in patterns.get("code_style", {}).values() if v is not None
            ),
            "session_summaries": session_count,
            "files": {
                "decisions": self.decisions_file.exists(),
                "patterns": self.patterns_file.exists(),
                "performance": self.performance_file.exists()
            }
        }


# =============================================================================
# CLI Interface
# =============================================================================

def main():
    """CLI interface for memory manager."""
    import argparse

    parser = argparse.ArgumentParser(description="Memory Manager CLI")
    parser.add_argument("--stats", action="store_true", help="Show memory statistics")
    parser.add_argument("--compact", type=int, metavar="DAYS", help="Compact entries older than DAYS")
    parser.add_argument("--context", action="store_true", help="Show next session context")
    parser.add_argument("--patterns", action="store_true", help="Show learned patterns")
    parser.add_argument("--agents", action="store_true", help="Show agent performance")

    args = parser.parse_args()
    memory = MemoryManager()

    if args.stats:
        stats = memory.stats()
        print("=== Memory System Statistics ===")
        for key, value in stats.items():
            if isinstance(value, dict):
                print(f"{key}:")
                for k, v in value.items():
                    print(f"  {k}: {v}")
            else:
                print(f"{key}: {value}")

    elif args.compact:
        result = memory.compact(args.compact)
        print(f"Compacted: kept {result['kept']}, archived {result['archived']}")
        if result['archive_file']:
            print(f"Archive: {result['archive_file']}")

    elif args.context:
        context = memory.get_next_session_context()
        if context:
            print(f"Next session context: {context}")
        else:
            print("No context from previous session")

    elif args.patterns:
        patterns = memory.get_patterns()
        print(json.dumps(patterns, indent=2))

    elif args.agents:
        perf = memory.get_agent_performance()
        print(json.dumps(perf, indent=2))

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
