#!/usr/bin/env python3
import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HISTORY = ROOT / "build/abe/public-release-custody-history.json"
OUT = ROOT / "build/abe/public-release-custody-checkpoint.json"

def digest(value):
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()

history = json.loads(HISTORY.read_text(encoding="utf-8"))
if history.get("schema_version") != 1 or history.get("history_state") != "PASS_REPOSITORY_LOCAL_ONLY":
    raise SystemExit("checkpoint requires validated repository-local custody history")
records = history.get("records")
if not isinstance(records, list) or not records or history.get("chain_length") != len(records):
    raise SystemExit("invalid custody history input")
source = history.get("source_commit", "")
if not re.fullmatch(r"[0-9a-f]{40}", source):
    raise SystemExit("invalid custody history source commit")
if history.get("publication_policy") != "explicit-public-only" or history.get("classification_boundary") != "PUBLIC_ONLY":
    raise SystemExit("non-PUBLIC custody history rejected")
if any(history.get(k) is not False for k in ("external_write_performed", "production_deploy_performed", "publication_performed", "authorizes_deployment")):
    raise SystemExit("checkpoint input cannot contain consequential action")
for index, record in enumerate(records):
    if record.get("sequence") != index or record.get("source_commit") != source:
        raise SystemExit("custody history continuity/source mismatch")
terminal = records[-1].get("record_digest", {})
hd = history.get("history_digest", {})
if terminal.get("algorithm") != "sha256" or not re.fullmatch(r"[0-9a-f]{64}", terminal.get("digest", "")):
    raise SystemExit("invalid terminal custody digest")
core_history = {k: v for k, v in history.items() if k != "history_digest"}
if hd.get("algorithm") != "sha256" or hd.get("digest") != digest(core_history):
    raise SystemExit("custody history digest mismatch")
checkpoint_core = {
    "schema_version": 1,
    "stage": "ABE-023",
    "checkpoint_state": "PASS_REPOSITORY_LOCAL_ONLY",
    "source_commit": source,
    "history_identity": {"algorithm": "sha256", "digest": hd["digest"]},
    "first_sequence": records[0]["sequence"],
    "last_sequence": records[-1]["sequence"],
    "record_count": len(records),
    "terminal_custody_digest": {"algorithm": "sha256", "digest": terminal["digest"]},
    "continuity_assertion": "STRICT_MONOTONIC_CONTIGUOUS",
    "publication_policy": "explicit-public-only",
    "classification_boundary": "PUBLIC_ONLY",
    "external_write_performed": False,
    "production_deploy_performed": False,
    "publication_performed": False,
    "destructive_action_performed": False,
    "secret_access_performed": False,
    "authorizes_deployment": False
}
out = dict(checkpoint_core)
out["checkpoint_digest"] = {"algorithm": "sha256", "digest": digest(checkpoint_core)}
OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8")
print(f"public release custody checkpoint PASS: source={source[:12]}; records={len(records)}; deployment_authorized=false")
