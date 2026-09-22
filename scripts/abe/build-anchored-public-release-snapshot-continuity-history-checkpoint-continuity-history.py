#!/usr/bin/env python3
import hashlib, json, re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CURRENT = ROOT / "build/abe/anchored-public-release-snapshot-continuity-history-checkpoint-continuity.json"
PREDECESSOR = ROOT / "build/abe/anchored-public-release-snapshot-continuity-history-checkpoint-continuity-history.previous.json"
OUT = ROOT / "build/abe/anchored-public-release-snapshot-continuity-history-checkpoint-continuity-history.json"


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()).hexdigest()


def valid_identity(value):
    return isinstance(value, dict) and value.get("algorithm") == "sha256" and re.fullmatch(r"[0-9a-f]{64}", value.get("digest", ""))


def require_identity(value, label):
    if not valid_identity(value):
        raise SystemExit(f"invalid {label}")
    return value


def validate_continuity(value):
    flags = ("external_write_performed", "production_deploy_performed", "publication_performed", "destructive_action_performed", "secret_access_performed", "authorizes_deployment")
    if value.get("schema_version") != 1 or value.get("stage") != "ABE-034" or value.get("continuity_state") not in {"GENESIS", "LINKED"}:
        raise SystemExit("ABE-035 requires validated ABE-034 checkpoint-continuity evidence")
    if value.get("publication_policy") != "explicit-public-only" or value.get("classification_boundary") != "PUBLIC_ONLY":
        raise SystemExit("non-PUBLIC checkpoint-continuity evidence rejected")
    if any(value.get(k) is not False for k in flags):
        raise SystemExit("consequential checkpoint-continuity evidence rejected")
    sequence = value.get("continuity_sequence")
    if not isinstance(sequence, int) or isinstance(sequence, bool) or sequence < 1:
        raise SystemExit("invalid ABE-034 continuity sequence")
    identity = require_identity(value.get("continuity_digest"), "ABE-034 continuity identity")
    core = {k: v for k, v in value.items() if k != "continuity_digest"}
    if identity["digest"] != digest(core):
        raise SystemExit("ABE-034 continuity digest mismatch")
    return identity, sequence


current = json.loads(CURRENT.read_text(encoding="utf-8"))
current_identity, continuity_sequence = validate_continuity(current)
checkpoint_identity = require_identity(current.get("current_checkpoint_identity"), "ABE-033 checkpoint identity")
terminal_history_identity = require_identity(current.get("terminal_history_identity"), "ABE-032 terminal history identity")
anchor_continuity_identity = require_identity(current.get("current_continuity_identity"), "ABE-031 anchor-continuity identity")
anchor_identity = require_identity(current.get("current_anchor_identity"), "ABE-030 anchor identity")
terminal_history_sequence = current.get("terminal_history_sequence")
if not isinstance(terminal_history_sequence, int) or isinstance(terminal_history_sequence, bool) or terminal_history_sequence < 1:
    raise SystemExit("invalid terminal history sequence")

predecessor_identity = None
history_state = "GENESIS"
history_sequence = 1
if PREDECESSOR.exists():
    predecessor = json.loads(PREDECESSOR.read_text(encoding="utf-8"))
    flags = ("external_write_performed", "production_deploy_performed", "publication_performed", "destructive_action_performed", "secret_access_performed", "authorizes_deployment")
    if predecessor.get("schema_version") != 1 or predecessor.get("stage") != "ABE-035" or predecessor.get("history_state") not in {"GENESIS", "LINKED"}:
        raise SystemExit("invalid predecessor checkpoint-continuity-history evidence")
    if predecessor.get("publication_policy") != "explicit-public-only" or predecessor.get("classification_boundary") != "PUBLIC_ONLY" or any(predecessor.get(k) is not False for k in flags):
        raise SystemExit("unsafe predecessor checkpoint-continuity-history evidence")
    predecessor_digest = require_identity(predecessor.get("history_digest"), "predecessor history identity")
    predecessor_core = {k: v for k, v in predecessor.items() if k != "history_digest"}
    if predecessor_digest["digest"] != digest(predecessor_core):
        raise SystemExit("predecessor history digest mismatch")
    predecessor_sequence = predecessor.get("history_sequence")
    if not isinstance(predecessor_sequence, int) or isinstance(predecessor_sequence, bool) or predecessor_sequence < 1:
        raise SystemExit("invalid predecessor history sequence")
    predecessor_current = require_identity(predecessor.get("current_continuity_identity"), "predecessor ABE-034 continuity identity")
    if predecessor_current == current_identity:
        raise SystemExit("duplicate/self-reference checkpoint-continuity history rejected")
    predecessor_identity = predecessor_digest
    history_state = "LINKED"
    history_sequence = predecessor_sequence + 1

core = {
    "schema_version": 1,
    "stage": "ABE-035",
    "history_state": history_state,
    "history_sequence": history_sequence,
    "current_continuity_sequence": continuity_sequence,
    "current_continuity_identity": current_identity,
    "current_checkpoint_identity": checkpoint_identity,
    "terminal_history_sequence": terminal_history_sequence,
    "terminal_history_identity": terminal_history_identity,
    "current_anchor_continuity_identity": anchor_continuity_identity,
    "current_anchor_identity": anchor_identity,
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
print(f"ABE-035 checkpoint continuity history build PASS: state={history_state}; sequence={history_sequence}; deployment_authorized=false")
