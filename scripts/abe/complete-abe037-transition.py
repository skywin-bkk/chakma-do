#!/usr/bin/env python3
"""Fail-closed, metadata-preserving ABE-037 authoritative queue transition.

Repository-local only. This utility changes exactly ABE-037.status READY ->
COMPLETE_FOUNDATION and adds the validated completion note. It refuses to run
if authoritative scope, baseline, safety rules, task identity, or current state
do not match the validated transition gate.
"""
from __future__ import annotations

import copy
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
QUEUE = ROOT / "config/abe/task-queue.json"
NOTE = (
    "ABE-037 implementation and fresh completion gate validated on authoritative "
    "main before metadata-preserving completion transition."
)
EXPECTED_RULES = {
    "public_exposure": "explicit-public-only",
    "external_writes": False,
    "production_deploy": False,
    "destructive_actions": False,
}


def fail(message: str) -> None:
    raise SystemExit(f"FAIL: {message}")


def main() -> None:
    original_text = QUEUE.read_text(encoding="utf-8")
    data = json.loads(original_text)

    if data.get("authoritative_department_scope") != ["DO-DEP-01", "DO-DEP-14"]:
        fail("authoritative department scope drift")
    if data.get("verified_baseline") != "DO-DEP-04":
        fail("verified baseline drift")
    if data.get("rules") != EXPECTED_RULES:
        fail("locked safety-rule drift")

    tasks = data.get("queue")
    if not isinstance(tasks, list):
        fail("queue is not a list")
    matches = [task for task in tasks if task.get("id") == "ABE-037"]
    if len(matches) != 1:
        fail("ABE-037 must exist exactly once")

    task = matches[0]
    if task.get("status") != "READY":
        fail("ABE-037 is not in the validated READY state")
    if task.get("safe_autonomous") is not True:
        fail("ABE-037 is not marked safe_autonomous")
    if not isinstance(task.get("acceptance"), list) or not task["acceptance"]:
        fail("ABE-037 acceptance contract missing")
    if "note" in task:
        fail("ABE-037 already has a note; refusing ambiguous mutation")

    before = copy.deepcopy(data)
    task["status"] = "COMPLETE_FOUNDATION"
    task["note"] = NOTE

    # Prove the mutation is bounded to the authorized fields.
    expected = copy.deepcopy(before)
    expected_task = next(t for t in expected["queue"] if t.get("id") == "ABE-037")
    expected_task["status"] = "COMPLETE_FOUNDATION"
    expected_task["note"] = NOTE
    if data != expected:
        fail("unexpected metadata mutation detected")

    # Preserve the repository's established two-space JSON representation.
    QUEUE.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("PASS: ABE-037 bounded completion transition prepared")


if __name__ == "__main__":
    main()
