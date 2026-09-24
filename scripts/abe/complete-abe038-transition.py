#!/usr/bin/env python3
"""Fail-closed, metadata-preserving ABE-038 authoritative queue transition.

Repository-local only. Changes exactly ABE-038.status READY -> COMPLETE_FOUNDATION
and adds the validated completion note. Refuses scope, baseline, safety, identity,
or state drift.
"""
from __future__ import annotations

import copy
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
QUEUE = ROOT / "config/abe/task-queue.json"
NOTE = (
    "ABE-038 implementation and fresh completion gate validated on authoritative "
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
    data = json.loads(QUEUE.read_text(encoding="utf-8"))
    if data.get("authoritative_department_scope") != ["DO-DEP-01", "DO-DEP-14"]:
        fail("authoritative department scope drift")
    if data.get("verified_baseline") != "DO-DEP-04":
        fail("verified baseline drift")
    if data.get("rules") != EXPECTED_RULES:
        fail("locked safety-rule drift")

    tasks = data.get("queue")
    if not isinstance(tasks, list):
        fail("queue is not a list")
    matches = [task for task in tasks if task.get("id") == "ABE-038"]
    if len(matches) != 1:
        fail("ABE-038 must exist exactly once")
    task = matches[0]
    if task.get("status") != "READY":
        fail("ABE-038 is not in the validated READY state")
    if task.get("safe_autonomous") is not True:
        fail("ABE-038 is not marked safe_autonomous")
    if not isinstance(task.get("acceptance"), list) or not task["acceptance"]:
        fail("ABE-038 acceptance contract missing")
    if "note" in task:
        fail("ABE-038 already has a note; refusing ambiguous mutation")

    before = copy.deepcopy(data)
    task["status"] = "COMPLETE_FOUNDATION"
    task["note"] = NOTE
    expected = copy.deepcopy(before)
    expected_task = next(t for t in expected["queue"] if t.get("id") == "ABE-038")
    expected_task["status"] = "COMPLETE_FOUNDATION"
    expected_task["note"] = NOTE
    if data != expected:
        fail("unexpected metadata mutation detected")

    QUEUE.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("PASS: ABE-038 bounded completion transition prepared")


if __name__ == "__main__":
    main()
