#!/usr/bin/env python3
"""Fail-closed validator for a reviewed ABE authoritative queue transition manifest.

The manifest is historical evidence. Validate its source queue at the recorded
source commit instead of incorrectly requiring today's authoritative queue to
remain byte-identical to that historical source.
"""
import hashlib
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
QUEUE = ROOT / "config/abe/task-queue.json"
MANIFEST = ROOT / "config/abe/transitions/ABE-023-to-ABE-024.json"
LOCKED_RULES = {
    "public_exposure": "explicit-public-only",
    "external_writes": False,
    "production_deploy": False,
    "destructive_actions": False,
}


def fail(msg: str) -> None:
    raise SystemExit(f"FAIL: {msg}")


def git_blob_sha(data: bytes) -> str:
    header = f"blob {len(data)}\0".encode()
    return hashlib.sha1(header + data).hexdigest()


def source_queue_bytes(source_commit: str) -> bytes:
    try:
        return subprocess.check_output(
            ["git", "show", f"{source_commit}:config/abe/task-queue.json"], cwd=ROOT
        )
    except subprocess.CalledProcessError:
        fail("validated source queue cannot be read from recorded source commit")


def main() -> None:
    current_queue = json.loads(QUEUE.read_text())
    manifest = json.loads(MANIFEST.read_text())

    if manifest.get("schema_version") != 1 or manifest.get("transition_id") != "ABE-023-to-ABE-024":
        fail("unexpected transition manifest identity")

    source_commit = manifest.get("validated_source_commit", "")
    if len(source_commit) != 40:
        fail("validated source commit is malformed")
    try:
        subprocess.run(["git", "merge-base", "--is-ancestor", source_commit, "HEAD"], cwd=ROOT, check=True,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except subprocess.CalledProcessError:
        fail("validated source commit is not an ancestor of HEAD")

    qbytes = source_queue_bytes(source_commit)
    queue = json.loads(qbytes)
    if git_blob_sha(qbytes) != manifest.get("validated_source_queue_blob"):
        fail("recorded source queue does not match validated source blob")

    # Safety invariants must hold both at the historical source and now. This
    # permits bounded queue advancement without weakening the fail-closed gate.
    for label, candidate in (("source", queue), ("current", current_queue)):
        if candidate.get("authoritative_department_scope") != ["DO-DEP-01", "DO-DEP-14"]:
            fail(f"{label} authoritative department scope changed")
        if candidate.get("verified_baseline") != "DO-DEP-04" or candidate.get("rules") != LOCKED_RULES:
            fail(f"{label} baseline or safety rules changed")

    mutation = manifest.get("authoritative_mutation", {})
    if mutation.get("complete_task") != "ABE-023" or mutation.get("required_from_status") != "READY" or mutation.get("to_status") != "COMPLETE_FOUNDATION":
        fail("completion mutation is not the bounded ABE-023 transition")
    ready = mutation.get("append_ready_task", {})
    if ready.get("id") != "ABE-024" or ready.get("status") != "READY" or ready.get("safe_autonomous") is not True or not ready.get("acceptance"):
        fail("ABE-024 append specification is unsafe or incomplete")

    tasks = queue.get("queue", [])
    ids = [t.get("id") for t in tasks]
    if len(ids) != len(set(ids)) or "ABE-024" in ids:
        fail("source queue has duplicate IDs or already contains ABE-024")
    current = next((t for t in tasks if t.get("id") == "ABE-023"), None)
    if not current or current.get("status") != "READY" or current.get("safe_autonomous") is not True:
        fail("ABE-023 is not the expected safe READY task")

    # Current queue must retain the transitioned tasks; later bounded progress is allowed.
    current_tasks = {t.get("id"): t for t in current_queue.get("queue", [])}
    if current_tasks.get("ABE-023", {}).get("status") != "COMPLETE_FOUNDATION":
        fail("current queue lost ABE-023 completion")
    if current_tasks.get("ABE-024", {}).get("status") not in {"READY", "COMPLETE_FOUNDATION"}:
        fail("current queue lost or regressed ABE-024")

    ci = manifest.get("validated_ci", {})
    if ci.get("workflow_count") != 5 or ci.get("all_completed_successfully") is not True:
        fail("manifest does not record the required successful validation gate")
    auth = manifest.get("authorization", {})
    if set(auth) != {"publication", "production_deploy", "external_writes", "destructive_actions", "secret_access"} or any(auth.values()):
        fail("transition manifest attempts consequential authorization")

    print("PASS: ABE-023 -> ABE-024 historical transition evidence is source-bound, current safety invariants are intact, and bounded later queue progress is permitted")


if __name__ == "__main__":
    main()
