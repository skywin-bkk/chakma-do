#!/usr/bin/env python3
import hashlib, json, re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CURRENT = ROOT / "build/abe/anchored-public-release-snapshot-continuity-history-anchor-continuity.json"
PREDECESSOR = ROOT / "build/abe/anchored-public-release-snapshot-continuity-history-anchor-continuity-history.previous.json"
OUT = ROOT / "build/abe/anchored-public-release-snapshot-continuity-history-anchor-continuity-history.json"


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()).hexdigest()


def valid_identity(value):
    return isinstance(value, dict) and value.get("algorithm") == "sha256" and re.fullmatch(r"[0-9a-f]{64}", value.get("digest", ""))


def validate_continuity(value):
    flags = ("external_write_performed", "production_deploy_performed", "publication_performed", "destructive_action_performed", "secret_access_performed", "authorizes_deployment")
    if value.get("schema_version") != 1 or value.get("stage") != "ABE-031" or value.get("continuity_state") not in {"GENESIS", "LINKED"}:
        raise SystemExit("ABE-032 requires validated ABE-031 continuity evidence")
    if value.get("publication_policy") != "explicit-public-only" or value.get("classification_boundary") != "PUBLIC_ONLY":
        raise SystemExit("non-PUBLIC continuity evidence rejected")
    if any(value.get(k) is not False for k in flags):
        raise SystemExit("consequential continuity evidence rejected")
    current_anchor = value.get("current_anchor_identity")
    identity = value.get("continuity_digest", {})
    core = {k: v for k, v in value.items() if k != "continuity_digest"}
    if not valid_identity(current_anchor):
        raise SystemExit("invalid ABE-030 anchor identity")
    if not valid_identity(identity) or identity["digest"] != digest(core):
        raise SystemExit("ABE-031 continuity digest mismatch")
    return identity, current_anchor


current = json.loads(CURRENT.read_text(encoding="utf-8"))
current_identity, current_anchor_identity = validate_continuity(current)
predecessor_identity = None
history_state = "GENESIS"
sequence = 1

if PREDECESSOR.exists():
    predecessor = json.loads(PREDECESSOR.read_text(encoding="utf-8"))
    if predecessor.get("schema_version") != 1 or predecessor.get("stage") != "ABE-032" or predecessor.get("history_state") not in {"GENESIS", "LINKED"}:
        raise SystemExit("invalid predecessor history evidence")
    predecessor_digest = predecessor.get("history_digest", {})
    predecessor_core = {k: v for k, v in predecessor.items() if k != "history_digest"}
    if not valid_identity(predecessor_digest) or predecessor_digest["digest"] != digest(predecessor_core):
        raise SystemExit("predecessor history digest mismatch")
    predecessor_sequence = predecessor.get("sequence")
    if not isinstance(predecessor_sequence, int) or isinstance(predecessor_sequence, bool) or predecessor_sequence < 1:
        raise SystemExit("invalid predecessor history sequence")
    predecessor_current = predecessor.get("current_continuity_identity")
    if not valid_identity(predecessor_current):
        raise SystemExit("invalid predecessor continuity identity")
    if predecessor_current == current_identity:
        raise SystemExit("duplicate/self-reference continuity history rejected")
    predecessor_identity = predecessor_digest
    history_state = "LINKED"
    sequence = predecessor_sequence + 1

core = {
    "schema_version": 1,
    "stage": "ABE-032",
    "history_state": history_state,
    "sequence": sequence,
    "current_continuity_identity": current_identity,
    "current_anchor_identity": current_anchor_identity,
    "predecessor_history_identity": predecessor_identity,
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
out["history_digest"] = {"algorithm": "sha256", "digest": digest(core)}
OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8")
print(f"ABE-032 continuity history build PASS: state={history_state}; sequence={sequence}; deployment_authorized=false")
