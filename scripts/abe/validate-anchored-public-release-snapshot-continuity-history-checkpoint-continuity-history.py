#!/usr/bin/env python3
import hashlib, json, re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
QUEUE = ROOT / "config/abe/task-queue.json"
CURRENT = ROOT / "build/abe/anchored-public-release-snapshot-continuity-history-checkpoint-continuity.json"
PREDECESSOR = ROOT / "build/abe/anchored-public-release-snapshot-continuity-history-checkpoint-continuity-history.previous.json"
EVIDENCE = ROOT / "build/abe/anchored-public-release-snapshot-continuity-history-checkpoint-continuity-history.json"
FLAGS = ("external_write_performed", "production_deploy_performed", "publication_performed", "destructive_action_performed", "secret_access_performed", "authorizes_deployment")

def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()).hexdigest()

def valid_identity(value):
    return isinstance(value, dict) and value.get("algorithm") == "sha256" and re.fullmatch(r"[0-9a-f]{64}", value.get("digest", ""))

def require_identity(value, label):
    if not valid_identity(value): raise SystemExit(f"invalid {label}")
    return value

def validate_safe(value, label):
    if value.get("publication_policy") != "explicit-public-only" or value.get("classification_boundary") != "PUBLIC_ONLY": raise SystemExit(f"unsafe/non-PUBLIC {label}")
    if any(value.get(k) is not False for k in FLAGS): raise SystemExit(f"consequential authority rejected: {label}")

q = json.loads(QUEUE.read_text(encoding="utf-8"))
if q.get("authoritative_department_scope") != ["DO-DEP-01", "DO-DEP-14"] or q.get("verified_baseline") != "DO-DEP-04": raise SystemExit("scope/baseline changed")
if q.get("rules") != {"public_exposure":"explicit-public-only", "external_writes":False, "production_deploy":False, "destructive_actions":False}: raise SystemExit("safety gate changed")
task = next((x for x in q.get("queue", []) if x.get("id") == "ABE-035"), None)
if not task or task.get("status") not in {"READY", "COMPLETE_FOUNDATION"} or task.get("safe_autonomous") is not True: raise SystemExit("ABE-035 not authoritative READY or COMPLETE_FOUNDATION")

current = json.loads(CURRENT.read_text(encoding="utf-8"))
if current.get("schema_version") != 1 or current.get("stage") != "ABE-034" or current.get("continuity_state") not in {"GENESIS", "LINKED"}: raise SystemExit("invalid ABE-034 continuity evidence")
validate_safe(current, "ABE-034 continuity")
current_identity = require_identity(current.get("continuity_digest"), "ABE-034 continuity identity")
if current_identity["digest"] != digest({k:v for k,v in current.items() if k != "continuity_digest"}): raise SystemExit("ABE-034 continuity digest mismatch")
continuity_sequence = current.get("continuity_sequence")
if not isinstance(continuity_sequence, int) or isinstance(continuity_sequence, bool) or continuity_sequence < 1: raise SystemExit("invalid ABE-034 continuity sequence")

expected_sequence, expected_state, expected_predecessor = 1, "GENESIS", None
if PREDECESSOR.exists():
    predecessor = json.loads(PREDECESSOR.read_text(encoding="utf-8"))
    if predecessor.get("schema_version") != 1 or predecessor.get("stage") != "ABE-035" or predecessor.get("history_state") not in {"GENESIS", "LINKED"}: raise SystemExit("invalid predecessor ABE-035 history")
    validate_safe(predecessor, "ABE-035 predecessor")
    pid = require_identity(predecessor.get("history_digest"), "predecessor history identity")
    if pid["digest"] != digest({k:v for k,v in predecessor.items() if k != "history_digest"}): raise SystemExit("predecessor history digest mismatch")
    seq = predecessor.get("history_sequence")
    if not isinstance(seq, int) or isinstance(seq, bool) or seq < 1: raise SystemExit("invalid predecessor history sequence")
    if predecessor.get("current_continuity_identity") == current_identity: raise SystemExit("duplicate/self-reference history rejected")
    expected_sequence, expected_state, expected_predecessor = seq + 1, "LINKED", pid

evidence = json.loads(EVIDENCE.read_text(encoding="utf-8"))
if evidence.get("schema_version") != 1 or evidence.get("stage") != "ABE-035" or evidence.get("history_state") != expected_state: raise SystemExit("invalid ABE-035 history state")
validate_safe(evidence, "ABE-035 evidence")
expected = {
    "history_sequence": expected_sequence,
    "current_continuity_sequence": continuity_sequence,
    "current_continuity_identity": current_identity,
    "current_checkpoint_identity": current.get("current_checkpoint_identity"),
    "terminal_history_sequence": current.get("terminal_history_sequence"),
    "terminal_history_identity": current.get("terminal_history_identity"),
    "current_anchor_continuity_identity": current.get("current_continuity_identity"),
    "current_anchor_identity": current.get("current_anchor_identity"),
    "predecessor_history_identity": expected_predecessor,
    "current_release_source_commit": current.get("current_release_source_commit"),
}
for key, value in expected.items():
    if evidence.get(key) != value: raise SystemExit(f"checkpoint continuity history linkage mismatch: {key}")
for key in ("current_continuity_identity", "current_checkpoint_identity", "terminal_history_identity", "current_anchor_continuity_identity", "current_anchor_identity"):
    require_identity(evidence.get(key), key)
if not isinstance(evidence.get("terminal_history_sequence"), int) or isinstance(evidence.get("terminal_history_sequence"), bool) or evidence["terminal_history_sequence"] < 1: raise SystemExit("invalid terminal history sequence")
eid = require_identity(evidence.get("history_digest"), "ABE-035 history identity")
if eid["digest"] != digest({k:v for k,v in evidence.items() if k != "history_digest"}): raise SystemExit("ABE-035 history digest mismatch")
print(f"ABE-035 checkpoint continuity history validation PASS: state={expected_state}; sequence={expected_sequence}; deployment_authorized=false")
