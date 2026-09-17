#!/usr/bin/env python3
"""Propose, but never apply, a validated repository-local ABE queue transition."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
QUEUE = ROOT / "config/abe/task-queue.json"
RECEIPT = ROOT / "build/abe/execution-receipt.json"
OUT = ROOT / "build/abe/transition-proposal.json"


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def main():
    queue = load(QUEUE)
    receipt = load(RECEIPT)
    task_id = receipt.get("task_id")
    task = next((t for t in queue.get("queue", []) if t.get("id") == task_id), None)
    controls = receipt.get("controls", {})
    safe = (
        queue.get("mode") == "controlled-autonomous"
        and queue.get("authoritative_department_scope") == ["DO-DEP-01", "DO-DEP-14"]
        and queue.get("rules", {}).get("external_writes") is False
        and queue.get("rules", {}).get("production_deploy") is False
        and queue.get("rules", {}).get("destructive_actions") is False
        and task is not None
        and task.get("status") == "READY"
        and task.get("safe_autonomous") is True
        and receipt.get("result") == "FOUNDATION_VALIDATED"
        and receipt.get("transition_authorized") is False
        and receipt.get("scope") == "repository-local"
        and receipt.get("authoritative_department_scope") == ["DO-DEP-01", "DO-DEP-14"]
        and all(controls.get(k) is False for k in (
            "external_writes", "production_deploy", "destructive_actions", "secret_access"
        ))
    )
    if not safe:
        raise SystemExit("Refusing transition proposal: validated repository-local evidence is incomplete")

    proposal = {
        "schema_version": 1,
        "task_id": task_id,
        "from_status": "READY",
        "to_status": "COMPLETE_FOUNDATION",
        "apply_automatically": False,
        "requires_reviewed_repository_commit": True,
        "scope": "repository-local",
        "authoritative_department_scope": ["DO-DEP-01", "DO-DEP-14"],
        "safety_rules_unchanged": True,
        "external_writes": False,
        "production_deploy": False,
        "destructive_actions": False,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(proposal, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(proposal, sort_keys=True))


if __name__ == "__main__":
    main()
