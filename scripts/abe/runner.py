#!/usr/bin/env python3
"""Deterministic, fail-closed ABE runner foundation.

Selects repository-local work only. It cannot deploy, write external systems,
run destructive actions, or execute arbitrary queue-provided commands.
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
QUEUE = ROOT / "config/abe/task-queue.json"
PLAN = ROOT / "config/abe/build-plan.json"
STATE = ROOT / "build/abe/runner-state.json"


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def main():
    queue = load(QUEUE)
    plan = load(PLAN)
    safe_global = (
        queue.get("mode") == "controlled-autonomous"
        and plan.get("mode") == "controlled-autonomous"
        and plan.get("production_deploy") is False
        and plan.get("destructive_actions") is False
        and queue.get("rules", {}).get("external_writes") is False
        and queue.get("rules", {}).get("production_deploy") is False
        and queue.get("rules", {}).get("destructive_actions") is False
        and queue.get("authoritative_department_scope") == ["DO-DEP-01", "DO-DEP-14"]
    )
    selected = None
    blocked_reason = None
    if safe_global:
        for task in queue.get("queue", []):
            if task.get("status") == "READY":
                if task.get("safe_autonomous") is True:
                    selected = {"id": task["id"], "title": task["title"]}
                else:
                    blocked_reason = f"next READY task {task.get('id')} is not safe_autonomous"
                break
    else:
        blocked_reason = "global safety invariants failed"

    state = {
        "schema_version": 1,
        "mode": "controlled-autonomous",
        "safe_to_proceed": bool(safe_global and selected),
        "selected_task": selected,
        "blocked_reason": blocked_reason,
        "production_deploy": False,
        "destructive_actions": False,
        "external_writes": False,
    }
    STATE.parent.mkdir(parents=True, exist_ok=True)
    STATE.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(state, sort_keys=True))
    if not safe_global or blocked_reason:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
