#!/usr/bin/env python3
import hashlib, json, re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
QUEUE=ROOT/"config/abe/task-queue.json"; SNAP=ROOT/"build/abe/anchored-public-release-snapshot.json"; CONT=ROOT/"build/abe/anchored-public-release-snapshot-continuity.json"
def digest(v): return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode()).hexdigest()
def load(p): return json.loads(p.read_text(encoding="utf-8"))
q,s,c=map(load,(QUEUE,SNAP,CONT))
if q.get("authoritative_department_scope")!=["DO-DEP-01","DO-DEP-14"] or q.get("verified_baseline")!="DO-DEP-04": raise SystemExit("scope/baseline drift")
if q.get("rules")!={"public_exposure":"explicit-public-only","external_writes":False,"production_deploy":False,"destructive_actions":False}: raise SystemExit("safety rules drift")
if not any(t.get("id")=="ABE-028" and t.get("status")=="READY" and t.get("safe_autonomous") is True for t in q.get("queue",[])): raise SystemExit("ABE-028 not authoritative READY")
if s.get("stage")!="ABE-027" or s.get("snapshot_state")!="PASS_REPOSITORY_LOCAL_ONLY": raise SystemExit("invalid current snapshot")
sd=s.get("snapshot_digest",{}); sc={k:v for k,v in s.items() if k!="snapshot_digest"}
if sd.get("algorithm")!="sha256" or sd.get("digest")!=digest(sc): raise SystemExit("current snapshot digest mismatch")
if c.get("schema_version")!=1 or c.get("stage")!="ABE-028" or c.get("continuity_state")!="PASS_REPOSITORY_LOCAL_ONLY": raise SystemExit("invalid continuity evidence")
if c.get("current_snapshot_identity")!=sd or c.get("current_release_source_commit")!=s.get("release_source_commit"): raise SystemExit("current snapshot substitution rejected")
if c.get("predecessor_state")!="GENESIS" or c.get("predecessor_snapshot_identity") is not None: raise SystemExit("unvalidated predecessor linkage rejected")
if c.get("publication_policy")!="explicit-public-only" or c.get("classification_boundary")!="PUBLIC_ONLY": raise SystemExit("non-PUBLIC continuity rejected")
flags=("external_write_performed","production_deploy_performed","publication_performed","destructive_action_performed","secret_access_performed","authorizes_deployment")
if any(c.get(k) is not False for k in flags): raise SystemExit("consequential continuity rejected")
cd=c.get("continuity_digest",{}); cc={k:v for k,v in c.items() if k!="continuity_digest"}
if cd.get("algorithm")!="sha256" or not re.fullmatch(r"[0-9a-f]{64}",cd.get("digest","")) or cd.get("digest")!=digest(cc): raise SystemExit("continuity digest mismatch")
print("ABE-028 continuity validation PASS: genesis=true; deployment_authorized=false")
