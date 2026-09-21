#!/usr/bin/env python3
import hashlib, json, re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
QUEUE = ROOT / "config/abe/task-queue.json"
CURRENT = ROOT / "build/abe/anchored-public-release-snapshot-continuity-history-anchor.json"
PREDECESSOR = ROOT / "build/abe/anchored-public-release-snapshot-continuity-history-anchor-continuity.previous.json"
CONTINUITY = ROOT / "build/abe/anchored-public-release-snapshot-continuity-history-anchor-continuity.json"


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()).hexdigest()


def valid_identity(value):
    return isinstance(value, dict) and value.get("algorithm") == "sha256" and re.fullmatch(r"[0-9a-f]{64}", value.get("digest", ""))


q = json.loads(QUEUE.read_text(encoding="utf-8"))
current = json.loads(CURRENT.read_text(encoding="utf-8"))
continuity = json.loads(CONTINUITY.read_text(encoding="utf-8"))

if q.get("authoritative_department_scope") != ["DO-DEP-01", "DO-DEP-14"] or q.get("verified_baseline") != "DO-DEP-04":
    raise SystemExit("scope/baseline changed")
if q.get("rules") != {"public_exposure":"explicit-public-only", "external_writes":False, "production_deploy":False, "destructive_actions":False}:
    raise SystemExit("safety gate changed")
task = next((x for x in q.get("queue", []) if x.get("id") == "ABE-031"), None)
if not task or task.get("status") != "READY" or task.get("safe_autonomous") is not True:
    raise SystemExit("ABE-031 not authoritative READY")

flags = ("external_write_performed", "production_deploy_performed", "publication_performed", "destructive_action_performed", "secret_access_performed", "authorizes_deployment")
if current.get("schema_version") != 1 or current.get("stage") != "ABE-030" or current.get("anchor_state") != "PASS_REPOSITORY_LOCAL_ONLY":
    raise SystemExit("invalid ABE-030 anchor")
if current.get("publication_policy") != "explicit-public-only" or current.get("classification_boundary") != "PUBLIC_ONLY" or any(current.get(k) is not False for k in flags):
    raise SystemExit("unsafe/non-PUBLIC ABE-030 anchor")
current_identity = current.get("anchor_digest", {})
current_core = {k: v for k, v in current.items() if k != "anchor_digest"}
if not valid_identity(current_identity) or current_identity["digest"] != digest(current_core):
    raise SystemExit("ABE-030 anchor digest mismatch")

expected_state = "GENESIS"
expected_predecessor_identity = None
if PREDECESSOR.exists():
    predecessor = json.loads(PREDECESSOR.read_text(encoding="utf-8"))
    if predecessor.get("schema_version") != 1 or predecessor.get("stage") != "ABE-031" or predecessor.get("continuity_state") not in {"GENESIS", "LINKED"}:
        raise SystemExit("invalid predecessor continuity evidence")
    if predecessor.get("publication_policy") != "explicit-public-only" or predecessor.get("classification_boundary") != "PUBLIC_ONLY" or any(predecessor.get(k) is not False for k in flags):
        raise SystemExit("unsafe/non-PUBLIC predecessor rejected")
    predecessor_identity = predecessor.get("continuity_digest", {})
    predecessor_core = {k: v for k, v in predecessor.items() if k != "continuity_digest"}
    if not valid_identity(predecessor_identity) or predecessor_identity["digest"] != digest(predecessor_core):
        raise SystemExit("predecessor continuity digest mismatch")
    predecessor_current = predecessor.get("current_anchor_identity")
    if not valid_identity(predecessor_current) or predecessor_current == current_identity:
        raise SystemExit("invalid/self-referential predecessor linkage")
    expected_state = "LINKED"
    expected_predecessor_identity = predecessor_identity

if continuity.get("schema_version") != 1 or continuity.get("stage") != "ABE-031":
    raise SystemExit("invalid ABE-031 continuity evidence")
expected = {
    "continuity_state": expected_state,
    "current_anchor_identity": current_identity,
    "predecessor_continuity_identity": expected_predecessor_identity,
    "current_release_source_commit": current.get("current_release_source_commit"),
}
for key, value in expected.items():
    if continuity.get(key) != value:
        raise SystemExit(f"continuity linkage mismatch: {key}")
if not valid_identity(continuity.get("current_anchor_identity")):
    raise SystemExit("invalid current anchor identity")
if continuity.get("predecessor_continuity_identity") is not None and not valid_identity(continuity.get("predecessor_continuity_identity")):
    raise SystemExit("invalid predecessor continuity identity")
if continuity.get("publication_policy") != "explicit-public-only" or continuity.get("classification_boundary") != "PUBLIC_ONLY" or any(continuity.get(k) is not False for k in flags):
    raise SystemExit("continuity evidence cannot authorize consequential action")
continuity_identity = continuity.get("continuity_digest", {})
continuity_core = {k: v for k, v in continuity.items() if k != "continuity_digest"}
if not valid_identity(continuity_identity) or continuity_identity["digest"] != digest(continuity_core):
    raise SystemExit("continuity digest mismatch")

print(f"ABE-031 anchor continuity validation PASS: state={expected_state}; deployment_authorized=false")
