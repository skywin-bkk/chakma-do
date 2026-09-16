#!/usr/bin/env python3
"""Controlled ABE runner foundation.

Plans exactly one safe repository-local task per invocation. It never performs
external writes, production deployment, destructive actions, or arbitrary
commands. Execution handlers must be explicitly registered in HANDLERS.
"""
import json
from datetime import datetime, timezone
from pathlib import Path

QUEUE = Path("config/abe/task-queue.json")
OUT = Path("generated/abe/runner-execution.json")

HANDLERS = {
    "ABE-009": "runner-foundation-self-check",
}


def load_queue():
    data = json.loads(QUEUE.read_text())
    rules = data.get("rules", {})
    if not (
        rules.get("external_writes") is False
        and rules.get("production_deploy") is False
        and rules.get("destructive_actions") is False
    ):
        raise RuntimeError("safety rules are not fail-closed")
    return data


def select(data):
    for task in data.get("queue", []):
        if task.get("status") != "READY":
            continue
        if task.get("safe_autonomous") is not True:
            raise RuntimeError(f"READY task {task.get('id')} is not safe_autonomous")
        if task.get("id") not in HANDLERS:
            raise RuntimeError(f"READY task {task.get('id')} has no allowlisted handler")
        return task
    return None


def main():
    data = load_queue()
    task = select(data)
    state = {
        "schema_version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "mode": data.get("mode"),
        "selected_task": None,
        "action": "IDLE",
        "safety": {
            "external_writes": False,
            "production_deploy": False,
            "destructive_actions": False,
        },
    }
    if task:
        state["selected_task"] = {"id": task["id"], "title": task["title"]}
        state["action"] = "PLAN_ONLY"
        state["handler"] = HANDLERS[task["id"]]

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(state, indent=2) + "\n")
    print(json.dumps(state, indent=2))


if __name__ == "__main__":
    main()
