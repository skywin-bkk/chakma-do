#!/usr/bin/env python3
import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
GATE = ROOT / "build/abe/public-release-gate.json"
OUT = ROOT / "build/abe/public-release-custody.json"

def canonical_digest(value):
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()

gate = json.loads(GATE.read_text(encoding="utf-8"))
if gate.get("schema_version") != 1 or gate.get("gate_state") != "PASS_REPOSITORY_LOCAL_ONLY":
    raise SystemExit("custody requires validated repository-local release gate")
source = gate.get("source_commit", "")
if not re.fullmatch(r"[0-9a-f]{40}", source):
    raise SystemExit("invalid release gate source commit")
if gate.get("publication_policy") != "explicit-public-only" or gate.get("classification_boundary") != "PUBLIC_ONLY":
    raise SystemExit("release gate public boundary mismatch")
if any(gate.get(k) is not False for k in ("external_write_performed", "production_deploy_performed", "publication_performed", "authorizes_deployment")):
    raise SystemExit("release gate reports or authorizes consequential action")
integrity = gate.get("bundle_integrity", {})
if integrity.get("algorithm") != "sha256" or not re.fullmatch(r"[0-9a-f]{64}", integrity.get("digest", "")):
    raise SystemExit("invalid bundle integrity evidence")

gate_digest = canonical_digest(gate)
record_core = {
    "schema_version": 1,
    "sequence": 0,
    "record_type": "GENESIS",
    "source_commit": source,
    "publication_policy": "explicit-public-only",
    "classification_boundary": "PUBLIC_ONLY",
    "bundle_integrity": integrity,
    "release_gate_digest": {"algorithm": "sha256", "digest": gate_digest},
    "predecessor_digest": None,
    "external_write_performed": False,
    "production_deploy_performed": False,
    "publication_performed": False,
    "authorizes_deployment": False
}
record = dict(record_core)
record["record_digest"] = {"algorithm": "sha256", "digest": canonical_digest(record_core)}
out = {
    "schema_version": 1,
    "custody_state": "PASS_REPOSITORY_LOCAL_ONLY",
    "chain_length": 1,
    "records": [record]
}
OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8")
print(f"public release custody PASS: source={source[:12]}; sequence=0; deployment_authorized=false")
