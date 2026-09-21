#!/usr/bin/env python3
import hashlib, json, re
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
QUEUE=ROOT/"config/abe/task-queue.json"
HISTORY=ROOT/"build/abe/anchored-public-release-snapshot-continuity-history.json"
ANCHOR=ROOT/"build/abe/anchored-public-release-snapshot-continuity-history-anchor.json"

def digest(v): return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode()).hexdigest()
def valid_identity(v): return isinstance(v,dict) and v.get("algorithm")=="sha256" and re.fullmatch(r"[0-9a-f]{64}",v.get("digest", ""))

q=json.loads(QUEUE.read_text(encoding="utf-8")); h=json.loads(HISTORY.read_text(encoding="utf-8")); a=json.loads(ANCHOR.read_text(encoding="utf-8"))
if q.get("authoritative_department_scope") != ["DO-DEP-01","DO-DEP-14"] or q.get("verified_baseline") != "DO-DEP-04": raise SystemExit("scope/baseline changed")
if q.get("rules") != {"public_exposure":"explicit-public-only","external_writes":False,"production_deploy":False,"destructive_actions":False}: raise SystemExit("safety gate changed")
task=next((x for x in q.get("queue",[]) if x.get("id")=="ABE-030"),None)
# ABE-030 evidence remains independently verifiable after its reviewed,
# validated READY -> COMPLETE_FOUNDATION transition. No other status is valid.
if not task or task.get("status") not in {"READY","COMPLETE_FOUNDATION"} or task.get("safe_autonomous") is not True: raise SystemExit("ABE-030 not in an authoritative verifiable state")
flags=("external_write_performed","production_deploy_performed","publication_performed","destructive_action_performed","secret_access_performed","authorizes_deployment")
if h.get("schema_version")!=1 or h.get("stage")!="ABE-029" or h.get("history_state")!="PASS_REPOSITORY_LOCAL_ONLY": raise SystemExit("invalid ABE-029 history")
if h.get("publication_policy")!="explicit-public-only" or h.get("classification_boundary")!="PUBLIC_ONLY" or any(h.get(k) is not False for k in flags): raise SystemExit("unsafe history")
hd=h.get("history_digest",{}); hc={k:v for k,v in h.items() if k!="history_digest"}
if not valid_identity(hd) or hd["digest"]!=digest(hc): raise SystemExit("history digest mismatch")
records=h.get("records")
if not isinstance(records,list) or not records or h.get("record_count")!=len(records): raise SystemExit("invalid history length")
previous=None
for i,rec in enumerate(records):
    if rec.get("history_sequence")!=i or rec.get("predecessor_history_record_digest")!=previous: raise SystemExit("rollback/fork/gap/reorder/duplication detected")
    if rec.get("publication_policy")!="explicit-public-only" or rec.get("classification_boundary")!="PUBLIC_ONLY": raise SystemExit("non-PUBLIC record rejected")
    rd=rec.get("history_record_digest",{}); rc={k:v for k,v in rec.items() if k!="history_record_digest"}
    if not valid_identity(rd) or rd["digest"]!=digest(rc): raise SystemExit("record mutation/digest mismatch")
    previous=rd
terminal=records[-1]
if a.get("schema_version")!=1 or a.get("stage")!="ABE-030" or a.get("anchor_state")!="PASS_REPOSITORY_LOCAL_ONLY": raise SystemExit("invalid ABE-030 anchor")
expected={"terminal_history_sequence":terminal.get("history_sequence"),"terminal_history_record_identity":terminal.get("history_record_digest"),"history_identity":hd,"snapshot_continuity_identity":terminal.get("snapshot_continuity_identity"),"current_snapshot_identity":terminal.get("current_snapshot_identity"),"current_release_source_commit":terminal.get("current_release_source_commit")}
for k,v in expected.items():
    if a.get(k)!=v: raise SystemExit(f"terminal anchor mismatch: {k}")
for k in ("terminal_history_record_identity","history_identity","snapshot_continuity_identity","current_snapshot_identity"):
    if not valid_identity(a.get(k)): raise SystemExit(f"invalid anchor identity: {k}")
if a.get("publication_policy")!="explicit-public-only" or a.get("classification_boundary")!="PUBLIC_ONLY" or any(a.get(k) is not False for k in flags): raise SystemExit("anchor cannot authorize consequential action")
ad=a.get("anchor_digest",{}); ac={k:v for k,v in a.items() if k!="anchor_digest"}
if not valid_identity(ad) or ad["digest"]!=digest(ac): raise SystemExit("anchor digest mismatch")
print(f"ABE-030 terminal history anchor validation PASS: sequence={terminal['history_sequence']}; deployment_authorized=false")
