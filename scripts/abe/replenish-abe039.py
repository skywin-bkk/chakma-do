#!/usr/bin/env python3
"""Fail-closed repository-local replenishment for ABE-039.

Adds exactly one READY task after validated ABE-038 completion. No external
writes, deployment, publication, destructive action, secret access, or
non-PUBLIC exposure.
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
assert not any(t.get('id')=='ABE-039' for t in q['queue'])
assert q['queue'][-1]['id']=='ABE-038'
assert q['queue'][-1]['status']=='COMPLETE_FOUNDATION'

before=copy.deepcopy(q)
task={
 'id':'ABE-039',
 'title':'Checkpoint continuity history checkpoint foundation',
 'status':'READY',
 'safe_autonomous':True,
 'acceptance':[
  'Accept only independently validated PUBLIC ABE-038 checkpoint-continuity-history evidence',
  'Bind the exact terminal ABE-038 history sequence and identity/digest, current ABE-037 continuity sequence and identity/digest, predecessor ABE-036 checkpoint identity/digest, terminal ABE-035 history identity/digest, current ABE-034 continuity identity/digest, terminal ABE-032 history identity/digest, ABE-031 anchor-continuity identity/digest, and current ABE-030 anchor identity/digest into one deterministic repository-local checkpoint',
  'Produce byte-identical checkpoint evidence from identical validated inputs using canonical serialization and SHA-256 identities',
  'Require the checkpoint to represent the exact terminal validated ABE-038 history entry; reject stale or substituted history and any terminal-sequence mismatch',
  'Reject rollback, fork, gap, reorder, duplication, deletion, mutation, history-linkage mismatch, checkpoint-continuity mismatch, upstream identity/digest mismatch, non-PUBLIC evidence, scope/baseline drift, or consequential-action authority fail-closed',
  'Preserve DO-DEP-01 through DO-DEP-14 authoritative scope and DO-DEP-04 verified baseline',
  'Do not authorize or perform publication, production deployment, external writes, destructive actions, secret access, or INTERNAL/RESTRICTED exposure'
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
print('PASS: bounded ABE-039 READY replenishment prepared')
