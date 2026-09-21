#!/usr/bin/env python3
import hashlib, json, re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CURRENT = ROOT / "build/abe/anchored-public-release-snapshot-continuity-history-anchor.json"
PREDECESSOR = ROOT / "build/abe/anchored-public-release-snapshot-continuity-history-anchor-continuity.previous.json"
OUT = ROOT / "build/abe/anchored-public-release-snapshot-continuity-history-anchor-continuity.json"


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()).hexdigest()


def valid_identity(value):
    return isinstance(value, dict) and value.get("algorithm") == "sha256" and re.fullmatch(r"[0-9a-f]{64}", value.get("digest", ""))


def validate_anchor(anchor):
    flags = ("external_write_performed", "production_deploy_performed", "publication_performed", "destructive_action_performed", "secret_access_performed", "authorizes_deployment")
    if anchor.get("schema_version") != 1 or anchor.get("stage") != "ABE-030" or anchor.get("anchor_state") != "PASS_REPOSITORY_LOCAL_ONLY":
        raise SystemExit("ABE-031 requires validated ABE-030 anchor")
    if anchor.get("publication_policy") != "explicit-public-only" or anchor.get("classification_boundary") != "PUBLIC_ONLY":
        raise SystemExit("non-PUBLIC anchor rejected")
    if any(anchor.get(k) is not False for k in flags):
        raise SystemExit("consequential anchor rejected")
    identity = anchor.get("anchor_digest", {})
    core = {k: v for k, v in anchor.items() if k != "anchor_digest"}
    if not valid_identity(identity) or identity["digest"] != digest(core):
        raise SystemExit("ABE-030 anchor digest mismatch")
    return identity


current = json.loads(CURRENT.read_text(encoding="utf-8"))
current_identity = validate_anchor(current)
predecessor_identity = None
continuity_state = "GENESIS"

if PREDECESSOR.exists():
    predecessor = json.loads(PREDECESSOR.read_text(encoding="utf-8"))
    if predecessor.get("schema_version") != 1 or predecessor.get("stage") != "ABE-031" or predecessor.get("continuity_state") not in {"GENESIS", "LINKED"}:
        raise SystemExit("invalid predecessor continuity evidence")
    predecessor_digest = predecessor.get("continuity_digest", {})
    predecessor_core = {k: v for k, v in predecessor.items() if k != "continuity_digest"}
    if not valid_identity(predecessor_digest) or predecessor_digest["digest"] != digest(predecessor_core):
        raise SystemExit("predecessor continuity digest mismatch")
    predecessor_current = predecessor.get("current_anchor_identity")
    if not valid_identity(predecessor_current):
        raise SystemExit("invalid predecessor anchor identity")
    if predecessor_current == current_identity:
        raise SystemExit("self-reference/non-monotonic anchor linkage rejected")
    predecessor_identity = predecessor_digest
    continuity_state = "LINKED"

core = {
    "schema_version": 1,
    "stage": "ABE-031",
    "continuity_state": continuity_state,
    "current_anchor_identity": current_identity,
    "predecessor_continuity_identity": predecessor_identity,
    "current_release_source_commit": current.get("current_release_source_commit"),
    "publication_policy": "explicit-public-only",
    "classification_boundary": "PUBLIC_ONLY",
    "external_write_performed": False,
    "production_deploy_performed": False,
    "publication_performed": False,
    "destructive_action_performed": False,
    "secret_access_performed": False,
    "authorizes_deployment": False,
}
out = dict(core)
out["continuity_digest"] = {"algorithm": "sha256", "digest": digest(core)}
OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8")
print(f"ABE-031 anchor continuity build PASS: state={continuity_state}; deployment_authorized=false")
