#!/usr/bin/env python3
import hashlib, json, re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CURRENT = ROOT / "build/abe/anchored-public-release-snapshot-continuity-history-checkpoint-continuity-history-checkpoint-continuity.json"
PREDECESSOR = ROOT / "build/abe/anchored-public-release-snapshot-continuity-history-checkpoint-continuity-history-checkpoint-continuity-history.previous.json"
OUT = ROOT / "build/abe/anchored-public-release-snapshot-continuity-history-checkpoint-continuity-history-checkpoint-continuity-history.json"
FLAGS = ("external_write_performed", "production_deploy_performed", "publication_performed", "destructive_action_performed", "secret_access_performed", "authorizes_deployment")

def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()).hexdigest()

def valid_identity(value):
    return isinstance(value, dict) and value.get("algorithm") == "sha256" and re.fullmatch(r"[0-9a-f]{64}", value.get("digest", ""))

def require_identity(value, label):
    if not valid_identity(value): raise SystemExit(f"invalid {label}")
    return value

def require_positive_int(value, label):
    if not isinstance(value, int) or isinstance(value, bool) or value < 1: raise SystemExit(f"invalid {label}")
    return value

def validate_safe(value, label):
    if value.get("publication_policy") != "explicit-public-only" or value.get("classification_boundary") != "PUBLIC_ONLY": raise SystemExit(f"non-PUBLIC {label} rejected")
    if any(value.get(k) is not False for k in FLAGS): raise SystemExit(f"consequential {label} rejected")

current = json.loads(CURRENT.read_text(encoding="utf-8"))
if current.get("schema_version") != 1 or current.get("stage") != "ABE-037" or current.get("continuity_state") not in {"GENESIS", "LINKED"}: raise SystemExit("ABE-038 requires validated ABE-037 continuity evidence")
validate_safe(current, "ABE-037 continuity")
current_identity = require_identity(current.get("continuity_digest"), "ABE-037 continuity identity")
if current_identity["digest"] != digest({k:v for k,v in current.items() if k != "continuity_digest"}): raise SystemExit("ABE-037 continuity digest mismatch")
continuity_sequence = require_positive_int(current.get("continuity_sequence"), "ABE-037 continuity sequence")
checkpoint_identity = require_identity(current.get("current_checkpoint_identity"), "ABE-036 checkpoint identity")
terminal_history_sequence = require_positive_int(current.get("terminal_history_sequence"), "ABE-035 terminal history sequence")
terminal_history_identity = require_identity(current.get("terminal_history_identity"), "ABE-035 terminal history identity")
abe034_sequence = require_positive_int(current.get("current_abe034_continuity_sequence"), "ABE-034 continuity sequence")
abe034_identity = require_identity(current.get("current_abe034_continuity_identity"), "ABE-034 continuity identity")
abe032_sequence = require_positive_int(current.get("terminal_abe032_history_sequence"), "ABE-032 terminal history sequence")
abe032_identity = require_identity(current.get("terminal_abe032_history_identity"), "ABE-032 terminal history identity")
anchor_continuity_identity = require_identity(current.get("current_anchor_continuity_identity"), "ABE-031 anchor-continuity identity")
anchor_identity = require_identity(current.get("current_anchor_identity"), "ABE-030 anchor identity")

predecessor_identity, state, sequence = None, "GENESIS", 1
if PREDECESSOR.exists():
    predecessor = json.loads(PREDECESSOR.read_text(encoding="utf-8"))
    if predecessor.get("schema_version") != 1 or predecessor.get("stage") != "ABE-038" or predecessor.get("history_state") not in {"GENESIS", "LINKED"}: raise SystemExit("invalid predecessor ABE-038 history")
    validate_safe(predecessor, "ABE-038 predecessor")
    predecessor_identity = require_identity(predecessor.get("history_digest"), "predecessor ABE-038 history identity")
    if predecessor_identity["digest"] != digest({k:v for k,v in predecessor.items() if k != "history_digest"}): raise SystemExit("predecessor ABE-038 history digest mismatch")
    predecessor_sequence = require_positive_int(predecessor.get("history_sequence"), "predecessor ABE-038 history sequence")
    if predecessor.get("current_continuity_identity") == current_identity: raise SystemExit("duplicate/self-reference ABE-037 continuity rejected")
    sequence, state = predecessor_sequence + 1, "LINKED"

core = {
    "schema_version": 1, "stage": "ABE-038", "history_state": state, "history_sequence": sequence,
    "current_continuity_sequence": continuity_sequence, "current_continuity_identity": current_identity,
    "current_checkpoint_identity": checkpoint_identity,
    "terminal_abe035_history_sequence": terminal_history_sequence, "terminal_abe035_history_identity": terminal_history_identity,
    "current_abe034_continuity_sequence": abe034_sequence, "current_abe034_continuity_identity": abe034_identity,
    "terminal_abe032_history_sequence": abe032_sequence, "terminal_abe032_history_identity": abe032_identity,
    "current_anchor_continuity_identity": anchor_continuity_identity, "current_anchor_identity": anchor_identity,
    "predecessor_history_identity": predecessor_identity, "current_release_source_commit": current.get("current_release_source_commit"),
    "publication_policy": "explicit-public-only", "classification_boundary": "PUBLIC_ONLY",
    "external_write_performed": False, "production_deploy_performed": False, "publication_performed": False,
    "destructive_action_performed": False, "secret_access_performed": False, "authorizes_deployment": False,
}
out = dict(core); out["history_digest"] = {"algorithm":"sha256", "digest":digest(core)}
OUT.parent.mkdir(parents=True, exist_ok=True); OUT.write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8")
print(f"ABE-038 checkpoint continuity history build PASS: state={state}; sequence={sequence}; deployment_authorized=false")
