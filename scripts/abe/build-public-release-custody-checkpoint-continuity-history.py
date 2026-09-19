#!/usr/bin/env python3
import hashlib, json, re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "build/abe/public-release-custody-checkpoint-continuity.json"
OUT = ROOT / "build/abe/public-release-custody-checkpoint-continuity-history.json"

def digest(value):
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
    return hashlib.sha256(raw).hexdigest()

continuity = json.loads(SOURCE.read_text(encoding="utf-8"))
if continuity.get("schema_version") != 1 or continuity.get("stage") != "ABE-024" or continuity.get("continuity_state") != "PASS_REPOSITORY_LOCAL_ONLY":
    raise SystemExit("ABE-025 requires validated ABE-024 checkpoint continuity")
source = continuity.get("source_commit", "")
if not re.fullmatch(r"[0-9a-f]{40}", source): raise SystemExit("invalid source identity")
for field in ("history_identity", "continuity_digest"):
    value = continuity.get(field, {})
    if value.get("algorithm") != "sha256" or not re.fullmatch(r"[0-9a-f]{64}", value.get("digest", "")):
        raise SystemExit(f"invalid {field}")
core = {k:v for k,v in continuity.items() if k != "continuity_digest"}
if continuity["continuity_digest"]["digest"] != digest(core): raise SystemExit("continuity digest mismatch")
if continuity.get("publication_policy") != "explicit-public-only" or continuity.get("classification_boundary") != "PUBLIC_ONLY":
    raise SystemExit("non-PUBLIC continuity rejected")
flags=("external_write_performed","production_deploy_performed","publication_performed","destructive_action_performed","secret_access_performed","authorizes_deployment")
if any(continuity.get(k) is not False for k in flags): raise SystemExit("consequential action rejected")
record_core={"history_sequence":0,"source_commit":source,"custody_history_identity":continuity["history_identity"],"checkpoint_continuity_identity":continuity["continuity_digest"],"predecessor_continuity_digest":None,"publication_policy":"explicit-public-only","classification_boundary":"PUBLIC_ONLY"}
record=dict(record_core); record["history_record_digest"]={"algorithm":"sha256","digest":digest(record_core)}
history_core={"schema_version":1,"stage":"ABE-025","history_state":"PASS_REPOSITORY_LOCAL_ONLY","source_commit":source,"custody_history_identity":continuity["history_identity"],"checkpoint_continuity_identity":continuity["continuity_digest"],"record_count":1,"records":[record],"history_assertion":"APPEND_ONLY_STRICT_MONOTONIC_CONTINUITY_HISTORY","publication_policy":"explicit-public-only","classification_boundary":"PUBLIC_ONLY","external_write_performed":False,"production_deploy_performed":False,"publication_performed":False,"destructive_action_performed":False,"secret_access_performed":False,"authorizes_deployment":False}
out=dict(history_core); out["history_digest"]={"algorithm":"sha256","digest":digest(history_core)}
OUT.parent.mkdir(parents=True,exist_ok=True); OUT.write_text(json.dumps(out,indent=2)+"\n",encoding="utf-8")
print(f"ABE-025 checkpoint continuity history PASS: source={source[:12]}; records=1; deployment_authorized=false")
