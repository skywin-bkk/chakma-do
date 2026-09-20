#!/usr/bin/env python3
import hashlib, json, re
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
QUEUE=ROOT/"config/abe/task-queue.json"
SOURCE=ROOT/"build/abe/anchored-public-release-snapshot-continuity.json"
HISTORY=ROOT/"build/abe/anchored-public-release-snapshot-continuity-history.json"

def digest(v): return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode()).hexdigest()
def valid_identity(v): return isinstance(v,dict) and v.get("algorithm")=="sha256" and re.fullmatch(r"[0-9a-f]{64}",v.get("digest", ""))

q=json.loads(QUEUE.read_text(encoding="utf-8")); c=json.loads(SOURCE.read_text(encoding="utf-8")); h=json.loads(HISTORY.read_text(encoding="utf-8"))
if q.get("authoritative_department_scope") != ["DO-DEP-01","DO-DEP-14"] or q.get("verified_baseline") != "DO-DEP-04": raise SystemExit("scope/baseline changed")
r=q.get("rules",{})
if r != {"public_exposure":"explicit-public-only","external_writes":False,"production_deploy":False,"destructive_actions":False}: raise SystemExit("safety gate changed")
if c.get("schema_version")!=1 or c.get("stage")!="ABE-028" or c.get("continuity_state")!="PASS_REPOSITORY_LOCAL_ONLY": raise SystemExit("invalid ABE-028 continuity")
if c.get("publication_policy")!="explicit-public-only" or c.get("classification_boundary")!="PUBLIC_ONLY": raise SystemExit("non-PUBLIC continuity rejected")
action_flags=("external_write_performed","production_deploy_performed","publication_performed","destructive_action_performed","secret_access_performed","authorizes_deployment")
if any(c.get(k) is not False for k in action_flags): raise SystemExit("consequential continuity rejected")
cd=c.get("continuity_digest",{}); cc={k:v for k,v in c.items() if k!="continuity_digest"}
if not valid_identity(cd) or cd["digest"]!=digest(cc): raise SystemExit("continuity digest mismatch")
sid=c.get("current_snapshot_identity",{})
if not valid_identity(sid): raise SystemExit("invalid current snapshot identity")
source=c.get("current_release_source_commit","")
if not re.fullmatch(r"[0-9a-f]{40}",source): raise SystemExit("invalid release source")
if h.get("schema_version")!=1 or h.get("stage")!="ABE-029" or h.get("history_state")!="PASS_REPOSITORY_LOCAL_ONLY": raise SystemExit("invalid ABE-029 history")
records=h.get("records")
if not isinstance(records,list) or not records or h.get("record_count")!=len(records): raise SystemExit("invalid history length")
previous=None
for i,rec in enumerate(records):
    if rec.get("history_sequence")!=i: raise SystemExit("rollback/fork/gap/reorder/duplication detected")
    if rec.get("snapshot_continuity_identity")!=cd or rec.get("current_snapshot_identity")!=sid or rec.get("current_release_source_commit")!=source: raise SystemExit("stale/substituted continuity evidence")
    if rec.get("predecessor_history_record_digest")!=previous: raise SystemExit("predecessor history continuity mismatch")
    if rec.get("publication_policy")!="explicit-public-only" or rec.get("classification_boundary")!="PUBLIC_ONLY": raise SystemExit("non-PUBLIC history rejected")
    rd=rec.get("history_record_digest",{}); rc={k:v for k,v in rec.items() if k!="history_record_digest"}
    if not valid_identity(rd) or rd["digest"]!=digest(rc): raise SystemExit("history record digest mismatch")
    previous=rd
if h.get("history_origin")!="GENESIS" or records[0].get("predecessor_history_record_digest") is not None: raise SystemExit("invalid genesis history")
if h.get("history_assertion")!="APPEND_ONLY_STRICT_MONOTONIC_SNAPSHOT_CONTINUITY_HISTORY": raise SystemExit("history assertion mismatch")
if h.get("publication_policy")!="explicit-public-only" or h.get("classification_boundary")!="PUBLIC_ONLY": raise SystemExit("non-PUBLIC history rejected")
if any(h.get(k) is not False for k in action_flags): raise SystemExit("history cannot authorize consequential action")
hd=h.get("history_digest",{}); hc={k:v for k,v in h.items() if k!="history_digest"}
if not valid_identity(hd) or hd["digest"]!=digest(hc): raise SystemExit("history digest mismatch")
print(f"ABE-029 snapshot continuity history validation PASS: origin=GENESIS; records={len(records)}; release={source[:12]}; deployment_authorized=false")
