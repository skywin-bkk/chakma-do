#!/usr/bin/env python3
"""Build a metadata-preserving authoritative ABE queue transition candidate.

Repository-local only. This script never writes config/abe/task-queue.json and never
performs external actions. It emits a candidate that must receive normal CI review
before an authoritative queue update.
"""
import argparse
import copy
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_QUEUE = ROOT / "config/abe/task-queue.json"
DEFAULT_OUT = ROOT / "build/abe/authoritative-queue-transition-candidate.json"
LOCKED_RULES = {
    "public_exposure": "explicit-public-only",
    "external_writes": False,
    "production_deploy": False,
    "destructive_actions": False,
}
LOCKED_SCOPE = ["DO-DEP-01", "DO-DEP-14"]
LOCKED_BASELINE = "DO-DEP-04"


def fail(message: str) -> None:
    raise SystemExit(f"FAIL: {message}")


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--queue", type=Path, default=DEFAULT_QUEUE)
    p.add_argument("--out", type=Path, default=DEFAULT_OUT)
    p.add_argument("--complete", required=True)
    p.add_argument("--ready", required=True)
    p.add_argument("--ready-title", required=True)
    p.add_argument("--ready-acceptance", action="append", default=[])
    p.add_argument("--completion-note", required=True)
    args = p.parse_args()

    source = json.loads(args.queue.read_text())
    if source.get("authoritative_department_scope") != LOCKED_SCOPE:
        fail("authoritative department scope changed")
    if source.get("verified_baseline") != LOCKED_BASELINE:
        fail("verified baseline changed")
    if source.get("rules") != LOCKED_RULES:
        fail("safety rules changed")
    if not args.ready_acceptance:
        fail("next task must declare acceptance criteria")

    candidate = copy.deepcopy(source)
    queue = candidate.get("queue")
    if not isinstance(queue, list):
        fail("queue is not a list")
    ids = [item.get("id") for item in queue]
    if len(ids) != len(set(ids)):
        fail("duplicate task IDs in source queue")
    if args.complete not in ids:
        fail("completion task is missing")
    if args.ready in ids:
        fail("next task ID already exists")

    idx = ids.index(args.complete)
    task = queue[idx]
    if task.get("status") != "READY" or task.get("safe_autonomous") is not True:
        fail("completion task is not safe READY work")
    task["status"] = "COMPLETE_FOUNDATION"
    task["note"] = args.completion_note
    queue.append({
        "id": args.ready,
        "title": args.ready_title,
        "status": "READY",
        "safe_autonomous": True,
        "acceptance": args.ready_acceptance,
    })

    # Fail closed if anything except the intended task status/note and one append changed.
    before = copy.deepcopy(source)
    expected = copy.deepcopy(source)
    expected_task = expected["queue"][idx]
    expected_task["status"] = "COMPLETE_FOUNDATION"
    expected_task["note"] = args.completion_note
    expected["queue"].append(queue[-1])
    if candidate != expected or before != source:
        fail("unexpected metadata mutation")

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(candidate, indent=2, ensure_ascii=False) + "\n")
    print(f"PASS: metadata-preserving transition candidate {args.complete} -> COMPLETE_FOUNDATION; {args.ready} -> READY")


if __name__ == "__main__":
    main()
