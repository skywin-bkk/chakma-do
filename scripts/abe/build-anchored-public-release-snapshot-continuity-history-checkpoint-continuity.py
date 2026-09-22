#!/usr/bin/env python3
import hashlib, json, re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CURRENT = ROOT / "build/abe/anchored-public-release-snapshot-continuity-history-checkpoint.json"
PREDECESSOR = ROOT / "build/abe/anchored-public-release-snapshot-continuity-history-checkpoint-continuity.previous.json"
OUT = ROOT / "build/abe/anchored-public-release-snapshot-continuity-history-checkpoint-continuity.json"


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()).hexdigest()


def valid_identity(value):
    return isinstance(value, dict) and value.get("algorithm") == "sha256" and re.fullmatch(r"[0-9a-f]{64}", value.get("digest", ""))


def require_identity(value, label):
    if not valid_identity(value):
        raise SystemExit(f"invalid {label}")
    return value


def validate_checkpoint(checkpoint):
    flags = ("external_write_performed", "production_deploy_performed", "publication_performed", "destructive_action_performed", "secret_access_performed", "authorizes_deployment")
    if checkpoint.get("schema_version") != 1 or checkpoint.get("stage") != "ABE-033" or checkpoint.get("checkpoint_state") != "SEALED":
        raise SystemExit("ABE-034 requires validated ABE-033 checkpoint evidence")
    if checkpoint.get("publication_policy") != "explicit-public-only" or checkpoint.get("classification_boundary") != "PUBLIC_ONLY":
        raise SystemExit("non-PUBLIC checkpoint rejected")
    if any(checkpoint.get(k) is not False for k in flags):
        raise SystemExit("consequential checkpoint rejected")
    sequence = checkpoint.get("terminal_history_sequence")
    if not isinstance(sequence, int) or isinstance(sequence, bool) or sequence < 1:
        raise SystemExit("invalid terminal history sequence")
    checkpoint_identity = require_identity(checkpoint.get("checkpoint_digest"), "ABE-033 checkpoint identity")
    checkpoint_core = {k: v for k, v in checkpoint.items() if k != "checkpoint_digest"}
    if checkpoint_identity["digest"] != digest(checkpoint_core):
        raise SystemExit("ABE-033 checkpoint digest mismatch")
    return checkpoint_identity, sequence


current = json.loads(CURRENT.read_text(encoding="utf-8"))
current_identity, terminal_sequence = validate_checkpoint(current)
terminal_history_identity = require_identity(current.get("terminal_history_identity"), "ABE-032 terminal history identity")
continuity_identity = require_identity(current.get("current_continuity_identity"), "ABE-031 continuity identity")
anchor_identity = require_identity(current.get("current_anchor_identity"), "ABE-030 anchor identity")

predecessor_identity = None
continuity_sequence = 1
continuity_state = "GENESIS"
if PREDECESSOR.exists():
    predecessor = json.loads(PREDECESSOR.read_text(encoding="utf-8"))
    flags = ("external_write_performed", "production_deploy_performed", "publication_performed", "destructive_action_performed", "secret_access_performed", "authorizes_deployment")
    if predecessor.get("schema_version") != 1 or predecessor.get("stage") != "ABE-034" or predecessor.get("continuity_state") not in {"GENESIS", "LINKED"}:
        raise SystemExit("invalid predecessor checkpoint-continuity evidence")
    if predecessor.get("publication_policy") != "explicit-public-only" or predecessor.get("classification_boundary") != "PUBLIC_ONLY" or any(predecessor.get(k) is not False for k in flags):
        raise SystemExit("unsafe predecessor checkpoint-continuity evidence")
    predecessor_digest = require_identity(predecessor.get("continuity_digest"), "predecessor continuity identity")
    predecessor_core = {k: v for k, v in predecessor.items() if k != "continuity_digest"}
    if predecessor_digest["digest"] != digest(predecessor_core):
        raise SystemExit("predecessor continuity digest mismatch")
    predecessor_sequence = predecessor.get("continuity_sequence")
    if not isinstance(predecessor_sequence, int) or isinstance(predecessor_sequence, bool) or predecessor_sequence < 1:
        raise SystemExit("invalid predecessor continuity sequence")
    predecessor_current = require_identity(predecessor.get("current_checkpoint_identity"), "predecessor checkpoint identity")
    if predecessor_current == current_identity:
        raise SystemExit("self-reference/non-monotonic checkpoint linkage rejected")
    predecessor_identity = predecessor_digest
    continuity_sequence = predecessor_sequence + 1
    continuity_state = "LINKED"

core = {
    "schema_version": 1,
    "stage": "ABE-034",
    "continuity_state": continuity_state,
    "continuity_sequence": continuity_sequence,
    "current_checkpoint_identity": current_identity,
    "predecessor_continuity_identity": predecessor_identity,
    "terminal_history_sequence": terminal_sequence,
    "terminal_history_identity": terminal_history_identity,
    "current_continuity_identity": continuity_identity,
    "current_anchor_identity": anchor_identity,
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
print(f"ABE-034 checkpoint continuity build PASS: state={continuity_state}; sequence={continuity_sequence}; deployment_authorized=false")
