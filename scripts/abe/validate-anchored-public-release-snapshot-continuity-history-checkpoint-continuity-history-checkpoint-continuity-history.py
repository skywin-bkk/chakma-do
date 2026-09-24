#!/usr/bin/env python3
import hashlib, json, re
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
QUEUE = ROOT / "config/abe/task-queue.json"
CURRENT = ROOT / "build/abe/anchored-public-release-snapshot-continuity-history-checkpoint-continuity-history-checkpoint-continuity.json"
PREDECESSOR = ROOT / "build/abe/anchored-public-release-snapshot-continuity-history-checkpoint-continuity-history-checkpoint-continuity-history.previous.json"
EVIDENCE = ROOT / "build/abe/anchored-public-release-snapshot-continuity-history-checkpoint-continuity-history-checkpoint-continuity-history.json"
FLAGS=("external_write_performed","production_deploy_performed","publication_performed","destructive_action_performed","secret_access_performed","authorizes_deployment")
def digest(v): return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode()).hexdigest()
def identity(v,label):
    if not isinstance(v,dict) or v.get("algorithm")!="sha256" or not re.fullmatch(r"[0-9a-f]{64}",v.get("digest","")): raise SystemExit(f"invalid {label}")
    return v
def positive(v,label):
    if not isinstance(v,int) or isinstance(v,bool) or v<1: raise SystemExit(f"invalid {label}")
    return v
def safe(v,label):
    if v.get("publication_policy")!="explicit-public-only" or v.get("classification_boundary")!="PUBLIC_ONLY": raise SystemExit(f"unsafe/non-PUBLIC {label}")
    if any(v.get(k) is not False for k in FLAGS): raise SystemExit(f"consequential authority rejected: {label}")
q=json.loads(QUEUE.read_text(encoding="utf-8"))
if q.get("authoritative_department_scope") != ["DO-DEP-01","DO-DEP-14"] or q.get("verified_baseline")!="DO-DEP-04": raise SystemExit("scope/baseline changed")
if q.get("rules") != {"public_exposure":"explicit-public-only","external_writes":False,"production_deploy":False,"destructive_actions":False}: raise SystemExit("safety gate changed")
tasks=[x for x in q.get("queue",[]) if x.get("id")=="ABE-038"]
if len(tasks)!=1 or tasks[0].get("status") not in {"READY","COMPLETE_FOUNDATION"} or tasks[0].get("safe_autonomous") is not True: raise SystemExit("ABE-038 not authoritative READY or COMPLETE_FOUNDATION")
current=json.loads(CURRENT.read_text(encoding="utf-8"))
if current.get("schema_version")!=1 or current.get("stage")!="ABE-037" or current.get("continuity_state") not in {"GENESIS","LINKED"}: raise SystemExit("invalid ABE-037 continuity evidence")
safe(current,"ABE-037 continuity")
cid=identity(current.get("continuity_digest"),"ABE-037 continuity identity")
if cid["digest"]!=digest({k:v for k,v in current.items() if k!="continuity_digest"}): raise SystemExit("ABE-037 continuity digest mismatch")
seq=positive(current.get("continuity_sequence"),"ABE-037 continuity sequence")
expected_seq,expected_state,expected_pred=1,"GENESIS",None
if PREDECESSOR.exists():
    p=json.loads(PREDECESSOR.read_text(encoding="utf-8"))
    if p.get("schema_version")!=1 or p.get("stage")!="ABE-038" or p.get("history_state") not in {"GENESIS","LINKED"}: raise SystemExit("invalid predecessor ABE-038 history")
    safe(p,"ABE-038 predecessor"); pid=identity(p.get("history_digest"),"predecessor history identity")
    if pid["digest"]!=digest({k:v for k,v in p.items() if k!="history_digest"}): raise SystemExit("predecessor history digest mismatch")
    pseq=positive(p.get("history_sequence"),"predecessor history sequence")
    if p.get("current_continuity_identity")==cid: raise SystemExit("duplicate/self-reference history rejected")
    expected_seq,expected_state,expected_pred=pseq+1,"LINKED",pid
e=json.loads(EVIDENCE.read_text(encoding="utf-8"))
if e.get("schema_version")!=1 or e.get("stage")!="ABE-038" or e.get("history_state")!=expected_state: raise SystemExit("invalid ABE-038 history state")
safe(e,"ABE-038 evidence")
expected={"history_sequence":expected_seq,"current_continuity_sequence":seq,"current_continuity_identity":cid,"current_checkpoint_identity":current.get("current_checkpoint_identity"),"terminal_abe035_history_sequence":current.get("terminal_history_sequence"),"terminal_abe035_history_identity":current.get("terminal_history_identity"),"current_abe034_continuity_sequence":current.get("current_abe034_continuity_sequence"),"current_abe034_continuity_identity":current.get("current_abe034_continuity_identity"),"terminal_abe032_history_sequence":current.get("terminal_abe032_history_sequence"),"terminal_abe032_history_identity":current.get("terminal_abe032_history_identity"),"current_anchor_continuity_identity":current.get("current_anchor_continuity_identity"),"current_anchor_identity":current.get("current_anchor_identity"),"predecessor_history_identity":expected_pred,"current_release_source_commit":current.get("current_release_source_commit")}
for k,v in expected.items():
    if e.get(k)!=v: raise SystemExit(f"ABE-038 history linkage mismatch: {k}")
for k in ("current_continuity_identity","current_checkpoint_identity","terminal_abe035_history_identity","current_abe034_continuity_identity","terminal_abe032_history_identity","current_anchor_continuity_identity","current_anchor_identity"): identity(e.get(k),k)
for k in ("terminal_abe035_history_sequence","current_abe034_continuity_sequence","terminal_abe032_history_sequence"): positive(e.get(k),k)
eid=identity(e.get("history_digest"),"ABE-038 history identity")
if eid["digest"]!=digest({k:v for k,v in e.items() if k!="history_digest"}): raise SystemExit("ABE-038 history digest mismatch")
print(f"ABE-038 checkpoint continuity history validation PASS: state={expected_state}; sequence={expected_seq}; deployment_authorized=false")
