#!/usr/bin/env python3
import hashlib,json,re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
QUEUE=ROOT/"config/abe/task-queue.json"; HISTORY=ROOT/"build/abe/public-release-custody-checkpoint-continuity-history.json"; ANCHOR=ROOT/"build/abe/public-release-checkpoint-history-anchor.json"
def digest(v): return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode()).hexdigest()
q=json.loads(QUEUE.read_text()); h=json.loads(HISTORY.read_text()); a=json.loads(ANCHOR.read_text())
if q.get("authoritative_department_scope") != ["DO-DEP-01","DO-DEP-14"] or q.get("verified_baseline")!="DO-DEP-04": raise SystemExit("scope/baseline changed")
r=q.get("rules",{}); 
if r.get("public_exposure")!="explicit-public-only" or any(r.get(k) is not False for k in ("external_writes","production_deploy","destructive_actions")): raise SystemExit("safety gate changed")
if h.get("stage")!="ABE-025" or h.get("history_state")!="PASS_REPOSITORY_LOCAL_ONLY": raise SystemExit("invalid ABE-025 history")
hd=h.get("history_digest",{}); hc={k:v for k,v in h.items() if k!="history_digest"}
if hd.get("algorithm")!="sha256" or hd.get("digest")!=digest(hc): raise SystemExit("history digest mismatch")
records=h.get("records");
if not isinstance(records,list) or not records or h.get("record_count")!=len(records): raise SystemExit("invalid history length")
for i,rec in enumerate(records):
    if rec.get("history_sequence")!=i: raise SystemExit("rollback/fork/gap/reorder detected")
    rd=rec.get("history_record_digest",{}); rc={k:v for k,v in rec.items() if k!="history_record_digest"}
    if rd.get("algorithm")!="sha256" or rd.get("digest")!=digest(rc): raise SystemExit("history mutation detected")
terminal=records[-1]; rd=terminal["history_record_digest"]; cd=terminal.get("checkpoint_continuity_identity",{})
if a.get("schema_version")!=1 or a.get("stage")!="ABE-026" or a.get("anchor_state")!="PASS_REPOSITORY_LOCAL_ONLY": raise SystemExit("invalid ABE-026 anchor")
if a.get("source_commit")!=h.get("source_commit") or a.get("history_identity")!=hd: raise SystemExit("stale history identity")
if a.get("terminal_sequence")!=len(records)-1 or a.get("terminal_entry_digest")!=rd or a.get("terminal_continuity_digest")!=cd: raise SystemExit("non-terminal/stale anchor")
if a.get("publication_policy")!="explicit-public-only" or a.get("classification_boundary")!="PUBLIC_ONLY": raise SystemExit("non-PUBLIC anchor rejected")
flags=("external_write_performed","production_deploy_performed","publication_performed","destructive_action_performed","secret_access_performed","authorizes_deployment")
if any(a.get(k) is not False for k in flags): raise SystemExit("anchor cannot authorize consequential action")
ad=a.get("anchor_digest",{}); ac={k:v for k,v in a.items() if k!="anchor_digest"}
if ad.get("algorithm")!="sha256" or ad.get("digest")!=digest(ac): raise SystemExit("anchor digest mismatch")
print(f"ABE-026 checkpoint history anchor validation PASS: source={a['source_commit'][:12]}; terminal={a['terminal_sequence']}; deployment_authorized=false")
