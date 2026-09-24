#!/usr/bin/env python3
"""Fail-closed repository-local replenishment for ABE-038.

Adds exactly one READY task after ABE-037. No external writes, deployment,
publication, destructive action, secret access, or non-PUBLIC exposure.
"""
import copy, json
from pathlib import Path

P=Path('config/abe/task-queue.json')
q=json.loads(P.read_text())
assert q['schema_version']==1
assert q['mode']=='controlled-autonomous'
assert q['authoritative_department_scope']==['DO-DEP-01','DO-DEP-14']
assert q['verified_baseline']=='DO-DEP-04'
assert q['rules']=={
 'public_exposure':'explicit-public-only',
 'external_writes':False,
 'production_deploy':False,
 'destructive_actions':False,
}
assert not any(t.get('id')=='ABE-038' for t in q['queue'])
assert q['queue'][-1]['id']=='ABE-037'
assert q['queue'][-1]['status']=='COMPLETE_FOUNDATION'

before=copy.deepcopy(q)
task={
 'id':'ABE-038',
 'title':'Checkpoint continuity history foundation',
 'status':'READY',
 'safe_autonomous':True,
 'acceptance':[
  'Accept only independently validated ABE-037 PUBLIC checkpoint-continuity evidence',
  'Emit deterministic repository-local append-only checkpoint-continuity history from identical validated inputs',
  'Bind every history entry to the exact ABE-037 continuity sequence and identity/digest, exact predecessor ABE-036 checkpoint identity/digest, terminal ABE-035 history identity/digest, current ABE-034 continuity identity/digest, terminal ABE-032 history identity/digest, ABE-031 anchor-continuity identity/digest, and current ABE-030 anchor identity/digest represented by validated ABE-037 evidence',
  'Require strictly monotonic history sequence numbers and exact predecessor-history continuity; permit only an explicit deterministic genesis history entry when no predecessor ABE-038 history exists',
  'Produce byte-identical history evidence from identical validated inputs using canonical serialization and SHA-256 identities',
  'Reject rollback, fork, gap, reorder, duplication, deletion, mutation, stale/substituted continuity evidence, predecessor-history mismatch, checkpoint mismatch, terminal-history mismatch, upstream identity/digest mismatch, non-PUBLIC evidence, scope/baseline drift, or consequential-action authority fail-closed',
  'Do not authorize or perform publication, production deployment, external writes, destructive actions, secret access, or INTERNAL/RESTRICTED exposure',
  'Preserve DO-DEP-01 through DO-DEP-14 authoritative scope and DO-DEP-04 verified baseline'
 ]
}
q['queue'].append(task)
assert q.keys()==before.keys()
assert q['schema_version']==before['schema_version']
assert q['mode']==before['mode']
assert q['authoritative_department_scope']==before['authoritative_department_scope']
assert q['verified_baseline']==before['verified_baseline']
assert q['rules']==before['rules']
assert q['queue'][:-1]==before['queue']
P.write_text(json.dumps(q,indent=2,ensure_ascii=False)+'\n')
print('PASS: bounded ABE-038 READY replenishment prepared')
