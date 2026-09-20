#!/usr/bin/env python3
import hashlib, json, re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "build/abe/anchored-public-release-snapshot-continuity.json"
OUT = ROOT / "build/abe/anchored-public-release-snapshot-continuity-history.json"

def digest(value):
    raw=json.dumps(value,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode()
    return hashlib.sha256(raw).hexdigest()

def valid_identity(value):
    return isinstance(value,dict) and value.get("algorithm")=="sha256" and re.fullmatch(r"[0-9a-f]{64}",value.get("digest", ""))

c=json.loads(SOURCE.read_text(encoding="utf-8"))
if c.get("schema_version")!=1 or c.get("stage")!="ABE-028" or c.get("continuity_state")!="PASS_REPOSITORY_LOCAL_ONLY": raise SystemExit("ABE-029 requires validated ABE-028 continuity")
if c.get("publication_policy")!="explicit-public-only" or c.get("classification_boundary")!="PUBLIC_ONLY": raise SystemExit("non-PUBLIC continuity rejected")
flags=("external_write_performed","production_deploy_performed","publication_performed","destructive_action_performed","secret_access_performed","authorizes_deployment")
if any(c.get(k) is not False for k in flags): raise SystemExit("consequential continuity rejected")
cd=c.get("continuity_digest",{}); cc={k:v for k,v in c.items() if k!="continuity_digest"}
if not valid_identity(cd) or cd["digest"]!=digest(cc): raise SystemExit("continuity digest mismatch")
sid=c.get("current_snapshot_identity",{})
if not valid_identity(sid): raise SystemExit("invalid current snapshot identity")
source=c.get("current_release_source_commit","")
if not re.fullmatch(r"[0-9a-f]{40}",source): raise SystemExit("invalid release source")
record_core={"history_sequence":0,"snapshot_continuity_identity":cd,"current_snapshot_identity":sid,"current_release_source_commit":source,"predecessor_history_record_digest":None,"publication_policy":"explicit-public-only","classification_boundary":"PUBLIC_ONLY"}
record=dict(record_core); record["history_record_digest"]={"algorithm":"sha256","digest":digest(record_core)}
history_core={"schema_version":1,"stage":"ABE-029","history_state":"PASS_REPOSITORY_LOCAL_ONLY","history_origin":"GENESIS","record_count":1,"records":[record],"history_assertion":"APPEND_ONLY_STRICT_MONOTONIC_SNAPSHOT_CONTINUITY_HISTORY","publication_policy":"explicit-public-only","classification_boundary":"PUBLIC_ONLY","external_write_performed":False,"production_deploy_performed":False,"publication_performed":False,"destructive_action_performed":False,"secret_access_performed":False,"authorizes_deployment":False}
out=dict(history_core); out["history_digest"]={"algorithm":"sha256","digest":digest(history_core)}
OUT.parent.mkdir(parents=True,exist_ok=True); OUT.write_text(json.dumps(out,indent=2)+"\n",encoding="utf-8")
print(f"ABE-029 snapshot continuity history PASS: origin=GENESIS; records=1; release={source[:12]}; deployment_authorized=false")
