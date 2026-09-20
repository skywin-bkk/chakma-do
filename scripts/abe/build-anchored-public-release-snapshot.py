#!/usr/bin/env python3
import hashlib, json, re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
ANCHOR=ROOT/"build/abe/public-release-checkpoint-history-anchor.json"
BUNDLE=ROOT/"build/abe/public-release-bundle.json"
READINESS=ROOT/"build/abe/public-release-readiness.json"
GATE=ROOT/"build/abe/public-release-gate.json"
OUT=ROOT/"build/abe/anchored-public-release-snapshot.json"
def digest(v): return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode()).hexdigest()
def load(p): return json.loads(p.read_text(encoding="utf-8"))
a,b,r,g=map(load,(ANCHOR,BUNDLE,READINESS,GATE))
if a.get("schema_version")!=1 or a.get("stage")!="ABE-026" or a.get("anchor_state")!="PASS_REPOSITORY_LOCAL_ONLY": raise SystemExit("ABE-027 requires validated ABE-026 anchor")
if a.get("publication_policy")!="explicit-public-only" or a.get("classification_boundary")!="PUBLIC_ONLY": raise SystemExit("non-PUBLIC anchor rejected")
flags=("external_write_performed","production_deploy_performed","publication_performed","destructive_action_performed","secret_access_performed","authorizes_deployment")
if any(a.get(k) is not False for k in flags): raise SystemExit("consequential anchor rejected")
ad=a.get("anchor_digest",{}); ac={k:v for k,v in a.items() if k!="anchor_digest"}
if ad.get("algorithm")!="sha256" or ad.get("digest")!=digest(ac): raise SystemExit("anchor digest mismatch")
source=b.get("source_commit","")
if not re.fullmatch(r"[0-9a-f]{40}",source): raise SystemExit("invalid release source")
for x,state,key in ((b,"REPOSITORY_LOCAL_ONLY","release_state"),(r,"READY_REPOSITORY_LOCAL_ONLY","attestation_state"),(g,"PASS_REPOSITORY_LOCAL_ONLY","gate_state")):
    if x.get("schema_version")!=1 or x.get(key)!=state or x.get("source_commit")!=source: raise SystemExit("release evidence identity mismatch")
    if x.get("publication_policy")!="explicit-public-only" or x.get("classification_boundary")!="PUBLIC_ONLY": raise SystemExit("non-PUBLIC release evidence rejected")
    if x.get("external_write_performed") is not False or x.get("production_deploy_performed") is not False: raise SystemExit("consequential release evidence rejected")
bi=b.get("bundle_integrity",{})
if bi.get("algorithm")!="sha256" or not re.fullmatch(r"[0-9a-f]{64}",bi.get("digest","")): raise SystemExit("invalid bundle digest")
if r.get("bundle_integrity")!=bi or g.get("bundle_integrity")!=bi: raise SystemExit("release digest chain mismatch")
entries=b.get("entries")
if not isinstance(entries,list) or any(not isinstance(x,dict) or x.get("classification")!="PUBLIC" for x in entries): raise SystemExit("non-PUBLIC bundle entry rejected")
core={"schema_version":1,"stage":"ABE-027","snapshot_state":"PASS_REPOSITORY_LOCAL_ONLY","anchor_identity":ad,"anchor_source_commit":a.get("source_commit"),"release_source_commit":source,"bundle_integrity":bi,"entry_count":len(entries),"readiness_state":r["attestation_state"],"gate_state":g["gate_state"],"publication_policy":"explicit-public-only","classification_boundary":"PUBLIC_ONLY","external_write_performed":False,"production_deploy_performed":False,"publication_performed":False,"destructive_action_performed":False,"secret_access_performed":False,"authorizes_deployment":False}
out=dict(core); out["snapshot_digest"]={"algorithm":"sha256","digest":digest(core)}
OUT.parent.mkdir(parents=True,exist_ok=True); OUT.write_text(json.dumps(out,indent=2)+"\n",encoding="utf-8")
print(f"ABE-027 anchored snapshot PASS: release={source[:12]}; deployment_authorized=false")
