#!/usr/bin/env python3
"""Write deterministic repository-local ABE audit evidence without external side effects."""
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
QUEUE = ROOT / "config/abe/task-queue.json"
RUNNER = ROOT / "build/abe/runner-state.json"
PLAN = ROOT / "build/abe/execution-plan.json"
OUT = ROOT / "build/abe/audit-ledger.json"


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def digest(obj):
    payload = json.dumps(obj, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def main():
    queue = load(QUEUE)
    runner = load(RUNNER)
    plan = load(PLAN)
    selected = runner.get("selected_task")
    safe = (
        plan.get("safe_to_execute") is True
        and plan.get("task") == selected
        and plan.get("scope") == "repository-local"
        and plan.get("authoritative_department_scope") == ["DO-DEP-01", "DO-DEP-14"]
        and queue.get("authoritative_department_scope") == ["DO-DEP-01", "DO-DEP-14"]
        and runner.get("external_writes") is False
        and runner.get("production_deploy") is False
        and runner.get("destructive_actions") is False
    )
    if not safe:
        raise SystemExit("Refusing to write audit ledger: execution plan is not safe")

    ledger = {
        "schema_version": 1,
        "recorded_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "task_id": selected.get("id"),
        "task_title": selected.get("title"),
        "scope": "repository-local",
        "decision": "SAFE_TO_EXECUTE_REPOSITORY_LOCAL",
        "authoritative_department_scope": ["DO-DEP-01", "DO-DEP-14"],
        "controls": {
            "external_writes": False,
            "production_deploy": False,
            "destructive_actions": False,
            "secret_access": False,
            "arbitrary_commands": False,
        },
        "evidence_sha256": {
            "queue": digest(queue),
            "runner_state": digest(runner),
            "execution_plan": digest(plan),
        },
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(ledger, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(ledger, sort_keys=True))


if __name__ == "__main__":
    main()
