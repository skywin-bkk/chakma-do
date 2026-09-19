#!/usr/bin/env python3
import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
QUEUE = ROOT / "config/abe/task-queue.json"
CHECKPOINT = ROOT / "build/abe/public-release-custody-checkpoint.json"
CONTINUITY = ROOT / "build/abe/public-release-custody-checkpoint-continuity.json"

def digest(value):
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()

queue = json.loads(QUEUE.read_text(encoding="utf-8"))
checkpoint = json.loads(CHECKPOINT.read_text(encoding="utf-8"))
continuity = json.loads(CONTINUITY.read_text(encoding="utf-8"))
if queue.get("authoritative_department_scope") != ["DO-DEP-01", "DO-DEP-14"] or queue.get("verified_baseline") != "DO-DEP-04":
    raise SystemExit("authoritative scope/baseline changed")
rules = queue.get("rules", {})
if rules.get("public_exposure") != "explicit-public-only" or any(rules.get(k) is not False for k in ("external_writes", "production_deploy", "destructive_actions")):
    raise SystemExit("authoritative safety gate changed")
if checkpoint.get("schema_version") != 1 or checkpoint.get("stage") != "ABE-023" or checkpoint.get("checkpoint_state") != "PASS_REPOSITORY_LOCAL_ONLY":
    raise SystemExit("invalid ABE-023 checkpoint")
source = checkpoint.get("source_commit", "")
if not re.fullmatch(r"[0-9a-f]{40}", source):
    raise SystemExit("invalid source identity")
cd = checkpoint.get("checkpoint_digest", {})
ccore = {k: v for k, v in checkpoint.items() if k != "checkpoint_digest"}
if cd.get("algorithm") != "sha256" or cd.get("digest") != digest(ccore):
    raise SystemExit("checkpoint digest mismatch")
if checkpoint.get("publication_policy") != "explicit-public-only" or checkpoint.get("classification_boundary") != "PUBLIC_ONLY":
    raise SystemExit("non-PUBLIC checkpoint rejected")
if continuity.get("schema_version") != 1 or continuity.get("stage") != "ABE-024" or continuity.get("continuity_state") != "PASS_REPOSITORY_LOCAL_ONLY":
    raise SystemExit("invalid checkpoint continuity state")
if continuity.get("source_commit") != source or continuity.get("history_identity") != checkpoint.get("history_identity"):
    raise SystemExit("stale or mismatched source/history identity")
records = continuity.get("records")
if not isinstance(records, list) or not records or continuity.get("checkpoint_count") != len(records):
    raise SystemExit("invalid checkpoint continuity length")
previous = None
for index, record in enumerate(records):
    if record.get("checkpoint_sequence") != index:
        raise SystemExit("checkpoint rollback/fork/gap/reorder/duplication detected")
    if record.get("source_commit") != source or record.get("history_identity") != checkpoint.get("history_identity"):
        raise SystemExit("checkpoint continuity identity mismatch")
    if record.get("predecessor_checkpoint_digest") != previous:
        raise SystemExit("predecessor checkpoint digest mismatch")
    if record.get("publication_policy") != "explicit-public-only" or record.get("classification_boundary") != "PUBLIC_ONLY":
        raise SystemExit("non-PUBLIC continuity record rejected")
    rd = record.get("continuity_record_digest", {})
    rcore = {k: v for k, v in record.items() if k != "continuity_record_digest"}
    if rd.get("algorithm") != "sha256" or rd.get("digest") != digest(rcore):
        raise SystemExit("continuity record digest mismatch")
    current_checkpoint = record.get("checkpoint_digest", {})
    if current_checkpoint.get("algorithm") != "sha256" or not re.fullmatch(r"[0-9a-f]{64}", current_checkpoint.get("digest", "")):
        raise SystemExit("invalid checkpoint digest in continuity record")
    previous = {"algorithm": "sha256", "digest": current_checkpoint["digest"]}
if records[0].get("checkpoint_digest") != cd:
    raise SystemExit("continuity genesis checkpoint mismatch")
if continuity.get("continuity_assertion") != "STRICT_MONOTONIC_CHECKPOINT_CHAIN" or continuity.get("publication_policy") != "explicit-public-only" or continuity.get("classification_boundary") != "PUBLIC_ONLY":
    raise SystemExit("continuity safety assertion mismatch")
flags = ("external_write_performed", "production_deploy_performed", "publication_performed", "destructive_action_performed", "secret_access_performed", "authorizes_deployment")
if any(continuity.get(k) is not False for k in flags):
    raise SystemExit("continuity cannot perform or authorize consequential action")
d = continuity.get("continuity_digest", {})
core = {k: v for k, v in continuity.items() if k != "continuity_digest"}
if d.get("algorithm") != "sha256" or d.get("digest") != digest(core):
    raise SystemExit("continuity digest mismatch")
print(f"public release custody checkpoint continuity validation PASS: source={source[:12]}; checkpoints={len(records)}; deployment_authorized=false")
