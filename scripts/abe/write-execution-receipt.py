#!/usr/bin/env python3
"""Emit a deterministic, repository-local execution receipt for the selected ABE task."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
QUEUE = ROOT / "config/abe/task-queue.json"
RUNNER = ROOT / "build/abe/runner-state.json"
PLAN = ROOT / "build/abe/execution-plan.json"
LEDGER = ROOT / "build/abe/audit-ledger.json"
OUT = ROOT / "build/abe/execution-receipt.json"


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def digest(obj):
    payload = json.dumps(obj, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def main():
    queue = load(QUEUE)
    runner = load(RUNNER)
    plan = load(PLAN)
    ledger = load(LEDGER)
    selected = runner.get("selected_task")
    task = next((t for t in queue.get("queue", []) if selected and t.get("id") == selected.get("id")), None)
    controls = ledger.get("controls", {})
    safe = (
        isinstance(selected, dict)
        and task is not None
        and task.get("status") == "READY"
        and task.get("safe_autonomous") is True
        and runner.get("safe_to_proceed") is True
        and plan.get("safe_to_execute") is True
        and plan.get("task") == selected
        and ledger.get("task_id") == selected.get("id")
        and ledger.get("decision") == "SAFE_TO_EXECUTE_REPOSITORY_LOCAL"
        and queue.get("authoritative_department_scope") == ["DO-DEP-01", "DO-DEP-14"]
        and all(controls.get(k) is False for k in (
            "external_writes", "production_deploy", "destructive_actions",
            "secret_access", "arbitrary_commands"
        ))
    )
    if not safe:
        raise SystemExit("Refusing execution receipt: validated repository-local safety evidence is incomplete")

    receipt = {
        "schema_version": 1,
        "task_id": selected["id"],
        "task_title": selected["title"],
        "result": "FOUNDATION_VALIDATED",
        "transition_authorized": False,
        "transition_policy": "queue mutation requires a separate reviewed repository commit",
        "scope": "repository-local",
        "authoritative_department_scope": ["DO-DEP-01", "DO-DEP-14"],
        "controls": {
            "external_writes": False,
            "production_deploy": False,
            "destructive_actions": False,
            "secret_access": False,
        },
        "evidence_sha256": {
            "runner_state": digest(runner),
            "execution_plan": digest(plan),
            "audit_ledger": digest(ledger),
        },
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(receipt, sort_keys=True))


if __name__ == "__main__":
    main()
