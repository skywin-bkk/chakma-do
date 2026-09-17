#!/usr/bin/env python3
import json
from pathlib import Path

QUEUE = Path('config/abe/task-queue.json')
OUT = Path('build/abe/queue-replenishment-state.json')

q = json.loads(QUEUE.read_text())
assert q['authoritative_department_scope'] == ['DO-DEP-01', 'DO-DEP-14']
assert q['verified_baseline'] == 'DO-DEP-04'
assert q['rules']['public_exposure'] == 'explicit-public-only'
assert all(q['rules'][k] is False for k in ('external_writes','production_deploy','destructive_actions'))

tasks = q['queue']
ids = [t.get('id') for t in tasks]
assert all(isinstance(x, str) and x.startswith('ABE-') for x in ids)
assert len(ids) == len(set(ids)), 'duplicate task IDs are forbidden'

ready = [t for t in tasks if t.get('status') == 'READY']
for task in ready:
    assert task.get('safe_autonomous') is True, f"READY task {task['id']} must be safe_autonomous"
    acceptance = task.get('acceptance')
    assert isinstance(acceptance, list) and acceptance, f"READY task {task['id']} needs repository-local acceptance criteria"
    joined = ' '.join(str(x).lower() for x in acceptance)
    forbidden = ('production deploy', 'destructive external', 'external write', 'secret access')
    assert not any(term in joined and ('false' not in joined and 'preserve' not in joined and 'reject' not in joined and 'never' not in joined) for term in forbidden)

status = 'READY_TASK_AVAILABLE' if ready else 'SAFE_IDLE'
state = {
    'schema_version': 1,
    'status': status,
    'ready_task_ids': [t['id'] for t in ready],
    'idle': not ready,
    'replenishment_policy': 'REVIEWED_REPOSITORY_CHANGE_ONLY',
    'authoritative_mutation_performed': False,
    'scope_expansion_allowed': False,
    'authoritative_department_scope': q['authoritative_department_scope'],
    'verified_baseline': q['verified_baseline'],
    'external_writes': False,
    'production_deploy': False,
    'destructive_actions': False,
}
OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text(json.dumps(state, indent=2) + '\n')
print(json.dumps(state, indent=2))
