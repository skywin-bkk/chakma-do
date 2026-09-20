#!/usr/bin/env python3
import hashlib,json,re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
QUEUE=ROOT/"config/abe/task-queue.json"; ANCHOR=ROOT/"build/abe/public-release-checkpoint-history-anchor.json"; BUNDLE=ROOT/"build/abe/public-release-bundle.json"; READINESS=ROOT/"build/abe/public-release-readiness.json"; GATE=ROOT/"build/abe/public-release-gate.json"; SNAP=ROOT/"build/abe/anchored-public-release-snapshot.json"
def digest(v): return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode()).hexdigest()
def load(p): return json.loads(p.read_text(encoding="utf-8"))
q,a,b,r,g,s=map(load,(QUEUE,ANCHOR,BUNDLE,READINESS,GATE,SNAP))
if q.get("authoritative_department_scope") != ["DO-DEP-01","DO-DEP-14"] or q.get("verified_baseline")!="DO-DEP-04": raise SystemExit("scope/baseline changed")
rules=q.get("rules",{})
if rules.get("public_exposure")!="explicit-public-only" or rules.get("external_writes") is not False or rules.get("production_deploy") is not False or rules.get("destructive_actions") is not False: raise SystemExit("authoritative safety rules changed")
if a.get("stage")!="ABE-026" or a.get("anchor_state")!="PASS_REPOSITORY_LOCAL_ONLY": raise SystemExit("invalid anchor state")
ad=a.get("anchor_digest",{}); ac={k:v for k,v in a.items() if k!="anchor_digest"}
if ad.get("algorithm")!="sha256" or ad.get("digest")!=digest(ac): raise SystemExit("anchor digest mismatch")
source=b.get("source_commit","")
if not re.fullmatch(r"[0-9a-f]{40}",source): raise SystemExit("invalid release source")
if r.get("source_commit")!=source or g.get("source_commit")!=source: raise SystemExit("release identity mismatch")
bi=b.get("bundle_integrity",{})
if bi.get("algorithm")!="sha256" or r.get("bundle_integrity")!=bi or g.get("bundle_integrity")!=bi: raise SystemExit("release digest chain mismatch")
entries=b.get("entries")
if not isinstance(entries,list) or any(not isinstance(x,dict) or x.get("classification")!="PUBLIC" for x in entries): raise SystemExit("non-PUBLIC release evidence")
for x in (a,b,r,g,s):
    if x.get("publication_policy")!="explicit-public-only" or x.get("classification_boundary")!="PUBLIC_ONLY": raise SystemExit("PUBLIC boundary mismatch")
    if x.get("external_write_performed") is not False or x.get("production_deploy_performed") is not False: raise SystemExit("consequential action evidence rejected")
if s.get("schema_version")!=1 or s.get("stage")!="ABE-027" or s.get("snapshot_state")!="PASS_REPOSITORY_LOCAL_ONLY": raise SystemExit("invalid snapshot state")
if s.get("anchor_identity")!=ad or s.get("anchor_source_commit")!=a.get("source_commit") or s.get("release_source_commit")!=source or s.get("bundle_integrity")!=bi or s.get("entry_count")!=len(entries) or s.get("readiness_state")!=r.get("attestation_state") or s.get("gate_state")!=g.get("gate_state"): raise SystemExit("snapshot binding mismatch")
for k in ("publication_performed","destructive_action_performed","secret_access_performed","authorizes_deployment"):
    if s.get(k) is not False: raise SystemExit("snapshot consequential authority rejected")
sd=s.get("snapshot_digest",{}); sc={k:v for k,v in s.items() if k!="snapshot_digest"}
if sd.get("algorithm")!="sha256" or sd.get("digest")!=digest(sc): raise SystemExit("snapshot digest mismatch")
print(f"ABE-027 snapshot validation PASS: release={source[:12]}; deployment_authorized=false")
