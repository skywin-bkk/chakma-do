#!/usr/bin/env python3
import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
QUEUE = ROOT / "config/abe/task-queue.json"
BUNDLE = ROOT / "build/abe/public-release-bundle.json"
ATTEST = ROOT / "build/abe/public-release-readiness.json"
GATE = ROOT / "build/abe/public-release-gate.json"
CUSTODY = ROOT / "build/abe/public-release-custody.json"

def digest(value):
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()

queue = json.loads(QUEUE.read_text(encoding="utf-8"))
bundle = json.loads(BUNDLE.read_text(encoding="utf-8"))
att = json.loads(ATTEST.read_text(encoding="utf-8"))
gate = json.loads(GATE.read_text(encoding="utf-8"))
custody = json.loads(CUSTODY.read_text(encoding="utf-8"))
if queue.get("authoritative_department_scope") != ["DO-DEP-01", "DO-DEP-14"] or queue.get("verified_baseline") != "DO-DEP-04":
    raise SystemExit("authoritative scope/baseline changed")
if queue.get("rules", {}).get("public_exposure") != "explicit-public-only" or any(queue.get("rules", {}).get(k) is not False for k in ("external_writes", "production_deploy", "destructive_actions")):
    raise SystemExit("authoritative safety gate changed")
if custody.get("schema_version") != 1 or custody.get("custody_state") != "PASS_REPOSITORY_LOCAL_ONLY":
    raise SystemExit("invalid custody state")
records = custody.get("records")
if not isinstance(records, list) or custody.get("chain_length") != len(records) or len(records) != 1:
    raise SystemExit("invalid or duplicate custody sequence")
r = records[0]
if r.get("sequence") != 0 or r.get("record_type") != "GENESIS" or r.get("predecessor_digest") is not None:
    raise SystemExit("invalid genesis/predecessor evidence")
source = r.get("source_commit", "")
if not re.fullmatch(r"[0-9a-f]{40}", source) or source != gate.get("source_commit") or source != att.get("source_commit") or source != bundle.get("source_commit"):
    raise SystemExit("stale or mismatched custody source commit")
if r.get("publication_policy") != "explicit-public-only" or r.get("classification_boundary") != "PUBLIC_ONLY":
    raise SystemExit("custody public boundary mismatch")
if any(x.get("classification") != "PUBLIC" for x in bundle.get("entries", [])):
    raise SystemExit("INTERNAL/RESTRICTED evidence rejected")
if r.get("bundle_integrity") != gate.get("bundle_integrity") or r.get("bundle_integrity") != att.get("bundle_integrity") or r.get("bundle_integrity") != bundle.get("bundle_integrity"):
    raise SystemExit("custody bundle integrity mismatch")
expected_gate = digest(gate)
if r.get("release_gate_digest") != {"algorithm": "sha256", "digest": expected_gate}:
    raise SystemExit("release gate custody digest mismatch")
rd = r.get("record_digest", {})
core = {k: v for k, v in r.items() if k != "record_digest"}
if rd.get("algorithm") != "sha256" or rd.get("digest") != digest(core):
    raise SystemExit("custody record digest mismatch")
if any(r.get(k) is not False for k in ("external_write_performed", "production_deploy_performed", "publication_performed", "authorizes_deployment")):
    raise SystemExit("custody cannot perform or authorize consequential action")
print(f"public release custody validation PASS: source={source[:12]}; chain_length=1; deployment_authorized=false")
