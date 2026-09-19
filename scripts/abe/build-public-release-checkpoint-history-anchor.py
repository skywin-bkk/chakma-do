#!/usr/bin/env python3
import hashlib, json, re
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
SOURCE=ROOT/"build/abe/public-release-custody-checkpoint-continuity-history.json"
OUT=ROOT/"build/abe/public-release-checkpoint-history-anchor.json"

def digest(v): return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode()).hexdigest()

h=json.loads(SOURCE.read_text(encoding="utf-8"))
if h.get("schema_version")!=1 or h.get("stage")!="ABE-025" or h.get("history_state")!="PASS_REPOSITORY_LOCAL_ONLY": raise SystemExit("ABE-026 requires validated ABE-025 history")
source=h.get("source_commit","")
if not re.fullmatch(r"[0-9a-f]{40}",source): raise SystemExit("invalid source identity")
if h.get("publication_policy")!="explicit-public-only" or h.get("classification_boundary")!="PUBLIC_ONLY": raise SystemExit("non-PUBLIC history rejected")
flags=("external_write_performed","production_deploy_performed","publication_performed","destructive_action_performed","secret_access_performed","authorizes_deployment")
if any(h.get(k) is not False for k in flags): raise SystemExit("consequential action rejected")
hd=h.get("history_digest",{}); hc={k:v for k,v in h.items() if k!="history_digest"}
if hd.get("algorithm")!="sha256" or hd.get("digest")!=digest(hc): raise SystemExit("history digest mismatch")
records=h.get("records")
if not isinstance(records,list) or not records or h.get("record_count")!=len(records): raise SystemExit("invalid history length")
terminal=records[-1]
if terminal.get("history_sequence")!=len(records)-1: raise SystemExit("non-terminal history selection")
rd=terminal.get("history_record_digest",{}); rc={k:v for k,v in terminal.items() if k!="history_record_digest"}
if rd.get("algorithm")!="sha256" or rd.get("digest")!=digest(rc): raise SystemExit("terminal record digest mismatch")
continuity=terminal.get("checkpoint_continuity_identity",{})
if continuity.get("algorithm")!="sha256" or not re.fullmatch(r"[0-9a-f]{64}",continuity.get("digest","")): raise SystemExit("invalid terminal continuity digest")
core={"schema_version":1,"stage":"ABE-026","anchor_state":"PASS_REPOSITORY_LOCAL_ONLY","source_commit":source,"history_identity":hd,"terminal_sequence":terminal["history_sequence"],"terminal_entry_digest":rd,"terminal_continuity_digest":continuity,"publication_policy":"explicit-public-only","classification_boundary":"PUBLIC_ONLY","external_write_performed":False,"production_deploy_performed":False,"publication_performed":False,"destructive_action_performed":False,"secret_access_performed":False,"authorizes_deployment":False}
out=dict(core); out["anchor_digest"]={"algorithm":"sha256","digest":digest(core)}
OUT.parent.mkdir(parents=True,exist_ok=True); OUT.write_text(json.dumps(out,indent=2)+"\n",encoding="utf-8")
print(f"ABE-026 checkpoint history anchor PASS: source={source[:12]}; terminal={terminal['history_sequence']}; deployment_authorized=false")
