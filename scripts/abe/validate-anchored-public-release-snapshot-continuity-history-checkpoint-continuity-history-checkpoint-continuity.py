#!/usr/bin/env python3
import hashlib, json, re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
EVIDENCE = ROOT / "build/abe/anchored-public-release-snapshot-continuity-history-checkpoint-continuity-history-checkpoint-continuity.json"
CURRENT = ROOT / "build/abe/anchored-public-release-snapshot-continuity-history-checkpoint-continuity-history-checkpoint.json"


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()).hexdigest()


def identity(value, label):
    if not isinstance(value, dict) or value.get("algorithm") != "sha256" or not re.fullmatch(r"[0-9a-f]{64}", value.get("digest", "")):
        raise SystemExit(f"invalid {label}")
    return value


def positive_int(value, label):
    if not isinstance(value, int) or isinstance(value, bool) or value < 1:
        raise SystemExit(f"invalid {label}")
    return value


current = json.loads(CURRENT.read_text(encoding="utf-8"))
evidence = json.loads(EVIDENCE.read_text(encoding="utf-8"))
flags = ("external_write_performed", "production_deploy_performed", "publication_performed", "destructive_action_performed", "secret_access_performed", "authorizes_deployment")

if evidence.get("schema_version") != 1 or evidence.get("stage") != "ABE-037":
    raise SystemExit("invalid ABE-037 evidence envelope")
if evidence.get("continuity_state") not in {"GENESIS", "LINKED"}:
    raise SystemExit("invalid ABE-037 continuity state")
positive_int(evidence.get("continuity_sequence"), "ABE-037 continuity sequence")
if evidence.get("publication_policy") != "explicit-public-only" or evidence.get("classification_boundary") != "PUBLIC_ONLY":
    raise SystemExit("non-PUBLIC ABE-037 evidence rejected")
if any(evidence.get(k) is not False for k in flags):
    raise SystemExit("consequential ABE-037 evidence rejected")

continuity_identity = identity(evidence.get("continuity_digest"), "ABE-037 continuity identity")
core = {k: v for k, v in evidence.items() if k != "continuity_digest"}
if continuity_identity["digest"] != digest(core):
    raise SystemExit("ABE-037 continuity digest mismatch")

if current.get("schema_version") != 1 or current.get("stage") != "ABE-036" or current.get("checkpoint_state") != "SEALED":
    raise SystemExit("invalid current ABE-036 checkpoint")
if current.get("publication_policy") != "explicit-public-only" or current.get("classification_boundary") != "PUBLIC_ONLY" or any(current.get(k) is not False for k in flags):
    raise SystemExit("unsafe current ABE-036 checkpoint")
current_identity = identity(current.get("checkpoint_digest"), "current ABE-036 checkpoint identity")
current_core = {k: v for k, v in current.items() if k != "checkpoint_digest"}
if current_identity["digest"] != digest(current_core):
    raise SystemExit("current ABE-036 checkpoint digest mismatch")
if evidence.get("current_checkpoint_identity") != current_identity:
    raise SystemExit("ABE-037 is not bound to the authoritative ABE-036 checkpoint")

bindings = (
    ("terminal_history_sequence", "terminal_history_sequence", True),
    ("terminal_history_identity", "terminal_history_identity", False),
    ("current_abe034_continuity_sequence", "current_continuity_sequence", True),
    ("current_abe034_continuity_identity", "current_continuity_identity", False),
    ("current_abe033_checkpoint_identity", "current_checkpoint_identity", False),
    ("terminal_abe032_history_sequence", "terminal_abe032_history_sequence", True),
    ("terminal_abe032_history_identity", "terminal_abe032_history_identity", False),
    ("current_anchor_continuity_identity", "current_anchor_continuity_identity", False),
    ("current_anchor_identity", "current_anchor_identity", False),
    ("current_release_source_commit", "current_release_source_commit", False),
)
for evidence_key, current_key, numeric in bindings:
    value = evidence.get(evidence_key)
    if numeric:
        positive_int(value, evidence_key)
    elif evidence_key.endswith("identity"):
        identity(value, evidence_key)
    if value != current.get(current_key):
        raise SystemExit(f"ABE-037 upstream binding mismatch: {evidence_key}")

predecessor = evidence.get("predecessor_continuity_identity")
if evidence.get("continuity_state") == "GENESIS":
    if evidence.get("continuity_sequence") != 1 or predecessor is not None:
        raise SystemExit("invalid ABE-037 GENESIS semantics")
else:
    identity(predecessor, "ABE-037 predecessor continuity identity")
    if evidence.get("continuity_sequence") <= 1:
        raise SystemExit("invalid ABE-037 LINKED semantics")
    if predecessor == continuity_identity:
        raise SystemExit("ABE-037 self-reference rejected")

print(f"ABE-037 checkpoint continuity validation PASS: state={evidence['continuity_state']}; sequence={evidence['continuity_sequence']}; deployment_authorized=false")
