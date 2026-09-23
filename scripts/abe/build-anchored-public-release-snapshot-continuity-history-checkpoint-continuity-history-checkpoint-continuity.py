#!/usr/bin/env python3
import hashlib, json, re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CURRENT = ROOT / "build/abe/anchored-public-release-snapshot-continuity-history-checkpoint-continuity-history-checkpoint.json"
PREDECESSOR = ROOT / "build/abe/anchored-public-release-snapshot-continuity-history-checkpoint-continuity-history-checkpoint-continuity.previous.json"
OUT = ROOT / "build/abe/anchored-public-release-snapshot-continuity-history-checkpoint-continuity-history-checkpoint-continuity.json"


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()).hexdigest()


def valid_identity(value):
    return isinstance(value, dict) and value.get("algorithm") == "sha256" and re.fullmatch(r"[0-9a-f]{64}", value.get("digest", ""))


def require_identity(value, label):
    if not valid_identity(value):
        raise SystemExit(f"invalid {label}")
    return value


def require_positive_int(value, label):
    if not isinstance(value, int) or isinstance(value, bool) or value < 1:
        raise SystemExit(f"invalid {label}")
    return value


def validate_checkpoint(value):
    flags = ("external_write_performed", "production_deploy_performed", "publication_performed", "destructive_action_performed", "secret_access_performed", "authorizes_deployment")
    if value.get("schema_version") != 1 or value.get("stage") != "ABE-036" or value.get("checkpoint_state") != "SEALED":
        raise SystemExit("ABE-037 requires validated ABE-036 checkpoint evidence")
    if value.get("publication_policy") != "explicit-public-only" or value.get("classification_boundary") != "PUBLIC_ONLY":
        raise SystemExit("non-PUBLIC ABE-036 checkpoint evidence rejected")
    if any(value.get(k) is not False for k in flags):
        raise SystemExit("consequential ABE-036 checkpoint evidence rejected")
    identity = require_identity(value.get("checkpoint_digest"), "ABE-036 checkpoint identity")
    core = {k: v for k, v in value.items() if k != "checkpoint_digest"}
    if identity["digest"] != digest(core):
        raise SystemExit("ABE-036 checkpoint digest mismatch")
    return identity


current = json.loads(CURRENT.read_text(encoding="utf-8"))
current_identity = validate_checkpoint(current)
terminal_history_sequence = require_positive_int(current.get("terminal_history_sequence"), "ABE-035 terminal history sequence")
continuity_sequence = require_positive_int(current.get("current_continuity_sequence"), "ABE-034 continuity sequence")
terminal_abe032_history_sequence = require_positive_int(current.get("terminal_abe032_history_sequence"), "ABE-032 terminal history sequence")
terminal_history_identity = require_identity(current.get("terminal_history_identity"), "ABE-035 terminal history identity")
current_continuity_identity = require_identity(current.get("current_continuity_identity"), "ABE-034 continuity identity")
current_checkpoint_identity = require_identity(current.get("current_checkpoint_identity"), "ABE-033 checkpoint identity")
terminal_abe032_history_identity = require_identity(current.get("terminal_abe032_history_identity"), "ABE-032 terminal history identity")
anchor_continuity_identity = require_identity(current.get("current_anchor_continuity_identity"), "ABE-031 anchor-continuity identity")
anchor_identity = require_identity(current.get("current_anchor_identity"), "ABE-030 anchor identity")

predecessor_identity = None
state = "GENESIS"
sequence = 1
if PREDECESSOR.exists():
    predecessor = json.loads(PREDECESSOR.read_text(encoding="utf-8"))
    flags = ("external_write_performed", "production_deploy_performed", "publication_performed", "destructive_action_performed", "secret_access_performed", "authorizes_deployment")
    if predecessor.get("schema_version") != 1 or predecessor.get("stage") != "ABE-037" or predecessor.get("continuity_state") not in {"GENESIS", "LINKED"}:
        raise SystemExit("invalid predecessor ABE-037 continuity evidence")
    if predecessor.get("publication_policy") != "explicit-public-only" or predecessor.get("classification_boundary") != "PUBLIC_ONLY" or any(predecessor.get(k) is not False for k in flags):
        raise SystemExit("unsafe predecessor ABE-037 continuity evidence")
    predecessor_identity = require_identity(predecessor.get("continuity_digest"), "predecessor ABE-037 continuity identity")
    predecessor_core = {k: v for k, v in predecessor.items() if k != "continuity_digest"}
    if predecessor_identity["digest"] != digest(predecessor_core):
        raise SystemExit("predecessor ABE-037 continuity digest mismatch")
    predecessor_sequence = require_positive_int(predecessor.get("continuity_sequence"), "predecessor ABE-037 continuity sequence")
    predecessor_current = require_identity(predecessor.get("current_checkpoint_identity"), "predecessor ABE-036 checkpoint identity")
    if predecessor_current == current_identity:
        raise SystemExit("duplicate/self-reference ABE-036 checkpoint rejected")
    sequence = predecessor_sequence + 1
    state = "LINKED"

core = {
    "schema_version": 1,
    "stage": "ABE-037",
    "continuity_state": state,
    "continuity_sequence": sequence,
    "current_checkpoint_identity": current_identity,
    "terminal_history_sequence": terminal_history_sequence,
    "terminal_history_identity": terminal_history_identity,
    "current_abe034_continuity_sequence": continuity_sequence,
    "current_abe034_continuity_identity": current_continuity_identity,
    "current_abe033_checkpoint_identity": current_checkpoint_identity,
    "terminal_abe032_history_sequence": terminal_abe032_history_sequence,
    "terminal_abe032_history_identity": terminal_abe032_history_identity,
    "current_anchor_continuity_identity": anchor_continuity_identity,
    "current_anchor_identity": anchor_identity,
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
print(f"ABE-037 checkpoint continuity build PASS: state={state}; sequence={sequence}; deployment_authorized=false")
