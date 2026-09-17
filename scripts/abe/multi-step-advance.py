#!/usr/bin/env python3
"""Fail-closed validated multi-step advancement foundation for ABE-014.

The supervisor never mutates the authoritative queue. It consumes optional,
repository-local validation evidence and emits machine-readable advancement
history. Every proposed transition requires fresh PASS evidence tied to the
same task and a non-empty commit SHA; otherwise advancement stops.
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
QUEUE = ROOT / 'config/abe/task-queue.json'
EVIDENCE = ROOT / 'generated/abe/validation-evidence.json'
OUT = ROOT / 'build/abe/advancement-history.json'
MAX_STEPS = 5


def load(path):
    return json.loads(path.read_text(encoding='utf-8'))


def main():
    queue = load(QUEUE)
    rules = queue.get('rules', {})
    invariants = (
        queue.get('mode') == 'controlled-autonomous'
        and queue.get('authoritative_department_scope') == ['DO-DEP-01', 'DO-DEP-14']
        and queue.get('verified_baseline') == 'DO-DEP-04'
        and all(rules.get(k) is False for k in ('external_writes', 'production_deploy', 'destructive_actions'))
    )
    ready = [t for t in queue.get('queue', []) if t.get('status') == 'READY'][:MAX_STEPS]
    evidence = load(EVIDENCE) if EVIDENCE.exists() else {'records': []}
    records = evidence.get('records', []) if isinstance(evidence, dict) else []
    history = []
    previous_sha = None

    for task in ready:
        if not invariants or task.get('safe_autonomous') is not True:
            history.append({'task_id': task.get('id'), 'decision': 'BLOCKED_UNSAFE'})
            break
        match = next((r for r in records if r.get('task_id') == task.get('id')), None)
        fresh = bool(match and match.get('fresh') is True and match.get('validation_status') == 'PASS' and match.get('commit_sha'))
        distinct = bool(fresh and match['commit_sha'] != previous_sha)
        if not (fresh and distinct):
            history.append({'task_id': task['id'], 'decision': 'WAITING_FRESH_VALIDATION'})
            break
        history.append({'task_id': task['id'], 'decision': 'PROPOSE_COMPLETE_FOUNDATION', 'validation_commit_sha': match['commit_sha']})
        previous_sha = match['commit_sha']

    state = {
        'schema_version': 1,
        'status': 'READY' if history and history[-1]['decision'] == 'PROPOSE_COMPLETE_FOUNDATION' else ('IDLE' if not ready and invariants else 'WAITING_VALIDATION' if invariants else 'BLOCKED'),
        'bounded_max_steps': MAX_STEPS,
        'history': history,
        'authoritative_mutation_performed': False,
        'requires_reviewed_repository_commit': True,
        'authoritative_department_scope': ['DO-DEP-01', 'DO-DEP-14'],
        'verified_baseline': 'DO-DEP-04',
        'external_writes': False,
        'production_deploy': False,
        'destructive_actions': False,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(state, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(state, sort_keys=True))
    if state['status'] == 'BLOCKED':
        raise SystemExit(2)


if __name__ == '__main__':
    main()
