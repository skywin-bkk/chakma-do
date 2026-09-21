#!/usr/bin/env python3
import hashlib, json, re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
QUEUE = ROOT / "config/abe/task-queue.json"
CURRENT = ROOT / "build/abe/anchored-public-release-snapshot-continuity-history-anchor-continuity.json"
PREDECESSOR = ROOT / "build/abe/anchored-public-release-snapshot-continuity-history-anchor-continuity-history.previous.json"
HISTORY = ROOT / "build/abe/anchored-public-release-snapshot-continuity-history-anchor-continuity-history.json"


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()).hexdigest()


def valid_identity(value):
    return isinstance(value, dict) and value.get("algorithm") == "sha256" and re.fullmatch(r"[0-9a-f]{64}", value.get("digest", ""))


flags = ("external_write_performed", "production_deploy_performed", "publication_performed", "destructive_action_performed", "secret_access_performed", "authorizes_deployment")
q = json.loads(QUEUE.read_text(encoding="utf-8"))
current = json.loads(CURRENT.read_text(encoding="utf-8"))
history = json.loads(HISTORY.read_text(encoding="utf-8"))

if q.get("authoritative_department_scope") != ["DO-DEP-01", "DO-DEP-14"] or q.get("verified_baseline") != "DO-DEP-04":
    raise SystemExit("scope/baseline changed")
if q.get("rules") != {"public_exposure":"explicit-public-only", "external_writes":False, "production_deploy":False, "destructive_actions":False}:
    raise SystemExit("safety gate changed")
task = next((x for x in q.get("queue", []) if x.get("id") == "ABE-032"), None)
if not task or task.get("status") not in {"READY", "COMPLETE_FOUNDATION"} or task.get("safe_autonomous") is not True:
    raise SystemExit("ABE-032 not authoritative READY or COMPLETE_FOUNDATION")

if current.get("schema_version") != 1 or current.get("stage") != "ABE-031" or current.get("continuity_state") not in {"GENESIS", "LINKED"}:
    raise SystemExit("invalid ABE-031 continuity evidence")
if current.get("publication_policy") != "explicit-public-only" or current.get("classification_boundary") != "PUBLIC_ONLY" or any(current.get(k) is not False for k in flags):
    raise SystemExit("unsafe/non-PUBLIC ABE-031 continuity evidence")
current_identity = current.get("continuity_digest", {})
current_core = {k: v for k, v in current.items() if k != "continuity_digest"}
if not valid_identity(current_identity) or current_identity["digest"] != digest(current_core):
    raise SystemExit("ABE-031 continuity digest mismatch")
current_anchor_identity = current.get("current_anchor_identity")
if not valid_identity(current_anchor_identity):
    raise SystemExit("invalid ABE-030 anchor identity")

expected_state = "GENESIS"
expected_sequence = 1
expected_predecessor_identity = None
if PREDECESSOR.exists():
    predecessor = json.loads(PREDECESSOR.read_text(encoding="utf-8"))
    if predecessor.get("schema_version") != 1 or predecessor.get("stage") != "ABE-032" or predecessor.get("history_state") not in {"GENESIS", "LINKED"}:
        raise SystemExit("invalid predecessor history evidence")
    if predecessor.get("publication_policy") != "explicit-public-only" or predecessor.get("classification_boundary") != "PUBLIC_ONLY" or any(predecessor.get(k) is not False for k in flags):
        raise SystemExit("unsafe/non-PUBLIC predecessor history rejected")
    predecessor_identity = predecessor.get("history_digest", {})
    predecessor_core = {k: v for k, v in predecessor.items() if k != "history_digest"}
    if not valid_identity(predecessor_identity) or predecessor_identity["digest"] != digest(predecessor_core):
        raise SystemExit("predecessor history digest mismatch")
    predecessor_sequence = predecessor.get("sequence")
    if not isinstance(predecessor_sequence, int) or isinstance(predecessor_sequence, bool) or predecessor_sequence < 1:
        raise SystemExit("invalid predecessor history sequence")
    predecessor_current = predecessor.get("current_continuity_identity")
    if not valid_identity(predecessor_current) or predecessor_current == current_identity:
        raise SystemExit("invalid/self-referential predecessor linkage")
    expected_state = "LINKED"
    expected_sequence = predecessor_sequence + 1
    expected_predecessor_identity = predecessor_identity

if history.get("schema_version") != 1 or history.get("stage") != "ABE-032":
    raise SystemExit("invalid ABE-032 history evidence")
expected = {
    "history_state": expected_state,
    "sequence": expected_sequence,
    "current_continuity_identity": current_identity,
    "current_anchor_identity": current_anchor_identity,
    "predecessor_history_identity": expected_predecessor_identity,
    "current_release_source_commit": current.get("current_release_source_commit"),
}
for key, value in expected.items():
    if history.get(key) != value:
        raise SystemExit(f"history linkage mismatch: {key}")
if history.get("publication_policy") != "explicit-public-only" or history.get("classification_boundary") != "PUBLIC_ONLY" or any(history.get(k) is not False for k in flags):
    raise SystemExit("history evidence cannot authorize consequential action")
history_identity = history.get("history_digest", {})
history_core = {k: v for k, v in history.items() if k != "history_digest"}
if not valid_identity(history_identity) or history_identity["digest"] != digest(history_core):
    raise SystemExit("history digest mismatch")

print(f"ABE-032 continuity history validation PASS: state={expected_state}; sequence={expected_sequence}; deployment_authorized=false")
