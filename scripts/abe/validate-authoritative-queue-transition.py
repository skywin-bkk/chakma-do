#!/usr/bin/env python3
"""Fail-closed validator for a reviewed ABE authoritative queue transition manifest."""
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


def main() -> None:
    qbytes = QUEUE.read_bytes()
    queue = json.loads(qbytes)
    manifest = json.loads(MANIFEST.read_text())

    if manifest.get("schema_version") != 1 or manifest.get("transition_id") != "ABE-023-to-ABE-024":
        fail("unexpected transition manifest identity")
    if git_blob_sha(qbytes) != manifest.get("validated_source_queue_blob"):
        fail("authoritative queue no longer matches validated source blob")
    source_commit = manifest.get("validated_source_commit", "")
    if len(source_commit) != 40:
        fail("validated source commit is malformed")
    try:
        subprocess.run(["git", "merge-base", "--is-ancestor", source_commit, "HEAD"], cwd=ROOT, check=True,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except subprocess.CalledProcessError:
        fail("validated source commit is not an ancestor of HEAD")

    if queue.get("authoritative_department_scope") != ["DO-DEP-01", "DO-DEP-14"]:
        fail("authoritative department scope changed")
    if queue.get("verified_baseline") != "DO-DEP-04" or queue.get("rules") != LOCKED_RULES:
        fail("baseline or safety rules changed")

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

    ci = manifest.get("validated_ci", {})
    if ci.get("workflow_count") != 5 or ci.get("all_completed_successfully") is not True:
        fail("manifest does not record the required successful validation gate")
    auth = manifest.get("authorization", {})
    if set(auth) != {"publication", "production_deploy", "external_writes", "destructive_actions", "secret_access"} or any(auth.values()):
        fail("transition manifest attempts consequential authorization")

    print("PASS: ABE-023 -> ABE-024 authoritative transition manifest is bounded, source-bound, metadata-preserving, and non-consequential")


if __name__ == "__main__":
    main()
