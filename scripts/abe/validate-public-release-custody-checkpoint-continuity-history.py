#!/usr/bin/env python3
import hashlib, json, re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
QUEUE=ROOT/"config/abe/task-queue.json"; SOURCE=ROOT/"build/abe/public-release-custody-checkpoint-continuity.json"; HISTORY=ROOT/"build/abe/public-release-custody-checkpoint-continuity-history.json"
def digest(v): return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode()).hexdigest()
q=json.loads(QUEUE.read_text()); c=json.loads(SOURCE.read_text()); h=json.loads(HISTORY.read_text())
if q.get("authoritative_department_scope") != ["DO-DEP-01","DO-DEP-14"] or q.get("verified_baseline") != "DO-DEP-04": raise SystemExit("scope/baseline changed")
r=q.get("rules",{}); flags=("external_writes","production_deploy","destructive_actions")
if r.get("public_exposure") != "explicit-public-only" or any(r.get(k) is not False for k in flags): raise SystemExit("safety gate changed")
if c.get("stage") != "ABE-024" or c.get("continuity_state") != "PASS_REPOSITORY_LOCAL_ONLY": raise SystemExit("invalid ABE-024 continuity")
source=c.get("source_commit","")
if not re.fullmatch(r"[0-9a-f]{40}",source): raise SystemExit("invalid source")
cc={k:v for k,v in c.items() if k!="continuity_digest"}; cd=c.get("continuity_digest",{})
if cd.get("algorithm")!="sha256" or cd.get("digest")!=digest(cc): raise SystemExit("continuity digest mismatch")
if h.get("schema_version")!=1 or h.get("stage")!="ABE-025" or h.get("history_state")!="PASS_REPOSITORY_LOCAL_ONLY": raise SystemExit("invalid ABE-025 history")
if h.get("source_commit")!=source or h.get("custody_history_identity")!=c.get("history_identity") or h.get("checkpoint_continuity_identity")!=cd: raise SystemExit("stale/mismatched identity")
records=h.get("records");
if not isinstance(records,list) or not records or h.get("record_count")!=len(records): raise SystemExit("invalid history length")
previous=None
for i,rec in enumerate(records):
    if rec.get("history_sequence")!=i: raise SystemExit("rollback/fork/gap/reorder/duplication detected")
    if rec.get("source_commit")!=source or rec.get("custody_history_identity")!=c.get("history_identity"): raise SystemExit("history identity mismatch")
    if rec.get("predecessor_continuity_digest")!=previous: raise SystemExit("predecessor continuity digest mismatch")
    if rec.get("publication_policy")!="explicit-public-only" or rec.get("classification_boundary")!="PUBLIC_ONLY": raise SystemExit("non-PUBLIC history rejected")
    rd=rec.get("history_record_digest",{}); rc={k:v for k,v in rec.items() if k!="history_record_digest"}
    if rd.get("algorithm")!="sha256" or rd.get("digest")!=digest(rc): raise SystemExit("history record digest mismatch")
    ident=rec.get("checkpoint_continuity_identity",{})
    if ident.get("algorithm")!="sha256" or not re.fullmatch(r"[0-9a-f]{64}",ident.get("digest","")): raise SystemExit("invalid continuity identity")
    previous=ident
if records[0].get("checkpoint_continuity_identity")!=cd: raise SystemExit("genesis continuity mismatch")
if h.get("history_assertion")!="APPEND_ONLY_STRICT_MONOTONIC_CONTINUITY_HISTORY" or h.get("publication_policy")!="explicit-public-only" or h.get("classification_boundary")!="PUBLIC_ONLY": raise SystemExit("history assertion mismatch")
action_flags=("external_write_performed","production_deploy_performed","publication_performed","destructive_action_performed","secret_access_performed","authorizes_deployment")
if any(h.get(k) is not False for k in action_flags): raise SystemExit("history cannot authorize consequential action")
hd=h.get("history_digest",{}); hc={k:v for k,v in h.items() if k!="history_digest"}
if hd.get("algorithm")!="sha256" or hd.get("digest")!=digest(hc): raise SystemExit("history digest mismatch")
print(f"ABE-025 checkpoint continuity history validation PASS: source={source[:12]}; records={len(records)}; deployment_authorized=false")
