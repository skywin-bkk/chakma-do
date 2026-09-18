#!/usr/bin/env python3
import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
QUEUE = ROOT / "config/abe/task-queue.json"
CUSTODY = ROOT / "build/abe/public-release-custody.json"
HISTORY = ROOT / "build/abe/public-release-custody-history.json"

def digest(value):
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()

queue = json.loads(QUEUE.read_text(encoding="utf-8"))
custody = json.loads(CUSTODY.read_text(encoding="utf-8"))
history = json.loads(HISTORY.read_text(encoding="utf-8"))
if queue.get("authoritative_department_scope") != ["DO-DEP-01", "DO-DEP-14"] or queue.get("verified_baseline") != "DO-DEP-04":
    raise SystemExit("authoritative scope/baseline changed")
if queue.get("rules", {}).get("public_exposure") != "explicit-public-only" or any(queue.get("rules", {}).get(k) is not False for k in ("external_writes", "production_deploy", "destructive_actions")):
    raise SystemExit("authoritative safety gate changed")
if history.get("schema_version") != 1 or history.get("history_state") != "PASS_REPOSITORY_LOCAL_ONLY":
    raise SystemExit("invalid custody history state")
records = history.get("records")
if not isinstance(records, list) or not records or history.get("chain_length") != len(records):
    raise SystemExit("invalid custody history length")
if records != custody.get("records") or history.get("chain_length") != custody.get("chain_length"):
    raise SystemExit("custody history deletion, reordering, duplication, or mutation detected")
source = history.get("source_commit", "")
if not re.fullmatch(r"[0-9a-f]{40}", source):
    raise SystemExit("invalid custody history source commit")
previous = None
for index, record in enumerate(records):
    if record.get("sequence") != index:
        raise SystemExit("custody history sequence is not strictly monotonic")
    if record.get("source_commit") != source:
        raise SystemExit("stale source commit in custody history")
    if record.get("publication_policy") != "explicit-public-only" or record.get("classification_boundary") != "PUBLIC_ONLY":
        raise SystemExit("non-PUBLIC custody evidence rejected")
    rd = record.get("record_digest", {})
    core = {k: v for k, v in record.items() if k != "record_digest"}
    if rd.get("algorithm") != "sha256" or rd.get("digest") != digest(core):
        raise SystemExit("custody record digest mismatch")
    expected = None if index == 0 else previous
    if record.get("predecessor_digest") != expected:
        raise SystemExit("custody predecessor digest mismatch")
    if any(record.get(k) is not False for k in ("external_write_performed", "production_deploy_performed", "publication_performed", "authorizes_deployment")):
        raise SystemExit("custody record reports consequential action")
    previous = {"algorithm": "sha256", "digest": rd["digest"]}
if history.get("publication_policy") != "explicit-public-only" or history.get("classification_boundary") != "PUBLIC_ONLY":
    raise SystemExit("history public boundary mismatch")
if any(history.get(k) is not False for k in ("external_write_performed", "production_deploy_performed", "publication_performed", "authorizes_deployment")):
    raise SystemExit("custody history cannot perform or authorize consequential action")
hd = history.get("history_digest", {})
core = {k: v for k, v in history.items() if k != "history_digest"}
if hd.get("algorithm") != "sha256" or hd.get("digest") != digest(core):
    raise SystemExit("custody history digest mismatch")
print(f"public release custody history validation PASS: source={source[:12]}; chain_length={len(records)}; deployment_authorized=false")
