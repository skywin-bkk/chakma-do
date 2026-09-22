#!/usr/bin/env python3
import hashlib, json, re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HISTORY = ROOT / "build/abe/anchored-public-release-snapshot-continuity-history-anchor-continuity-history.json"
OUT = ROOT / "build/abe/anchored-public-release-snapshot-continuity-history-checkpoint.json"


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()).hexdigest()


def valid_identity(value):
    return isinstance(value, dict) and value.get("algorithm") == "sha256" and re.fullmatch(r"[0-9a-f]{64}", value.get("digest", ""))


def require_identity(value, label):
    if not valid_identity(value):
        raise SystemExit(f"invalid {label}")
    return value


history = json.loads(HISTORY.read_text(encoding="utf-8"))
flags = ("external_write_performed", "production_deploy_performed", "publication_performed", "destructive_action_performed", "secret_access_performed", "authorizes_deployment")
if history.get("schema_version") != 1 or history.get("stage") != "ABE-032" or history.get("history_state") not in {"GENESIS", "LINKED"}:
    raise SystemExit("ABE-033 requires validated ABE-032 history evidence")
if history.get("publication_policy") != "explicit-public-only" or history.get("classification_boundary") != "PUBLIC_ONLY":
    raise SystemExit("non-PUBLIC history evidence rejected")
if any(history.get(k) is not False for k in flags):
    raise SystemExit("consequential history evidence rejected")
sequence = history.get("sequence")
if not isinstance(sequence, int) or isinstance(sequence, bool) or sequence < 1:
    raise SystemExit("invalid terminal history sequence")
history_identity = require_identity(history.get("history_digest"), "ABE-032 history identity")
history_core = {k: v for k, v in history.items() if k != "history_digest"}
if history_identity["digest"] != digest(history_core):
    raise SystemExit("ABE-032 history digest mismatch")
continuity_identity = require_identity(history.get("current_continuity_identity"), "ABE-031 continuity identity")
anchor_identity = require_identity(history.get("current_anchor_identity"), "ABE-030 anchor identity")

core = {
    "schema_version": 1,
    "stage": "ABE-033",
    "checkpoint_state": "SEALED",
    "terminal_history_sequence": sequence,
    "terminal_history_identity": history_identity,
    "current_continuity_identity": continuity_identity,
    "current_anchor_identity": anchor_identity,
    "current_release_source_commit": history.get("current_release_source_commit"),
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
out["checkpoint_digest"] = {"algorithm": "sha256", "digest": digest(core)}
OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8")
print(f"ABE-033 checkpoint build PASS: terminal_sequence={sequence}; deployment_authorized=false")
