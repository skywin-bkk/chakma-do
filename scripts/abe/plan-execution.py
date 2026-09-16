#!/usr/bin/env python3
"""Emit a fail-closed, repository-local execution plan for the selected ABE task."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
QUEUE = ROOT / "config/abe/task-queue.json"
RUNNER = ROOT / "build/abe/runner-state.json"
OUT = ROOT / "build/abe/execution-plan.json"


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def main():
    queue = load(QUEUE)
    runner = load(RUNNER)
    selected = runner.get("selected_task")
    safe = (
        runner.get("safe_to_proceed") is True
        and runner.get("external_writes") is False
        and runner.get("production_deploy") is False
        and runner.get("destructive_actions") is False
        and queue.get("authoritative_department_scope") == ["DO-DEP-01", "DO-DEP-14"]
        and isinstance(selected, dict)
    )
    task = next((t for t in queue.get("queue", []) if selected and t.get("id") == selected.get("id")), None)
    safe = bool(safe and task and task.get("status") == "READY" and task.get("safe_autonomous") is True)
    plan = {
        "schema_version": 1,
        "task": selected if safe else None,
        "safe_to_execute": safe,
        "scope": "repository-local",
        "allowed_actions": ["inspect", "generate", "validate", "commit-proposal"] if safe else [],
        "forbidden_actions": ["external-write", "production-deploy", "destructive-action", "secret-access", "arbitrary-command"],
        "authoritative_department_scope": ["DO-DEP-01", "DO-DEP-14"],
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(plan, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(plan, sort_keys=True))
    if not safe:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
