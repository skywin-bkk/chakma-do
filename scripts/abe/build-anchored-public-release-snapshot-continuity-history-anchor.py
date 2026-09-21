#!/usr/bin/env python3
import hashlib, json, re
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
SOURCE=ROOT/"build/abe/anchored-public-release-snapshot-continuity-history.json"
OUT=ROOT/"build/abe/anchored-public-release-snapshot-continuity-history-anchor.json"

def digest(v): return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode()).hexdigest()
def valid_identity(v): return isinstance(v,dict) and v.get("algorithm")=="sha256" and re.fullmatch(r"[0-9a-f]{64}",v.get("digest", ""))

h=json.loads(SOURCE.read_text(encoding="utf-8"))
if h.get("schema_version")!=1 or h.get("stage")!="ABE-029" or h.get("history_state")!="PASS_REPOSITORY_LOCAL_ONLY": raise SystemExit("ABE-030 requires validated ABE-029 history")
if h.get("publication_policy")!="explicit-public-only" or h.get("classification_boundary")!="PUBLIC_ONLY": raise SystemExit("non-PUBLIC history rejected")
flags=("external_write_performed","production_deploy_performed","publication_performed","destructive_action_performed","secret_access_performed","authorizes_deployment")
if any(h.get(k) is not False for k in flags): raise SystemExit("consequential history rejected")
hd=h.get("history_digest",{}); hc={k:v for k,v in h.items() if k!="history_digest"}
if not valid_identity(hd) or hd["digest"]!=digest(hc): raise SystemExit("history digest mismatch")
records=h.get("records")
if not isinstance(records,list) or not records or h.get("record_count")!=len(records): raise SystemExit("invalid history length")
previous=None
for i,rec in enumerate(records):
    if rec.get("history_sequence")!=i or rec.get("predecessor_history_record_digest")!=previous: raise SystemExit("rollback/fork/gap/reorder/duplication detected")
    if rec.get("publication_policy")!="explicit-public-only" or rec.get("classification_boundary")!="PUBLIC_ONLY": raise SystemExit("non-PUBLIC record rejected")
    rd=rec.get("history_record_digest",{}); rc={k:v for k,v in rec.items() if k!="history_record_digest"}
    if not valid_identity(rd) or rd["digest"]!=digest(rc): raise SystemExit("history record digest mismatch")
    previous=rd
terminal=records[-1]
sci=terminal.get("snapshot_continuity_identity",{}); sid=terminal.get("current_snapshot_identity",{})
if not valid_identity(sci) or not valid_identity(sid): raise SystemExit("invalid terminal evidence identity")
core={"schema_version":1,"stage":"ABE-030","anchor_state":"PASS_REPOSITORY_LOCAL_ONLY","terminal_history_sequence":terminal["history_sequence"],"terminal_history_record_identity":terminal["history_record_digest"],"history_identity":hd,"snapshot_continuity_identity":sci,"current_snapshot_identity":sid,"current_release_source_commit":terminal.get("current_release_source_commit"),"publication_policy":"explicit-public-only","classification_boundary":"PUBLIC_ONLY","external_write_performed":False,"production_deploy_performed":False,"publication_performed":False,"destructive_action_performed":False,"secret_access_performed":False,"authorizes_deployment":False}
out=dict(core); out["anchor_digest"]={"algorithm":"sha256","digest":digest(core)}
OUT.parent.mkdir(parents=True,exist_ok=True); OUT.write_text(json.dumps(out,indent=2)+"\n",encoding="utf-8")
print(f"ABE-030 terminal history anchor PASS: sequence={terminal['history_sequence']}; deployment_authorized=false")
