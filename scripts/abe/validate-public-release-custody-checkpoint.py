#!/usr/bin/env python3
import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
QUEUE = ROOT / "config/abe/task-queue.json"
HISTORY = ROOT / "build/abe/public-release-custody-history.json"
CHECKPOINT = ROOT / "build/abe/public-release-custody-checkpoint.json"

def digest(value):
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()

queue = json.loads(QUEUE.read_text(encoding="utf-8"))
history = json.loads(HISTORY.read_text(encoding="utf-8"))
checkpoint = json.loads(CHECKPOINT.read_text(encoding="utf-8"))
if queue.get("authoritative_department_scope") != ["DO-DEP-01", "DO-DEP-14"] or queue.get("verified_baseline") != "DO-DEP-04":
    raise SystemExit("authoritative scope/baseline changed")
if queue.get("rules", {}).get("public_exposure") != "explicit-public-only" or any(queue.get("rules", {}).get(k) is not False for k in ("external_writes", "production_deploy", "destructive_actions")):
    raise SystemExit("authoritative safety gate changed")
if history.get("schema_version") != 1 or history.get("history_state") != "PASS_REPOSITORY_LOCAL_ONLY":
    raise SystemExit("invalid custody history state")
records = history.get("records")
if not isinstance(records, list) or not records or history.get("chain_length") != len(records):
    raise SystemExit("invalid custody history length")
source = history.get("source_commit", "")
if not re.fullmatch(r"[0-9a-f]{40}", source):
    raise SystemExit("invalid source identity")
previous = None
for index, record in enumerate(records):
    if record.get("sequence") != index or record.get("source_commit") != source:
        raise SystemExit("history sequence/source mismatch")
    if record.get("publication_policy") != "explicit-public-only" or record.get("classification_boundary") != "PUBLIC_ONLY":
        raise SystemExit("non-PUBLIC history rejected")
    rd = record.get("record_digest", {})
    core = {k: v for k, v in record.items() if k != "record_digest"}
    if rd.get("algorithm") != "sha256" or rd.get("digest") != digest(core):
        raise SystemExit("custody record digest mismatch")
    expected = None if index == 0 else previous
    if record.get("predecessor_digest") != expected:
        raise SystemExit("history continuity mismatch")
    previous = {"algorithm": "sha256", "digest": rd["digest"]}
hd = history.get("history_digest", {})
hcore = {k: v for k, v in history.items() if k != "history_digest"}
if hd.get("algorithm") != "sha256" or hd.get("digest") != digest(hcore):
    raise SystemExit("history digest mismatch")
if checkpoint.get("schema_version") != 1 or checkpoint.get("stage") != "ABE-023" or checkpoint.get("checkpoint_state") != "PASS_REPOSITORY_LOCAL_ONLY":
    raise SystemExit("invalid checkpoint state")
if checkpoint.get("source_commit") != source:
    raise SystemExit("stale or mismatched checkpoint source identity")
if checkpoint.get("history_identity") != {"algorithm": "sha256", "digest": hd["digest"]}:
    raise SystemExit("checkpoint/history digest mismatch")
if checkpoint.get("first_sequence") != records[0]["sequence"] or checkpoint.get("last_sequence") != records[-1]["sequence"] or checkpoint.get("record_count") != len(records):
    raise SystemExit("checkpoint sequence/count mismatch")
terminal = records[-1]["record_digest"]
if checkpoint.get("terminal_custody_digest") != {"algorithm": "sha256", "digest": terminal["digest"]}:
    raise SystemExit("terminal custody digest mismatch")
if checkpoint.get("continuity_assertion") != "STRICT_MONOTONIC_CONTIGUOUS" or checkpoint.get("publication_policy") != "explicit-public-only" or checkpoint.get("classification_boundary") != "PUBLIC_ONLY":
    raise SystemExit("checkpoint safety/continuity assertion mismatch")
flags = ("external_write_performed", "production_deploy_performed", "publication_performed", "destructive_action_performed", "secret_access_performed", "authorizes_deployment")
if any(checkpoint.get(k) is not False for k in flags):
    raise SystemExit("checkpoint cannot perform or authorize consequential action")
cd = checkpoint.get("checkpoint_digest", {})
ccore = {k: v for k, v in checkpoint.items() if k != "checkpoint_digest"}
if cd.get("algorithm") != "sha256" or cd.get("digest") != digest(ccore):
    raise SystemExit("checkpoint digest mismatch")
print(f"public release custody checkpoint validation PASS: source={source[:12]}; records={len(records)}; deployment_authorized=false")
