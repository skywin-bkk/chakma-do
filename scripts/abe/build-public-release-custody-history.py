#!/usr/bin/env python3
import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CUSTODY = ROOT / "build/abe/public-release-custody.json"
OUT = ROOT / "build/abe/public-release-custody-history.json"

def digest(value):
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()

custody = json.loads(CUSTODY.read_text(encoding="utf-8"))
if custody.get("schema_version") != 1 or custody.get("custody_state") != "PASS_REPOSITORY_LOCAL_ONLY":
    raise SystemExit("history requires validated repository-local custody")
records = custody.get("records")
if not isinstance(records, list) or not records or custody.get("chain_length") != len(records):
    raise SystemExit("invalid custody input")

history_records = []
previous = None
source = None
for index, record in enumerate(records):
    if record.get("sequence") != index:
        raise SystemExit("custody sequence is not strictly monotonic")
    current_source = record.get("source_commit", "")
    if not re.fullmatch(r"[0-9a-f]{40}", current_source):
        raise SystemExit("invalid custody source commit")
    if source is None:
        source = current_source
    elif current_source != source:
        raise SystemExit("stale or mismatched source commit in custody chain")
    if record.get("publication_policy") != "explicit-public-only" or record.get("classification_boundary") != "PUBLIC_ONLY":
        raise SystemExit("non-PUBLIC custody evidence rejected")
    if any(record.get(k) is not False for k in ("external_write_performed", "production_deploy_performed", "publication_performed", "authorizes_deployment")):
        raise SystemExit("custody history cannot contain consequential action")
    rd = record.get("record_digest", {})
    core = {k: v for k, v in record.items() if k != "record_digest"}
    if rd.get("algorithm") != "sha256" or rd.get("digest") != digest(core):
        raise SystemExit("custody record digest mismatch")
    expected_predecessor = None if index == 0 else previous
    if record.get("predecessor_digest") != expected_predecessor:
        raise SystemExit("custody predecessor digest mismatch")
    previous = {"algorithm": "sha256", "digest": rd["digest"]}
    history_records.append(record)

history_core = {
    "schema_version": 1,
    "history_state": "PASS_REPOSITORY_LOCAL_ONLY",
    "source_commit": source,
    "publication_policy": "explicit-public-only",
    "classification_boundary": "PUBLIC_ONLY",
    "chain_length": len(history_records),
    "records": history_records,
    "external_write_performed": False,
    "production_deploy_performed": False,
    "publication_performed": False,
    "authorizes_deployment": False
}
out = dict(history_core)
out["history_digest"] = {"algorithm": "sha256", "digest": digest(history_core)}
OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8")
print(f"public release custody history PASS: source={source[:12]}; chain_length={len(history_records)}; deployment_authorized=false")
