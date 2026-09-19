#!/usr/bin/env python3
import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CHECKPOINT = ROOT / "build/abe/public-release-custody-checkpoint.json"
OUT = ROOT / "build/abe/public-release-custody-checkpoint-continuity.json"

def digest(value):
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()

checkpoint = json.loads(CHECKPOINT.read_text(encoding="utf-8"))
if checkpoint.get("schema_version") != 1 or checkpoint.get("stage") != "ABE-023" or checkpoint.get("checkpoint_state") != "PASS_REPOSITORY_LOCAL_ONLY":
    raise SystemExit("ABE-024 requires validated ABE-023 checkpoint evidence")
source = checkpoint.get("source_commit", "")
if not re.fullmatch(r"[0-9a-f]{40}", source):
    raise SystemExit("invalid checkpoint source identity")
for field in ("history_identity", "checkpoint_digest"):
    value = checkpoint.get(field, {})
    if value.get("algorithm") != "sha256" or not re.fullmatch(r"[0-9a-f]{64}", value.get("digest", "")):
        raise SystemExit(f"invalid {field}")
core = {k: v for k, v in checkpoint.items() if k != "checkpoint_digest"}
if checkpoint["checkpoint_digest"]["digest"] != digest(core):
    raise SystemExit("checkpoint digest mismatch")
if checkpoint.get("publication_policy") != "explicit-public-only" or checkpoint.get("classification_boundary") != "PUBLIC_ONLY":
    raise SystemExit("non-PUBLIC checkpoint rejected")
flags = ("external_write_performed", "production_deploy_performed", "publication_performed", "destructive_action_performed", "secret_access_performed", "authorizes_deployment")
if any(checkpoint.get(k) is not False for k in flags):
    raise SystemExit("checkpoint cannot perform or authorize consequential action")
record_core = {
    "checkpoint_sequence": 0,
    "source_commit": source,
    "history_identity": checkpoint["history_identity"],
    "checkpoint_digest": checkpoint["checkpoint_digest"],
    "predecessor_checkpoint_digest": None,
    "publication_policy": "explicit-public-only",
    "classification_boundary": "PUBLIC_ONLY"
}
record = dict(record_core)
record["continuity_record_digest"] = {"algorithm": "sha256", "digest": digest(record_core)}
continuity_core = {
    "schema_version": 1,
    "stage": "ABE-024",
    "continuity_state": "PASS_REPOSITORY_LOCAL_ONLY",
    "source_commit": source,
    "history_identity": checkpoint["history_identity"],
    "checkpoint_count": 1,
    "records": [record],
    "continuity_assertion": "STRICT_MONOTONIC_CHECKPOINT_CHAIN",
    "publication_policy": "explicit-public-only",
    "classification_boundary": "PUBLIC_ONLY",
    "external_write_performed": False,
    "production_deploy_performed": False,
    "publication_performed": False,
    "destructive_action_performed": False,
    "secret_access_performed": False,
    "authorizes_deployment": False
}
out = dict(continuity_core)
out["continuity_digest"] = {"algorithm": "sha256", "digest": digest(continuity_core)}
OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8")
print(f"public release custody checkpoint continuity PASS: source={source[:12]}; checkpoints=1; deployment_authorized=false")
