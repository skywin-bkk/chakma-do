#!/usr/bin/env python3
import hashlib, json, re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
SNAP=ROOT/"build/abe/anchored-public-release-snapshot.json"
OUT=ROOT/"build/abe/anchored-public-release-snapshot-continuity.json"
def digest(v): return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode()).hexdigest()
def load(p): return json.loads(p.read_text(encoding="utf-8"))
s=load(SNAP)
if s.get("schema_version")!=1 or s.get("stage")!="ABE-027" or s.get("snapshot_state")!="PASS_REPOSITORY_LOCAL_ONLY": raise SystemExit("ABE-028 requires validated ABE-027 snapshot")
if s.get("publication_policy")!="explicit-public-only" or s.get("classification_boundary")!="PUBLIC_ONLY": raise SystemExit("non-PUBLIC snapshot rejected")
flags=("external_write_performed","production_deploy_performed","publication_performed","destructive_action_performed","secret_access_performed","authorizes_deployment")
if any(s.get(k) is not False for k in flags): raise SystemExit("consequential snapshot rejected")
sd=s.get("snapshot_digest",{}); sc={k:v for k,v in s.items() if k!="snapshot_digest"}
if sd.get("algorithm")!="sha256" or not re.fullmatch(r"[0-9a-f]{64}",sd.get("digest","")) or sd.get("digest")!=digest(sc): raise SystemExit("snapshot digest mismatch")
source=s.get("release_source_commit","")
if not re.fullmatch(r"[0-9a-f]{40}",source): raise SystemExit("invalid release source")
# ABE-028 starts with an explicit deterministic genesis continuity record. A future validated
# snapshot may extend this chain by supplying the exact predecessor identity/digest.
core={"schema_version":1,"stage":"ABE-028","continuity_state":"PASS_REPOSITORY_LOCAL_ONLY","current_snapshot_identity":sd,"current_release_source_commit":source,"predecessor_state":"GENESIS","predecessor_snapshot_identity":None,"publication_policy":"explicit-public-only","classification_boundary":"PUBLIC_ONLY","external_write_performed":False,"production_deploy_performed":False,"publication_performed":False,"destructive_action_performed":False,"secret_access_performed":False,"authorizes_deployment":False}
out=dict(core); out["continuity_digest"]={"algorithm":"sha256","digest":digest(core)}
OUT.parent.mkdir(parents=True,exist_ok=True); OUT.write_text(json.dumps(out,indent=2)+"\n",encoding="utf-8")
print(f"ABE-028 snapshot continuity PASS: state=GENESIS; release={source[:12]}; deployment_authorized=false")
