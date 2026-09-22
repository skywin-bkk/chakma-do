#!/usr/bin/env python3
import hashlib, json, re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
QUEUE = ROOT / "config/abe/task-queue.json"
HISTORY = ROOT / "build/abe/anchored-public-release-snapshot-continuity-history-anchor-continuity-history.json"
CHECKPOINT = ROOT / "build/abe/anchored-public-release-snapshot-continuity-history-checkpoint.json"


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()).hexdigest()


def valid_identity(value):
    return isinstance(value, dict) and value.get("algorithm") == "sha256" and re.fullmatch(r"[0-9a-f]{64}", value.get("digest", ""))


flags = ("external_write_performed", "production_deploy_performed", "publication_performed", "destructive_action_performed", "secret_access_performed", "authorizes_deployment")
q = json.loads(QUEUE.read_text(encoding="utf-8"))
history = json.loads(HISTORY.read_text(encoding="utf-8"))
checkpoint = json.loads(CHECKPOINT.read_text(encoding="utf-8"))

if q.get("authoritative_department_scope") != ["DO-DEP-01", "DO-DEP-14"] or q.get("verified_baseline") != "DO-DEP-04":
    raise SystemExit("scope/baseline changed")
if q.get("rules") != {"public_exposure":"explicit-public-only", "external_writes":False, "production_deploy":False, "destructive_actions":False}:
    raise SystemExit("safety gate changed")
task = next((x for x in q.get("queue", []) if x.get("id") == "ABE-033"), None)
if not task or task.get("status") not in {"READY", "COMPLETE_FOUNDATION"} or task.get("safe_autonomous") is not True:
    raise SystemExit("ABE-033 not authoritative READY or COMPLETE_FOUNDATION")

if history.get("schema_version") != 1 or history.get("stage") != "ABE-032" or history.get("history_state") not in {"GENESIS", "LINKED"}:
    raise SystemExit("invalid ABE-032 terminal history")
if history.get("publication_policy") != "explicit-public-only" or history.get("classification_boundary") != "PUBLIC_ONLY" or any(history.get(k) is not False for k in flags):
    raise SystemExit("unsafe/non-PUBLIC ABE-032 history")
history_identity = history.get("history_digest", {})
history_core = {k: v for k, v in history.items() if k != "history_digest"}
if not valid_identity(history_identity) or history_identity["digest"] != digest(history_core):
    raise SystemExit("ABE-032 history digest mismatch")
sequence = history.get("sequence")
if not isinstance(sequence, int) or isinstance(sequence, bool) or sequence < 1:
    raise SystemExit("invalid terminal history sequence")
continuity_identity = history.get("current_continuity_identity")
anchor_identity = history.get("current_anchor_identity")
if not valid_identity(continuity_identity) or not valid_identity(anchor_identity):
    raise SystemExit("invalid continuity/anchor identity")

if checkpoint.get("schema_version") != 1 or checkpoint.get("stage") != "ABE-033" or checkpoint.get("checkpoint_state") != "SEALED":
    raise SystemExit("invalid ABE-033 checkpoint")
expected = {
    "terminal_history_sequence": sequence,
    "terminal_history_identity": history_identity,
    "current_continuity_identity": continuity_identity,
    "current_anchor_identity": anchor_identity,
    "current_release_source_commit": history.get("current_release_source_commit"),
}
for key, value in expected.items():
    if checkpoint.get(key) != value:
        raise SystemExit(f"checkpoint linkage mismatch: {key}")
if checkpoint.get("publication_policy") != "explicit-public-only" or checkpoint.get("classification_boundary") != "PUBLIC_ONLY" or any(checkpoint.get(k) is not False for k in flags):
    raise SystemExit("checkpoint cannot authorize consequential action")
checkpoint_identity = checkpoint.get("checkpoint_digest", {})
checkpoint_core = {k: v for k, v in checkpoint.items() if k != "checkpoint_digest"}
if not valid_identity(checkpoint_identity) or checkpoint_identity["digest"] != digest(checkpoint_core):
    raise SystemExit("checkpoint digest mismatch")

print(f"ABE-033 checkpoint validation PASS: terminal_sequence={sequence}; state=SEALED; deployment_authorized=false")
