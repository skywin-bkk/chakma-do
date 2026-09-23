#!/usr/bin/env python3
"""Build a metadata-preserving ABE queue replenishment candidate.

Repository-local only. This script never mutates the authoritative queue. It emits a
candidate for review/CI so an already-complete tail can safely receive one READY task
without rewriting metadata on prior entries.
"""
import argparse
import copy
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_QUEUE = ROOT / "config/abe/task-queue.json"
DEFAULT_OUT = ROOT / "build/abe/authoritative-queue-replenishment-candidate.json"
LOCKED_SCOPE = ["DO-DEP-01", "DO-DEP-14"]
LOCKED_BASELINE = "DO-DEP-04"
LOCKED_RULES = {
    "public_exposure": "explicit-public-only",
    "external_writes": False,
    "production_deploy": False,
    "destructive_actions": False,
}


def fail(message: str) -> None:
    raise SystemExit(f"FAIL: {message}")


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--queue", type=Path, default=DEFAULT_QUEUE)
    p.add_argument("--out", type=Path, default=DEFAULT_OUT)
    p.add_argument("--ready", required=True)
    p.add_argument("--ready-title", required=True)
    p.add_argument("--ready-acceptance", action="append", default=[])
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

    queue = source.get("queue")
    if not isinstance(queue, list) or not queue:
        fail("queue is missing or empty")
    ids = [item.get("id") for item in queue]
    if any(not isinstance(x, str) or not x for x in ids):
        fail("invalid task ID")
    if len(ids) != len(set(ids)):
        fail("duplicate task IDs in source queue")
    if args.ready in ids:
        fail("next task ID already exists")
    if queue[-1].get("status") not in {"COMPLETE", "COMPLETE_FOUNDATION"}:
        fail("authoritative tail is not complete")

    candidate = copy.deepcopy(source)
    candidate["queue"].append({
        "id": args.ready,
        "title": args.ready_title,
        "status": "READY",
        "safe_autonomous": True,
        "acceptance": args.ready_acceptance,
    })

    # Strong metadata-preservation gate: every pre-existing object must be byte-value
    # equivalent after the append; only one new READY object may differ from source.
    if candidate["queue"][:-1] != source["queue"]:
        fail("pre-existing queue metadata changed")
    if {k: v for k, v in candidate.items() if k != "queue"} != {k: v for k, v in source.items() if k != "queue"}:
        fail("top-level authoritative metadata changed")
    if len(candidate["queue"]) != len(source["queue"]) + 1:
        fail("replenishment is not exactly one append")

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(candidate, indent=2, ensure_ascii=False) + "\n")
    print(f"PASS: metadata-preserving queue replenishment candidate {args.ready} -> READY")


if __name__ == "__main__":
    main()
