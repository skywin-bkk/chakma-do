#!/usr/bin/env python3
"""Fail-closed deterministic selector for the controlled ABE task queue."""
import json
from pathlib import Path

QUEUE = Path("config/abe/task-queue.json")
OUT = Path("generated/abe/runner-state.json")


def main():
    data = json.loads(QUEUE.read_text())
    rules = data.get("rules", {})
    safe_rules = (
        rules.get("external_writes") is False
        and rules.get("production_deploy") is False
        and rules.get("destructive_actions") is False
    )
    selected = None
    blocked_reason = None
    if not safe_rules:
        blocked_reason = "queue safety rules are not fail-closed"
    else:
        for task in data.get("queue", []):
            if task.get("status") == "READY":
                if task.get("safe_autonomous") is not True:
                    blocked_reason = f"next READY task {task.get('id')} is not safe_autonomous"
                else:
                    selected = {"id": task.get("id"), "title": task.get("title")}
                break

    state = {
        "schema_version": 1,
        "mode": data.get("mode"),
        "authoritative_department_scope": data.get("authoritative_department_scope"),
        "selected_task": selected,
        "blocked": blocked_reason is not None,
        "blocked_reason": blocked_reason,
        "safety": {
            "external_writes": rules.get("external_writes"),
            "production_deploy": rules.get("production_deploy"),
            "destructive_actions": rules.get("destructive_actions"),
        },
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(state, indent=2) + "\n")
    print(json.dumps(state, indent=2))
    if blocked_reason:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
