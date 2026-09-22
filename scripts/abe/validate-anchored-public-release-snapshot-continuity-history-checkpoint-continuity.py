#!/usr/bin/env python3
import hashlib, json, re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
QUEUE = ROOT / "config/abe/task-queue.json"
CURRENT = ROOT / "build/abe/anchored-public-release-snapshot-continuity-history-checkpoint.json"
PREDECESSOR = ROOT / "build/abe/anchored-public-release-snapshot-continuity-history-checkpoint-continuity.previous.json"
EVIDENCE = ROOT / "build/abe/anchored-public-release-snapshot-continuity-history-checkpoint-continuity.json"

FLAGS = ("external_write_performed", "production_deploy_performed", "publication_performed", "destructive_action_performed", "secret_access_performed", "authorizes_deployment")


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()).hexdigest()


def valid_identity(value):
    return isinstance(value, dict) and value.get("algorithm") == "sha256" and re.fullmatch(r"[0-9a-f]{64}", value.get("digest", ""))


def require_identity(value, label):
    if not valid_identity(value):
        raise SystemExit(f"invalid {label}")
    return value


def validate_safe(value, label):
    if value.get("publication_policy") != "explicit-public-only" or value.get("classification_boundary") != "PUBLIC_ONLY":
        raise SystemExit(f"unsafe/non-PUBLIC {label}")
    if any(value.get(k) is not False for k in FLAGS):
        raise SystemExit(f"consequential authority rejected: {label}")


q = json.loads(QUEUE.read_text(encoding="utf-8"))
if q.get("authoritative_department_scope") != ["DO-DEP-01", "DO-DEP-14"] or q.get("verified_baseline") != "DO-DEP-04":
    raise SystemExit("scope/baseline changed")
if q.get("rules") != {"public_exposure":"explicit-public-only", "external_writes":False, "production_deploy":False, "destructive_actions":False}:
    raise SystemExit("safety gate changed")
task = next((x for x in q.get("queue", []) if x.get("id") == "ABE-034"), None)
if not task or task.get("status") not in {"READY", "COMPLETE_FOUNDATION"} or task.get("safe_autonomous") is not True:
    raise SystemExit("ABE-034 not authoritative READY or COMPLETE_FOUNDATION")

current = json.loads(CURRENT.read_text(encoding="utf-8"))
if current.get("schema_version") != 1 or current.get("stage") != "ABE-033" or current.get("checkpoint_state") != "SEALED":
    raise SystemExit("invalid ABE-033 checkpoint")
validate_safe(current, "ABE-033 checkpoint")
current_identity = require_identity(current.get("checkpoint_digest"), "ABE-033 checkpoint identity")
current_core = {k: v for k, v in current.items() if k != "checkpoint_digest"}
if current_identity["digest"] != digest(current_core):
    raise SystemExit("ABE-033 checkpoint digest mismatch")

expected_sequence = 1
expected_state = "GENESIS"
expected_predecessor = None
if PREDECESSOR.exists():
    predecessor = json.loads(PREDECESSOR.read_text(encoding="utf-8"))
    if predecessor.get("schema_version") != 1 or predecessor.get("stage") != "ABE-034" or predecessor.get("continuity_state") not in {"GENESIS", "LINKED"}:
        raise SystemExit("invalid predecessor checkpoint-continuity evidence")
    validate_safe(predecessor, "ABE-034 predecessor")
    predecessor_identity = require_identity(predecessor.get("continuity_digest"), "predecessor continuity identity")
    predecessor_core = {k: v for k, v in predecessor.items() if k != "continuity_digest"}
    if predecessor_identity["digest"] != digest(predecessor_core):
        raise SystemExit("predecessor continuity digest mismatch")
    predecessor_sequence = predecessor.get("continuity_sequence")
    if not isinstance(predecessor_sequence, int) or isinstance(predecessor_sequence, bool) or predecessor_sequence < 1:
        raise SystemExit("invalid predecessor continuity sequence")
    if predecessor.get("current_checkpoint_identity") == current_identity:
        raise SystemExit("self-reference/non-monotonic checkpoint linkage rejected")
    expected_sequence = predecessor_sequence + 1
    expected_state = "LINKED"
    expected_predecessor = predecessor_identity

evidence = json.loads(EVIDENCE.read_text(encoding="utf-8"))
if evidence.get("schema_version") != 1 or evidence.get("stage") != "ABE-034" or evidence.get("continuity_state") != expected_state:
    raise SystemExit("invalid ABE-034 checkpoint continuity state")
validate_safe(evidence, "ABE-034 evidence")
expected = {
    "continuity_sequence": expected_sequence,
    "current_checkpoint_identity": current_identity,
    "predecessor_continuity_identity": expected_predecessor,
    "terminal_history_sequence": current.get("terminal_history_sequence"),
    "terminal_history_identity": current.get("terminal_history_identity"),
    "current_continuity_identity": current.get("current_continuity_identity"),
    "current_anchor_identity": current.get("current_anchor_identity"),
    "current_release_source_commit": current.get("current_release_source_commit"),
}
for key, value in expected.items():
    if evidence.get(key) != value:
        raise SystemExit(f"checkpoint continuity linkage mismatch: {key}")
for key in ("terminal_history_identity", "current_continuity_identity", "current_anchor_identity"):
    require_identity(evidence.get(key), key)
if not isinstance(evidence.get("terminal_history_sequence"), int) or isinstance(evidence.get("terminal_history_sequence"), bool) or evidence["terminal_history_sequence"] < 1:
    raise SystemExit("invalid terminal history sequence")
evidence_identity = require_identity(evidence.get("continuity_digest"), "ABE-034 continuity identity")
evidence_core = {k: v for k, v in evidence.items() if k != "continuity_digest"}
if evidence_identity["digest"] != digest(evidence_core):
    raise SystemExit("ABE-034 continuity digest mismatch")

print(f"ABE-034 checkpoint continuity validation PASS: state={expected_state}; sequence={expected_sequence}; deployment_authorized=false")
